"""
LXL·QuantAxis Web 量化平台
Flask 单文件应用 — 浏览器访问
"""
import sys, os, json, threading, time, io, re
sys.path.insert(0, os.path.dirname(__file__))
os.chdir(os.path.dirname(__file__))

from flask import Flask, request, jsonify, Response, stream_with_context
from datetime import datetime
from src.lxl_quantaxis.core.security.settings import (
    SecurityConfigurationError,
    SecuritySettings,
)

SECURITY_SETTINGS = SecuritySettings.from_env()
if SECURITY_SETTINGS.is_production:
    raise SecurityConfigurationError(
        "web_app.py is a local-only legacy server; use web_modern.py in production"
    )

app = Flask(__name__)

# ═══════════════════════════════════════════════════════════
# HTML 页面 (内嵌 — 单文件部署)
# ═══════════════════════════════════════════════════════════

STYLE = """
:root{--bg0:#060912;--bg1:#0b0f1a;--bg2:#111827;--bg3:#1a2332;--bg4:#1f2a3a;
--ac:#3b82f6;--ac2:#8b5cf6;--gr:#10b981;--rd:#ef4444;--yl:#f59e0b;--cy:#06b6d4;
--pk:#ec4899;--t1:#f1f5f9;--t2:#94a3b8;--t3:#475569}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Inter','Segoe UI',system-ui,sans-serif;background:var(--bg0);
  color:var(--t1);min-height:100vh}
.sidebar{position:fixed;left:0;top:0;width:240px;height:100vh;background:var(--bg1);
  border-right:1px solid var(--bg3);overflow-y:auto;z-index:100;padding:20px 0}
.sidebar .logo{padding:0 20px 20px;border-bottom:1px solid var(--bg3);margin-bottom:16px}
.sidebar .logo h1{font-size:20px;color:var(--t1)}
.sidebar .logo h1 span{color:var(--ac)}
.sidebar .logo p{font-size:11px;color:var(--t3);margin-top:4px}
.nav-group{padding:0 16px;margin-bottom:8px}
.nav-group .label{font-size:10px;text-transform:uppercase;letter-spacing:1.5px;
  color:var(--t3);padding:8px 4px 4px}
.nav-item{display:flex;align-items:center;gap:10px;padding:10px 12px;
  border-radius:8px;cursor:pointer;font-size:13px;color:var(--t2);
  transition:all .15s;margin-bottom:2px;border-left:3px solid transparent}
.nav-item:hover{background:var(--bg2);color:var(--t1)}
.nav-item.active{background:var(--bg2);color:var(--t1);border-left-color:var(--ac)}
.main{margin-left:240px;padding:24px 28px}
.panel{display:none}
.panel.active{display:block}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:14px;margin-bottom:24px}
.kpi{background:var(--bg2);border-radius:12px;padding:20px}
.kpi .label{font-size:11px;text-transform:uppercase;letter-spacing:1px;color:var(--t3);margin-bottom:6px}
.kpi .val{font-size:30px;font-weight:800}
.card{background:var(--bg2);border-radius:12px;padding:20px;margin-bottom:18px}
.card h3{font-size:15px;margin-bottom:14px;color:var(--t1)}
table{width:100%;border-collapse:collapse;font-size:13px}
th{background:var(--bg3);padding:10px 14px;text-align:left;font-weight:600;
  color:var(--t3);font-size:10px;text-transform:uppercase;letter-spacing:.5px}
td{padding:9px 14px;border-bottom:1px solid var(--bg3)}
tr:hover td{background:rgba(59,130,246,.04)}
.tag{padding:2px 8px;border-radius:4px;font-size:10px;font-weight:700}
.tag-buy{background:#14532d;color:#86efac}.tag-sell{background:#7f1d1d;color:#fca5a5}
.btn{background:var(--ac);color:#fff;border:none;padding:10px 20px;border-radius:8px;
  font-size:13px;font-weight:600;cursor:pointer;transition:.15s}
.btn:hover{filter:brightness(1.15)}
.btn-sm{padding:6px 14px;font-size:12px}
.btn-gr{background:var(--gr)}.btn-rd{background:var(--rd)}.btn-ac2{background:var(--ac2)}
.btn-out{background:transparent;border:1px solid var(--bg4);color:var(--t2)}
input,select,textarea{background:var(--bg3);border:1px solid var(--bg4);color:var(--t1);
  padding:8px 12px;border-radius:6px;font-size:13px;width:100%}
input:focus,select:focus,textarea:focus{outline:none;border-color:var(--ac)}
.form-row{display:flex;gap:12px;margin-bottom:10px;align-items:flex-end}
.form-row label{font-size:11px;color:var(--t3);display:block;margin-bottom:4px}
.console{background:var(--bg0);border-radius:8px;padding:16px;font-family:'Cascadia Code','Consolas',monospace;
  font-size:12px;color:var(--t2);max-height:400px;overflow-y:auto;white-space:pre-wrap;line-height:1.6}
.console .green{color:var(--gr)}.console .red{color:var(--rd)}.console .yellow{color:var(--yl)}
.msg-user{background:var(--bg3);padding:12px 16px;border-radius:12px 12px 2px 12px;margin:8px 0 8px auto;
  max-width:70%;text-align:right}
.msg-ai{background:var(--bg2);padding:12px 16px;border-radius:12px 12px 12px 2px;margin:8px auto 8px 0;
  max-width:85%}
.chat-box{max-height:500px;overflow-y:auto;padding:8px}
.spinner{display:inline-block;width:20px;height:20px;border:2px solid var(--t3);
  border-top-color:var(--ac);border-radius:50%;animation:spin .8s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
.green{color:var(--gr)}.red{color:var(--rd)}.yellow{color:var(--yl)}.blue{color:var(--ac)}.purple{color:var(--ac2)}
"""

def base_page(title, body):
    return f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title>
<style>{STYLE}</style></head><body>{body}<script>{JS}</script></body></html>"""

JS = """
// 导航切换
document.querySelectorAll('.nav-item').forEach(item => {
  item.addEventListener('click', () => {
    document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
    item.classList.add('active');
    document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
    const target = document.getElementById(item.dataset.panel);
    if (target) target.classList.add('active');
    if (item.dataset.panel === 'dashboard') refreshKPIs();
    if (item.dataset.panel === 'positions') refreshPositions();
    if (item.dataset.panel === 'trades') refreshTrades();
  });
});

async function api(url, data=null) {
  const opts = data ? {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)} : {};
  const r = await fetch(url, opts); return r.json();
}

async function refreshKPIs() {
  try {
    const d = await api('/api/status');
    document.getElementById('kpi_trades').textContent = d.trades || 0;
    document.getElementById('kpi_positions').textContent = d.positions || 0;
    const pnl = d.total_pnl || 0;
    const el = document.getElementById('kpi_pnl');
    el.textContent = '¥' + pnl.toLocaleString();
    el.className = 'val ' + (pnl >= 0 ? 'green' : 'red');
    document.getElementById('kpi_backtests').textContent = d.backtests || 0;
  } catch(e) {}
}

// -- 回测 --
async function runBacktest() {
  const sym = document.getElementById('bt_sym').value || '601398';
  const strat = document.getElementById('bt_strat').value || 'ma_cross';
  const start = document.getElementById('bt_start').value || '2024-01-01';
  document.getElementById('bt_result').innerHTML = '<div class="spinner"></div> 运行中...';
  try {
    const r = await api('/api/backtest', {symbol:sym, strategy:strat, start_date:start});
    let html = `<b>${sym} @ ${strat}</b> | 数据: ${r.data_rows}条<br><br>`;
    if (r.metrics) for (const [k,v] of Object.entries(r.metrics)) html += `${k}: ${v}<br>`;
    if (r.trades) { html += `<br><b>最近交易:</b><br>`; r.trades.forEach(t => { html += `${t.date} ${t.action} ¥${t.price}×${t.qty}<br>`; }); }
    html += `<br><span class="green">✅ 完成</span>`;
    document.getElementById('bt_result').innerHTML = html;
  } catch(e) { document.getElementById('bt_result').innerHTML = `<span class="red">❌ ${e}</span>`; }
}

// -- 批量 --
async function runBatch() {
  document.getElementById('batch_result').innerHTML = '<div class="spinner"></div> 批量回测中...';
  try {
    const r = await api('/api/batch');
    let html = `<b>${r.count} 条结果</b><br><br>`;
    if (r.ranking) r.ranking.forEach((row,i) => { html += `${row.symbol} | ${row.strategy} | 夏普${row.sharpe} | ${row.total_return}<br>`; });
    document.getElementById('batch_result').innerHTML = html;
  } catch(e) { document.getElementById('batch_result').innerHTML = `<span class="red">❌ ${e}</span>`; }
}

// -- AI聊天 --
async function chatSend() {
  const input = document.getElementById('chat_input');
  const msg = input.value.trim(); if (!msg) return; input.value = '';
  const box = document.getElementById('chat_messages');
  box.innerHTML += `<div class="msg-user">${msg}</div>`;
  box.innerHTML += `<div class="msg-ai" id="chat_loading"><div class="spinner"></div> 思考中...</div>`;
  box.scrollTop = box.scrollHeight;
  try {
    const r = await api('/api/ai/chat', {message:msg});
    document.getElementById('chat_loading').remove();
    let reply = r.reply || '无回复';
    if (r.system_action) reply = `<span class="yellow">[系统执行: ${r.system_action}]</span><br>` + reply;
    box.innerHTML += `<div class="msg-ai">${reply}</div>`;
  } catch(e) {
    document.getElementById('chat_loading').remove();
    box.innerHTML += `<div class="msg-ai"><span class="red">❌ 连接失败，请检查AI配置</span></div>`;
  }
  box.scrollTop = box.scrollHeight;
}

// -- 交易日志 --
async function submitTrade() {
  const data = {
    market: document.getElementById('tr_market').value,
    symbol: document.getElementById('tr_symbol').value.toUpperCase(),
    name: document.getElementById('tr_name').value,
    direction: document.getElementById('tr_dir').value,
    trade_type: document.getElementById('tr_type').value,
    trade_date: document.getElementById('tr_date').value,
    price: parseFloat(document.getElementById('tr_price').value),
    quantity: parseInt(document.getElementById('tr_qty').value),
    fee: parseFloat(document.getElementById('tr_fee').value) || 0,
    reason: document.getElementById('tr_reason').value,
    tags: document.getElementById('tr_tags').value,
  };
  try {
    const r = await api('/api/trade/add', data);
    document.getElementById('tr_result').innerHTML = `<span class="green">✅ 已保存! ID=${r.id}</span>`;
    ['tr_symbol','tr_name','tr_price','tr_qty','tr_reason','tr_tags'].forEach(id => {
      if (!['tr_symbol','tr_name'].includes(id)) document.getElementById(id).value = '';
    });
  } catch(e) { document.getElementById('tr_result').innerHTML = `<span class="red">❌ ${e}</span>`; }
}

async function refreshPositions() {
  try {
    const r = await api('/api/trade/positions');
    if (r.positions && r.positions.length) {
      let html = '<table><thead><tr><th>ID</th><th>市场</th><th>代码</th><th>名称</th><th>日期</th><th>价格</th><th>数量</th></tr></thead><tbody>';
      r.positions.forEach(p => { html += `<tr><td>${p.id}</td><td>${p.market}</td><td>${p.symbol}</td><td>${p.name}</td><td>${p.trade_date}</td><td>¥${p.price}</td><td>${p.quantity}</td></tr>`; });
      html += '</tbody></table>';
      document.getElementById('pos_content').innerHTML = html;
    } else document.getElementById('pos_content').innerHTML = '<p style="color:var(--t3)">暂无持仓</p>';
  } catch(e) {}
}

async function refreshTrades() {
  try {
    const r = await api('/api/trade/history?limit=50');
    if (r.trades && r.trades.length) {
      let html = '<table><thead><tr><th>ID</th><th>日期</th><th>代码</th><th>名称</th><th>类型</th><th>价格</th><th>数量</th></tr></thead><tbody>';
      r.trades.forEach(t => { html += `<tr><td>${t.id}</td><td>${t.trade_date}</td><td>${t.symbol}</td><td>${t.name}</td><td>${t.trade_type}</td><td>¥${t.price}</td><td>${t.quantity}</td></tr>`; });
      html += '</tbody></table>';
      document.getElementById('trades_content').innerHTML = html;
    } else document.getElementById('trades_content').innerHTML = '<p style="color:var(--t3)">暂无记录</p>';
  } catch(e) {}
}

// -- 快速验证 --
async function runQuickBacktest() {
  const sym = document.getElementById('qb_sym').value || '601398';
  const market = document.getElementById('qb_market').value || 'A股';
  const strat = document.getElementById('qb_strat').value || 'ma_cross';
  const start = document.getElementById('qb_start').value || '2024-01-01';
  const end = document.getElementById('qb_end').value || null;
  document.getElementById('qb_result').innerHTML = '<div class="spinner"></div> 运行中...';
  try {
    const r = await api('/api/quick_backtest', {symbol:sym, market:market, strategy:strat, start_date:start, end_date:end});
    let html = `<b>${sym} @ ${strat}</b> | 数据: ${r.data_rows}条 | ${r.date_range}<br><br>`;
    if (r.metrics) for (const [k,v] of Object.entries(r.metrics)) html += `${k}: ${v}<br>`;
    if (r.trades) { html += `<br><b>最近交易:</b><br>`; r.trades.forEach(t => { html += `${t.date} ${t.action} ¥${t.price}×${t.qty}<br>`; }); }
    html += `<br><span class="green">✅ 完成</span>`;
    document.getElementById('qb_result').innerHTML = html;
  } catch(e) { document.getElementById('qb_result').innerHTML = `<span class="red">❌ ${e}</span>`; }
}

// -- 个股诊断 --
async function runDiagnosis() {
  const sym = document.getElementById('diag_sym').value || '601398';
  const market = document.getElementById('diag_market').value || 'A股';
  const start = document.getElementById('diag_start').value || '2022-01-01';
  const el = document.getElementById('diag_result');
  el.innerHTML = '<div class="spinner"></div> ⏳ 加载数据 + 刷新行情...';
  try {
    const r = await api('/api/diagnosis', {symbol:sym, market:market, start_date:start});
    if (r.error) { el.innerHTML = `<span class="red">❌ ${r.error}</span>`; return; }
    let html = `<pre style="white-space:pre-wrap;font-size:12px;line-height:1.5">${r.report}</pre>`;
    el.innerHTML = html;
  } catch(e) { el.innerHTML = `<span class="red">❌ ${e}</span>`; }
}

// -- 每日快扫 --
async function runDailyScan(mode) {
  const syms = document.getElementById('scan_symbols').value.trim();
  const el = document.getElementById('scan_result');
  el.innerHTML = '<div class="spinner"></div> ⏳ 扫描中...';
  try {
    const symbols = syms ? syms.split(/\\s+/) : [];
    const r = await api('/api/daily_scan', {symbols:symbols, full:mode==='full'});
    if (r.error) { el.innerHTML = `<span class="red">❌ ${r.error}</span>`; return; }
    let html = `<b>扫描 ${r.count} 只标的 | ${mode==='full'?'完整诊断':'快速评分'}</b><br><br>`;
    html += `<table><thead><tr><th>排名</th><th>代码</th><th>价格</th><th>评分</th><th>信号</th></tr></thead><tbody>`;
    if (r.results) r.results.forEach((s,i) => {
      const cls = s.score>=60?'green':(s.score>=40?'yellow':'red');
      html += `<tr><td>${i+1}</td><td>${s.symbol}</td><td>¥${s.price}</td><td class="${cls}">${s.score}</td><td>${s.level||''}</td></tr>`;
    });
    html += '</tbody></table>';
    if (r.summary) html += `<br><b>汇总:</b> 🟢${r.summary.buy||0}只 ⚪${r.summary.wait||0}只 🔴${r.summary.avoid||0}只`;
    html += `<br><span class="green">✅ 完成</span> | 报告: ${r.report_file||''}`;
    el.innerHTML = html;
  } catch(e) { el.innerHTML = `<span class="red">❌ ${e}</span>`; }
}

// 股票搜索
async function lookupStock() {
  const code = document.getElementById('tr_symbol').value.trim();
  if (code.length < 4) return;
  try {
    const r = await api('/api/stock/lookup?code=' + encodeURIComponent(code));
    if (r.name && r.name !== code) document.getElementById('tr_name').value = r.name;
    if (r.suggestions) document.getElementById('tr_suggest').textContent = r.suggestions.join(' | ');
  } catch(e) {}
}

// 估值
async function refreshValuation() {
  try {
    const r = await api('/api/valuation');
    if (r.snapshot && r.snapshot.length) {
      let html = '<table><thead><tr><th>指数</th><th>名称</th><th>PE</th><th>PE分位</th><th>PE评级</th><th>PB分位</th></tr></thead><tbody>';
      r.snapshot.forEach(s => { html += `<tr><td>${s.指数}</td><td>${s.名称}</td><td>${s.PE||'N/A'}</td><td>${s['PE分位']||'N/A'}</td><td>${s['PE评级']||'-'}</td><td>${s['PB分位']||'N/A'}</td></tr>`; });
      html += '</tbody></table>';
      document.getElementById('val_content').innerHTML = html;
    }
  } catch(e) {}
}

// 页面加载
window.onload = () => { refreshKPIs(); };
document.getElementById('tr_symbol')?.addEventListener('input', lookupStock);
"""

# ═══════════════════════════════════════════════════════════
# HTML 模板 (内嵌)
# ═══════════════════════════════════════════════════════════

SIDEBAR = """
<div class="sidebar">
  <div class="logo"><h1>LXL<span>·</span>QuantAxis</h1><p>量化交易平台 v2.1</p></div>
  <div class="nav-group"><div class="label">总览</div>
    <div class="nav-item active" data-panel="dashboard">🏠 仪表盘</div>
  </div>
  <div class="nav-group"><div class="label">交易实战</div>
    <div class="nav-item" data-panel="quick_backtest">🔍 快速验证</div>
    <div class="nav-item" data-panel="diagnosis">🩺 个股诊断</div>
    <div class="nav-item" data-panel="daily_scan">🔄 每日快扫</div>
    <div class="nav-item" data-panel="journal">📒 交易日志</div>
    <div class="nav-item" data-panel="positions">📦 当前持仓</div>
    <div class="nav-item" data-panel="trades">📋 交易记录</div>
  </div>
  <div class="nav-group"><div class="label">策略</div>
    <div class="nav-item" data-panel="backtest">🧪 策略回测</div>
    <div class="nav-item" data-panel="batch">🔬 批量回测</div>
    <div class="nav-item" data-panel="optimize">⚙️ 参数优化</div>
    <div class="nav-item" data-panel="evolve">🧬 策略进化</div>
  </div>
  <div class="nav-group"><div class="label">指数</div>
    <div class="nav-item" data-panel="valuation">📊 指数估值</div>
    <div class="nav-item" data-panel="index_strat">🔄 轮动+定投</div>
  </div>
  <div class="nav-group"><div class="label">AI</div>
    <div class="nav-item" data-panel="chat">💬 AI 对话</div>
    <div class="nav-item" data-panel="ai_review">📝 AI 复盘</div>
  </div>
</div>
<div class="main">
  <div class="panel active" id="panel-dashboard">{}</div>
  <div class="panel" id="panel-quick_backtest">{}</div>
  <div class="panel" id="panel-diagnosis">{}</div>
  <div class="panel" id="panel-daily_scan">{}</div>
  <div class="panel" id="panel-journal">{}</div>
  <div class="panel" id="panel-positions">{}</div>
  <div class="panel" id="panel-trades">{}</div>
  <div class="panel" id="panel-backtest">{}</div>
  <div class="panel" id="panel-batch">{}</div>
  <div class="panel" id="panel-optimize">{}</div>
  <div class="panel" id="panel-evolve">{}</div>
  <div class="panel" id="panel-valuation">{}</div>
  <div class="panel" id="panel-index_strat">{}</div>
  <div class="panel" id="panel-chat">{}</div>
  <div class="panel" id="panel-ai_review">{}</div>
</div>
"""

def build_page():
    # 仪表盘
    dash = """
    <div class="kpis">
      <div class="kpi"><div class="label">交易记录</div><div class="val blue" id="kpi_trades">0</div></div>
      <div class="kpi"><div class="label">当前持仓</div><div class="val yellow" id="kpi_positions">0</div></div>
      <div class="kpi"><div class="label">总盈亏</div><div class="val green" id="kpi_pnl">¥0</div></div>
      <div class="kpi"><div class="label">回测次数</div><div class="val purple" id="kpi_backtests">0</div></div>
    </div>
    <div class="card"><h3>📊 快速操作</h3>
      <button class="btn" onclick="document.querySelector('[data-panel=backtest]').click()">单策略回测</button>
      <button class="btn btn-gr" onclick="document.querySelector('[data-panel=batch]').click()" style="margin-left:8px">批量回测</button>
      <button class="btn btn-ac2" onclick="document.querySelector('[data-panel=valuation]').click()" style="margin-left:8px">指数估值</button>
      <button class="btn btn-out" onclick="document.querySelector('[data-panel=chat]').click()" style="margin-left:8px">AI 对话</button>
    </div>"""

    # 策略选项 (多个面板共用)
    from src.strategies.library import STRATEGIES
    from src.factors.composer import PRESET_STRATEGIES
    all_s = list(STRATEGIES.keys()) + list(PRESET_STRATEGIES.keys())
    strat_opts = "".join(f'<option value="{s}">{STRATEGIES.get(s,PRESET_STRATEGIES.get(s,{"name":s}))["name"]}</option>' for s in all_s)

    # 快速验证面板
    quick_backtest = f"""
    <div class="card"><h3>🔍 快速验证 — 选股票 → 设时间 → 选策略 → 出结果</h3>
    <div class="form-row">
      <div><label>股票代码</label><input id="qb_sym" value="601398"></div>
      <div><label>市场</label><select id="qb_market"><option>A股</option><option>美股</option><option>港股</option></select></div>
    </div>
    <div class="form-row">
      <div><label>起始日期</label><input id="qb_start" value="2024-01-01"></div>
      <div><label>截止日期(可选)</label><input id="qb_end" placeholder="留空=最新"></div>
    </div>
    <div class="form-row">
      <div><label>策略</label><select id="qb_strat">{strat_opts}</select></div>
      <div style="display:flex;align-items:flex-end"><button class="btn" onclick="runQuickBacktest()">▶ 验证</button></div>
    </div>
    <div class="console" id="qb_result" style="margin-top:12px">输入股票、时间、策略，点击验证...</div></div>"""

    # 个股诊断面板
    diagnosis = """
    <div class="card"><h3>🩺 个股诊断 — 全策略扫描 · 投资者适配 · 时机仓位</h3>
    <div class="form-row">
      <div><label>股票代码</label><input id="diag_sym" value="601398"></div>
      <div><label>市场</label><select id="diag_market"><option>A股</option><option>美股</option><option>港股</option></select></div>
      <div><label>回测起始</label><input id="diag_start" value="2022-01-01"></div>
      <div style="display:flex;align-items:flex-end"><button class="btn btn-gr" onclick="runDiagnosis()">▶ 开始诊断</button></div>
    </div>
    <div class="console" id="diag_result" style="margin-top:12px;max-height:600px">点击开始诊断，系统将运行全部11个策略并生成完整报告...</div></div>"""

    # 每日快扫面板
    daily_scan = """
    <div class="card"><h3>🔄 每日快扫 — 扫描13只默认标的</h3>
    <div class="form-row">
      <div style="flex:1"><label>自定义标的 (空格分隔, 留空=默认13只)</label><input id="scan_symbols" placeholder="如: 000858 601398"></div>
    </div>
    <div class="form-row">
      <button class="btn btn-gr" onclick="runDailyScan('quick')">⚡ 快速扫描 (因子评分)</button>
      <button class="btn btn-ac2" onclick="runDailyScan('full')" style="margin-left:8px">🔬 完整诊断 (含策略回测)</button>
    </div>
    <div class="console" id="scan_result" style="margin-top:12px;max-height:500px">点击扫描，自动刷新行情并生成信号排名...</div></div>"""

    # 交易日志
    today = datetime.now().strftime("%Y-%m-%d")
    journal = f"""
    <div class="card"><h3>📒 记录交易</h3>
    <div class="form-row">
      <div><label>市场</label><select id="tr_market"><option>A股</option><option>美股</option><option>港股</option></select></div>
      <div><label>代码</label><input id="tr_symbol" value="601398" oninput="lookupStock()"></div>
      <div><label>名称</label><input id="tr_name" value="工商银行"></div>
      <div><label>方向</label><select id="tr_dir"><option>做多</option><option>做空</option></select></div>
    </div>
    <div class="form-row">
      <div><label>类型</label><select id="tr_type"><option>买入</option><option>卖出</option></select></div>
      <div><label>日期</label><input id="tr_date" value="{today}"></div>
      <div><label>价格</label><input id="tr_price" value="5.00" type="number" step="0.01"></div>
      <div><label>数量</label><input id="tr_qty" value="1000" type="number"></div>
      <div><label>手续费</label><input id="tr_fee" value="0" type="number" step="0.01"></div>
    </div>
    <div class="form-row">
      <div style="flex:1"><label>理由</label><input id="tr_reason"></div>
      <div style="flex:1"><label>标签</label><input id="tr_tags"></div>
    </div>
    <div id="tr_suggest" style="font-size:11px;color:var(--t3);margin-bottom:8px"></div>
    <button class="btn btn-gr" onclick="submitTrade()">保存交易</button>
    <div id="tr_result" style="margin-top:8px"></div></div>"""

    # 持仓
    positions = '<div class="card"><h3>📦 当前持仓</h3><div id="pos_content"></div></div>'

    # 交易记录
    trades = '<div class="card"><h3>📋 交易记录</h3><div id="trades_content"></div></div>'

    # 策略回测
    backtest = f"""
    <div class="card"><h3>🧪 单策略回测</h3>
    <div class="form-row">
      <div><label>股票代码</label><input id="bt_sym" value="601398"></div>
      <div><label>策略</label><select id="bt_strat">{strat_opts}</select></div>
      <div><label>起始日期</label><input id="bt_start" value="2024-01-01"></div>
      <div style="display:flex;align-items:flex-end"><button class="btn" onclick="runBacktest()">▶ 运行</button></div>
    </div>
    <div class="console" id="bt_result">点击运行查看结果</div></div>"""

    # 批量
    batch = """
    <div class="card"><h3>🔬 批量回测 (5标的 × 11策略)</h3>
    <button class="btn btn-gr" onclick="runBatch()">▶ 全部运行</button>
    <div class="console" id="batch_result" style="margin-top:12px">点击运行</div></div>"""

    # 优化
    optimize = """
    <div class="card"><h3>⚙️ 参数优化</h3>
    <div class="form-row">
      <div><label>股票</label><input id="opt_sym" value="601398"></div>
      <div><label>策略</label><select id="opt_strat">"""+strat_opts+"""</select></div>
      <div><label>起始</label><input id="opt_start" value="2022-01-01"></div>
    </div>
    <div class="form-row">
      <div style="flex:1"><label>参数 (JSON)</label><input id="opt_params" value='{"fast_period":[5,10,20],"slow_period":[20,30,60]}'></div>
    </div>
    <button class="btn btn-ac2" onclick="runOptimize()">▶ 网格搜索</button>
    <div class="console" id="opt_result" style="margin-top:12px"></div></div>"""

    # 进化
    evolve = """
    <div class="card"><h3>🧬 AI + 遗传算法 策略进化</h3>
    <p style="color:var(--t3);margin-bottom:12px">AI分析回测数据 → 生成种子策略 → 遗传算法杂交突变 → 回测验证 → 最优策略入银行</p>
    <div class="form-row">
      <div><label>标的</label><input id="ev_sym" value="601398"></div>
      <div><label>代数</label><input id="ev_gen" value="5" type="number"></div>
    </div>
    <button class="btn btn-gr" onclick="runEvolve()">▶ 启动进化</button>
    <div class="console" id="ev_result" style="margin-top:12px"></div></div>"""

    # 估值
    valuation = """
    <div class="card"><h3>📊 指数估值快照</h3>
    <button class="btn btn-sm btn-out" onclick="refreshValuation()">刷新</button>
    <div id="val_content" style="margin-top:12px"></div></div>"""

    # 指数策略
    index_strat = """
    <div class="card"><h3>🔄 指数轮动 + 定投</h3>
    <button class="btn btn-gr" onclick="runIndexCompare()">▶ 策略对比</button>
    <div class="console" id="idx_result" style="margin-top:12px"></div></div>"""

    # AI 聊天
    chat = """
    <div class="card"><h3>💬 AI 量化助手</h3>
    <div class="chat-box" id="chat_messages" style="max-height:450px;min-height:300px"></div>
    <div class="form-row" style="margin-top:12px">
      <input id="chat_input" style="flex:1" placeholder="输入消息... 或 输入'跑回测'/'看估值'操控系统" onkeypress="if(event.key==='Enter')chatSend()">
      <button class="btn" onclick="chatSend()">发送</button>
    </div></div>"""

    # AI 复盘
    ai_review = """
    <div class="card"><h3>📝 AI 交易复盘</h3>
    <button class="btn btn-gr" onclick="runAIReview()">▶ 分析交易</button>
    <div class="console" id="ai_review_result" style="margin-top:12px"></div></div>"""

    html = SIDEBAR.format(dash, quick_backtest, diagnosis, daily_scan,
                          journal, positions, trades, backtest, batch,
                          optimize, evolve, valuation, index_strat, chat, ai_review)
    return base_page("LXL·QuantAxis 量化平台", html)


# ═══════════════════════════════════════════════════════════
# API 路由
# ═══════════════════════════════════════════════════════════

@app.route('/')
def index():
    return build_page()

@app.route('/api/status')
def api_status():
    try:
        from src.models.trade import TradeRepository
        from src.backtest.batch_runner import ResultDB
        repo = TradeRepository(); db = ResultDB()
        pnl = [p["net_pnl"] for p in repo.get_all_pnl()]
        return jsonify({
            "trades": repo.count(),
            "positions": len(repo.find_open_positions()),
            "total_pnl": sum(pnl) if pnl else 0,
            "backtests": db.summary().get("总回测数", 0),
        })
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/backtest', methods=['POST'])
def api_backtest():
    data = request.json
    try:
        from src.backtest.data_feed import get_data
        from src.backtest.engine import BacktestEngine
        from src.backtest.batch_runner import _make_strategy_instance
        d = get_data(data.get("symbol","601398"), "A股", start_date=data.get("start_date","2024-01-01"))
        s = _make_strategy_instance(data.get("strategy","ma_cross"), {}, data.get("symbol","601398"))
        r = BacktestEngine().run(s, d)
        return jsonify({
            "data_rows": len(d),
            "metrics": r["metrics"],
            "trades": [{"date":t["date"],"action":t["action"],"price":t["price"],"qty":t["quantity"]}
                      for t in r["portfolio"].trade_log[-10:]]
        })
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/batch', methods=['POST'])
def api_batch():
    try:
        from src.backtest.batch_runner import BatchRunner
        runner = BatchRunner()
        runner.add_symbols(["601398","000858","600036","600900","000333"])
        from src.strategies.library import STRATEGIES
        from src.factors.composer import PRESET_STRATEGIES
        runner.add_strategies(list(STRATEGIES.keys()) + list(PRESET_STRATEGIES.keys()))
        runner.start_date = "2024-01-01"
        df = runner.run(verbose=False)
        ranking = []
        if not df.empty:
            for _, r in df.head(20).iterrows():
                ranking.append({"symbol":r["symbol"],"strategy":r["strategy"],
                               "sharpe":r["夏普比率"],"total_return":str(r["总收益率"])})
        return jsonify({"count": len(df), "ranking": ranking})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/trade/add', methods=['POST'])
def api_trade_add():
    try:
        from src.models.trade import Trade, TradeRepository
        d = request.json
        t = Trade(market=d.get("market","A股"), symbol=d.get("symbol",""), name=d.get("name",""),
                 direction=d.get("direction","做多"), trade_type=d.get("trade_type","买入"),
                 trade_date=d.get("trade_date",""), price=float(d.get("price",0)),
                 quantity=int(d.get("quantity",0)), fee=float(d.get("fee",0)),
                 reason=d.get("reason",""), tags=d.get("tags",""))
        tid = TradeRepository().add(t)
        return jsonify({"id": tid, "ok": True})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/trade/positions')
def api_trade_positions():
    try:
        from src.models.trade import TradeRepository
        ps = TradeRepository().find_open_positions()
        return jsonify({"positions": [{"id":p.id,"market":p.market,"symbol":p.symbol,
                     "name":p.name,"trade_date":p.trade_date,"price":p.price,"quantity":p.quantity} for p in ps]})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/trade/history')
def api_trade_history():
    try:
        from src.models.trade import TradeRepository
        ts = TradeRepository().find_all(limit=int(request.args.get("limit",50)))
        return jsonify({"trades": [{"id":t.id,"trade_date":t.trade_date,"market":t.market,
                     "symbol":t.symbol,"name":t.name,"trade_type":t.trade_type,
                     "price":t.price,"quantity":t.quantity} for t in ts]})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/stock/lookup')
def api_stock_lookup():
    try:
        from src.data.stock_db import ensure_stock_db
        db = ensure_stock_db()
        code = request.args.get("code","").strip()
        name = db.get_name(code)
        suggestions = db.autocomplete(code, limit=8)
        return jsonify({"code": code, "name": name, "suggestions": suggestions})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/valuation')
def api_valuation():
    try:
        from src.index.valuation import get_valuation_snapshot
        snap = get_valuation_snapshot()
        return jsonify({"snapshot": snap.to_dict(orient="records") if not snap.empty else []})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/quick_backtest', methods=['POST'])
def api_quick_backtest():
    data = request.json
    try:
        from src.backtest.data_feed import get_data, download_watchlist, get_data_summary
        from src.backtest.engine import BacktestEngine
        from src.backtest.batch_runner import _make_strategy_instance
        from datetime import datetime as _dt

        sym = data.get("symbol", "601398")
        market = data.get("market", "A股")
        strat_key = data.get("strategy", "ma_cross")
        start = data.get("start_date", "2024-01-01")
        end = data.get("end_date") or None

        # 检查数据新鲜度，自动刷新
        today_str = _dt.now().strftime("%Y-%m-%d")
        try:
            cache_df = get_data_summary()
            target_file = f"{market}_{sym}_daily.csv"
            if not cache_df.empty:
                mask = cache_df["文件"] == target_file
                if mask.any():
                    latest = str(cache_df[mask].iloc[0]["结束日期"]).strip()[:10]
                    if latest < today_str:
                        download_watchlist([{"symbol": sym, "market": market, "name": sym}], verbose=False)
        except Exception:
            pass

        d = get_data(sym, market, start_date=start, end_date=end)
        s = _make_strategy_instance(strat_key, {}, sym)
        r = BacktestEngine().run(s, d)
        return jsonify({
            "data_rows": len(d),
            "date_range": f"{str(d['date'].iloc[0])[:10]} ~ {str(d['date'].iloc[-1])[:10]}",
            "metrics": r["metrics"],
            "trades": [{"date": t["date"], "action": t["action"], "price": t["price"], "qty": t["quantity"]}
                      for t in r["portfolio"].trade_log[-10:]]
        })
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route('/api/diagnosis', methods=['POST'])
def api_diagnosis():
    """个股诊断 API — 运行全部策略 + 因子分析 + 投资者适配"""
    data = request.json
    sym = data.get("symbol", "601398")
    market = data.get("market", "A股")
    start = data.get("start_date", "2022-01-01")

    try:
        from src.backtest.data_feed import get_data, download_watchlist, get_data_summary
        from src.backtest.engine import BacktestEngine
        from src.backtest.batch_runner import _make_strategy_instance
        from src.strategies.library import STRATEGIES
        from src.factors.composer import PRESET_STRATEGIES
        from src.factors.definitions import FactorCalculator
        from datetime import datetime as _dt

        # 自动刷新数据
        today_str = _dt.now().strftime("%Y-%m-%d")
        try:
            cache_df = get_data_summary()
            target_file = f"{market}_{sym}_daily.csv"
            if not cache_df.empty:
                mask = cache_df["文件"] == target_file
                if mask.any():
                    latest = str(cache_df[mask].iloc[0]["结束日期"]).strip()[:10]
                    if latest < today_str:
                        download_watchlist([{"symbol": sym, "market": market, "name": sym}], verbose=False)
        except Exception:
            pass

        d = get_data(sym, market, start_date=start)
        if d is None or len(d) == 0:
            return jsonify({"error": f"未获取到 {sym} 的数据"})

        current_price = float(d["close"].iloc[-1])
        date_start = str(d["date"].iloc[0])[:10]
        date_end = str(d["date"].iloc[-1])[:10]
        fresh_tag = "🟢 今日" if date_end >= today_str else f"⚠️ 仅到 {date_end}"

        # 全策略回测
        report = []
        report.append(f"═══ 个股诊断报告: {sym}  {_dt.now().strftime('%Y-%m-%d %H:%M')} ═══")
        report.append(f"市场:{market} | 数据:{date_start}~{date_end} | K线:{len(d)}条 | {fresh_tag}")
        report.append(f"当前价格: ¥{current_price:.2f}")
        report.append("")

        all_strategies = list(STRATEGIES.keys()) + list(PRESET_STRATEGIES.keys())
        results = []
        for key in all_strategies:
            name = key
            for src in [STRATEGIES, PRESET_STRATEGIES]:
                if key in src: name = src[key].get("name", key); break
            try:
                strategy = _make_strategy_instance(key, {}, sym)
                engine = BacktestEngine()
                res = engine.run(strategy, d)
                results.append({"key": key, "name": name, "metrics": res["metrics"], "error": None})
            except Exception as e:
                results.append({"key": key, "name": name, "metrics": {}, "error": str(e)})

        def _parse_sharpe(r):
            if r["error"]: return -999
            try: return float(str(r["metrics"].get("夏普比率", -999)))
            except: return -999
        results.sort(key=_parse_sharpe, reverse=True)

        report.append("─── 一、历史策略表现 ───")
        report.append(f"{'排名':<4} {'策略':<14} {'总收益':>8} {'夏普':>6} {'回撤':>8} {'胜率':>6}")
        for i, r in enumerate(results, 1):
            if r["error"]:
                report.append(f"  {i:<2} {r['name']:<14} {'ERR':>8}")
            else:
                m = r["metrics"]
                report.append(f"  {i:<2} {r['name']:<14} {str(m.get('总收益率','-')):>8} {str(m.get('夏普比率','-')):>6} {str(m.get('最大回撤','-')):>8} {str(m.get('胜率','-')):>6}")

        # 因子分析
        report.append("")
        report.append("─── 二、当前入场时机 ───")
        try:
            calc = FactorCalculator(d)
            factors_df = calc.compute_all()
            cf = factors_df.iloc[-1]
            def _fv(name, default=0.5):
                try: return float(cf.get(name, default))
                except: return default

            score = 50
            rsi = _fv("rsi_norm")
            if rsi < 0.3: score += int((0.3-rsi)/0.3*20)
            elif rsi > 0.7: score -= int((rsi-0.7)/0.3*20)
            else: score += 5

            bb = _fv("bollinger_pos")
            if bb < 0.2: score += int((0.2-bb)/0.2*20)
            elif bb > 0.8: score -= int((bb-0.8)/0.2*20)
            else: score += 5

            ma = _fv("ma_alignment")
            if ma > 0.7: score += 15
            elif ma < 0.3: score -= 10

            macd_h = _fv("macd_hist", 0.5)
            if macd_h > 0.55: score += 15
            elif macd_h < 0.45: score -= 10

            vol = _fv("volume_ratio")
            if vol > 0.7: score += 10
            elif vol < 0.3: score -= 5
            else: score += 3

            mom = _fv("momentum_score")
            if mom > 0.6: score += 10
            elif mom < 0.4: score -= 5
            else: score += 2

            trend = _fv("trend_strength")
            if trend > 0.5: score += 5
            else: score -= 3

            score = max(0, min(100, score))
            level = "🟢强烈买入" if score>=80 else ("🟡谨慎买入" if score>=60 else ("⚪观望" if score>=40 else "🔴回避"))
            bar = "█"*int(score/5) + "░"*(20-int(score/5))
            report.append(f"RSI:{rsi*100:.0f} | 布林:{bb:.2f} | 均线:{ma:.2f} | MACD:{macd_h:.2f} | 量比:{vol:.2f} | 动量:{mom:.2f}")
            report.append(f"评分:{score}/100 [{bar}] {level}")
        except Exception as e:
            report.append(f"因子分析失败: {e}")

        report.append("")
        report.append(f"═══ 报告结束 ═══")

        return jsonify({"report": "\n".join(report), "data_rows": len(d), "score": score if 'score' in dir() else 50})
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route('/api/daily_scan', methods=['POST'])
def api_daily_scan():
    """每日快扫 API"""
    data = request.json
    symbols = data.get("symbols", [])
    full = data.get("full", False)

    try:
        # 调用 daily_runner 的核心逻辑
        import sys, os, io
        sys.path.insert(0, os.path.dirname(__file__))
        from daily_runner import quick_diagnosis, DEFAULT_WATCHLIST
        from datetime import datetime

        watchlist = DEFAULT_WATCHLIST if not symbols else [
            {"symbol": s, "market": "A股", "name": s} for s in symbols
        ]

        results = []
        for item in watchlist:
            r = quick_diagnosis(item["symbol"], item.get("market", "A股"),
                              item.get("name", item["symbol"]), full=full)
            results.append(r)

        results.sort(key=lambda r: r["score"], reverse=True)

        scan_results = []
        for r in results:
            scan_results.append({
                "symbol": r["symbol"], "name": r["name"],
                "price": r["price"], "score": r["score"],
                "level": r["level"].split()[-1] if r["level"] else "N/A",
                "data_fresh": r.get("data_fresh", False),
            })

        buys = [r for r in results if not r.get("error") and r["score"] >= 60]
        waits = [r for r in results if not r.get("error") and 40 <= r["score"] < 60]
        avoids = [r for r in results if not r.get("error") and r["score"] < 40]

        return jsonify({
            "count": len(results),
            "results": scan_results,
            "summary": {"buy": len(buys), "wait": len(waits), "avoid": len(avoids)},
            "report_file": f"D:/trading_data/reports/daily_scan_{datetime.now().strftime('%Y%m%d')}.txt"
        })
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route('/api/ai/chat', methods=['POST'])
def api_ai_chat():
    msg = request.json.get("message","")
    try:
        # 关键词快速匹配
        t = msg.lower().replace(" ","")
        for ks, act in [
            (["回测","跑一下","backtest"],"backtest"),
            (["批量回测","batch"],"batch"),
            (["估值","valuation"],"valuation"),
            (["进化","factory","evolve"],"factory"),
            (["状态","status"],"status"),
        ]:
            if any(k in t for k in ks):
                import re as _re
                codes = _re.findall(r'\b(60\d{4}|00\d{4})\b', msg)
                sym = codes[0] if codes else "601398"
                # 执行系统命令
                res = _execute_system_action(act, sym)
                from src.ai.engine import LLMClient
                summary_prompt = f"系统执行了{act}操作，结果摘要:{res[:400]}\n用一句话自然语言总结。"
                try:
                    ai_summary = LLMClient().ask(summary_prompt, system="简短回复，一句话。")
                except:
                    ai_summary = res[:200]
                return jsonify({"reply": ai_summary, "system_action": act, "system_result": res[:500]})

        # 正常 AI 对话
        from src.ai.engine import LLMClient
        reply = LLMClient().ask(msg, system="你是LXL的量化助手。简洁回复。涉及投资声明仅供参考。")
        return jsonify({"reply": reply})
    except Exception as e:
        return jsonify({"reply": f"[AI未连接] {e}\n请先配置 AI: 点左侧→AI→配置AI"})

def _execute_system_action(action, arg=""):
    buf = io.StringIO(); old = sys.stdout; sys.stdout = buf
    try:
        if action == "backtest":
            from src.backtest.data_feed import get_data
            from src.backtest.engine import BacktestEngine
            from src.backtest.batch_runner import _make_strategy_instance
            d = get_data(arg,"A股",start_date="2024-01-01")
            s = _make_strategy_instance("ma_cross",{},arg)
            r = BacktestEngine().run(s,d)
            res = f"[回测:{arg}] {len(d)}条\n"
            for k,v in r["metrics"].items(): res += f"{k}:{v}\n"
            return res
        elif action == "batch":
            from src.backtest.batch_runner import BatchRunner
            from src.strategies.library import STRATEGIES
            from src.factors.composer import PRESET_STRATEGIES
            ru = BatchRunner()
            ru.add_symbols(["601398","000858","600036","600900","000333"])
            ru.add_strategies(list(STRATEGIES.keys()) + list(PRESET_STRATEGIES.keys()))
            ru.start_date="2024-01-01"
            df = ru.run(verbose=False)
            return f"[批量回测] {len(df)}条"
        elif action == "valuation":
            from src.index.valuation import show_valuation; show_valuation()
        elif action == "status":
            from src.models.trade import TradeRepository
            repo = TradeRepository()
            pnl = [p["net_pnl"] for p in repo.get_all_pnl()]
            return f"交易:{repo.count()}笔 持仓:{len(repo.find_open_positions())}只 总盈亏:¥{sum(pnl) if pnl else 0:+,.0f}"
        elif action == "factory":
            from src.ai.factory import auto_evolve
            auto_evolve(symbol=arg, generations=3)
            return "[进化] 完成"
        return buf.getvalue() or "[OK]"
    except Exception as e: return f"[失败] {e}"
    finally: sys.stdout = old

@app.route('/api/ai/review')
def api_ai_review():
    try:
        from src.ai.assistants import AITradeReviewer
        return jsonify({"review": AITradeReviewer().review()})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/optimize', methods=['POST'])
def api_optimize():
    try:
        import json as _json
        d = request.json
        from src.backtest.optimizer import GridSearch
        gs = GridSearch(d.get("symbol","601398"), "A股", start_date=d.get("start_date","2022-01-01"))
        pg = _json.loads(d.get("params",'{"fast_period":[5,10,20],"slow_period":[20,30,60]}'))
        df = gs.run(d.get("strategy","ma_cross"), pg, verbose=False)
        return jsonify({"count":len(df),"results":df.head(10).to_dict(orient="records") if not df.empty else []})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/evolve', methods=['POST'])
def api_evolve():
    try:
        d = request.json
        from src.ai.factory import auto_evolve
        buf = io.StringIO(); old = sys.stdout; sys.stdout = buf
        auto_evolve(symbol=d.get("symbol","601398"), generations=int(d.get("generations",5)))
        sys.stdout = old
        return jsonify({"result": buf.getvalue()})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/index/compare')
def api_index_compare():
    try:
        buf = io.StringIO(); old = sys.stdout; sys.stdout = buf
        from src.index.rotation import compare_index_strategies
        compare_index_strategies("2022-01-01")
        sys.stdout = old
        return jsonify({"result": buf.getvalue()})
    except Exception as e:
        return jsonify({"error": str(e)})


# ═══════════════════════════════════════════════════════════
# 启动
# ═══════════════════════════════════════════════════════════

if __name__ == '__main__':
    print("\n  ╔══════════════════════════════════════╗")
    print("  ║  LXL·QuantAxis Web 量化平台          ║")
    print("  ║  http://127.0.0.1:5000              ║")
    print("  ║  浏览器打开上面的地址                ║")
    print("  ╚══════════════════════════════════════╝\n")
    app.run(host=SECURITY_SETTINGS.bind_host, port=5000, debug=False)
