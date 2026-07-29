"""
LXL·QuantAxis v5.0 — 完整Web量化平台
TradingView风格 · 全部功能 · 一键启动
"""
import sys, os, json, io, threading, time
sys.path.insert(0, os.path.dirname(__file__))
os.chdir(os.path.dirname(__file__))

from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import threading, time

app = Flask(__name__)

# ═══════════════════════════════════════════════════════════
# Prometheus 监控 (v6.9)
# ═══════════════════════════════════════════════════════════

class MetricsRegistry:
    """轻量 Prometheus 监控"""

    def __init__(self):
        self._lock = threading.Lock()
        # Counter: 信号总数
        self.strategy_signals_total = 0
        self.signals_by_action = {"BUY": 0, "SELL": 0, "HOLD": 0, "SHORT": 0, "COVER": 0}
        # Gauge: 交易延迟(秒)
        self.trade_execution_latency = 0.0
        self._latency_samples = []
        # Gauge: 实时回撤
        self.portfolio_drawdown_percent = 0.0
        self.peak_equity = 0
        # 心跳
        self.last_signal_time = datetime.now()
        self.last_data_update = datetime.now()
        # 启动时间
        self.start_time = datetime.now()

    def inc_signals(self, action: str = "BUY", count: int = 1):
        with self._lock:
            self.strategy_signals_total += count
            self.signals_by_action[action] = self.signals_by_action.get(action, 0) + count
            self.last_signal_time = datetime.now()

    def observe_latency(self, seconds: float):
        with self._lock:
            self.trade_execution_latency = seconds
            self._latency_samples.append(seconds)
            if len(self._latency_samples) > 100:
                self._latency_samples = self._latency_samples[-100:]

    def update_drawdown(self, current_equity: float):
        with self._lock:
            if current_equity > self.peak_equity:
                self.peak_equity = current_equity
                self.portfolio_drawdown_percent = 0.0
            elif self.peak_equity > 0:
                self.portfolio_drawdown_percent = round(
                    (self.peak_equity - current_equity) / self.peak_equity * 100, 2)

    def heartbeat(self):
        self.last_data_update = datetime.now()

    def check_stall(self, timeout_minutes: int = 30) -> dict:
        """检查是否停滞"""
        now = datetime.now()
        signal_age = (now - self.last_signal_time).total_seconds() / 60
        data_age = (now - self.last_data_update).total_seconds() / 60

        stalled = signal_age > timeout_minutes or data_age > timeout_minutes
        return {
            "stalled": stalled,
            "signal_age_minutes": round(signal_age, 1),
            "data_age_minutes": round(data_age, 1),
            "since_last_signal": str(self.last_signal_time)[:19],
            "since_last_data": str(self.last_data_update)[:19],
        }

    def render(self) -> str:
        """Prometheus text format"""
        uptime = (datetime.now() - self.start_time).total_seconds()
        with self._lock:
            lines = [
                "# HELP strategy_signals_total Total number of trading signals.",
                "# TYPE strategy_signals_total counter",
                f"strategy_signals_total {self.strategy_signals_total}",
                f"strategy_signals_total{{action=\"BUY\"}} {self.signals_by_action.get('BUY',0)}",
                f"strategy_signals_total{{action=\"SELL\"}} {self.signals_by_action.get('SELL',0)}",
                f"strategy_signals_total{{action=\"SHORT\"}} {self.signals_by_action.get('SHORT',0)}",
                "",
                "# HELP trade_execution_latency_seconds Trade execution latency.",
                "# TYPE trade_execution_latency_seconds gauge",
                f"trade_execution_latency_seconds {self.trade_execution_latency:.6f}",
                "",
                "# HELP portfolio_drawdown_percent Current portfolio drawdown.",
                "# TYPE portfolio_drawdown_percent gauge",
                f"portfolio_drawdown_percent {self.portfolio_drawdown_percent}",
                "",
                "# HELP quantaxis_uptime_seconds Application uptime.",
                "# TYPE quantaxis_uptime_seconds gauge",
                f"quantaxis_uptime_seconds {uptime:.0f}",
                "",
                "# HELP quantaxis_stall_status 1 if stalled, 0 otherwise.",
                "# TYPE quantaxis_stall_status gauge",
                f"quantaxis_stall_status {1 if self.check_stall()['stalled'] else 0}",
            ]
        return "\n".join(lines) + "\n"


metrics = MetricsRegistry()


def stall_monitor(timeout_minutes: int = 30):
    """后台停滞监控线程"""
    while True:
        time.sleep(60)  # 每分钟检查一次
        status = metrics.check_stall(timeout_minutes)
        if status["stalled"]:
            from src.audit.TradeAudit import audit
            audit.send_alert(
                "⚠️ 策略停滞告警",
                f"超过{timeout_minutes}分钟无交易信号或数据更新\n"
                f"最后信号: {status['since_last_signal']}\n"
                f"最后数据: {status['since_last_data']}\n"
                f"可能原因: 逻辑死锁 / 数据断流 / 网络异常"
            )


# 启动监控线程
_stall_thread = threading.Thread(target=stall_monitor, args=(30,), daemon=True)
_stall_thread.start()


# ═══════════════════════════════════════════════════════════
# 完整单页HTML
# ═══════════════════════════════════════════════════════════

HTML = r'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>LXL·QuantAxis v5.0</title>
<script src="https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js"></script>
<style>
:root{
--bg:#0d1117;--bg2:#161b22;--bg3:#21262d;--border:#30363d;--ac:#58a6ff;--gr:#3fb950;
--rd:#f85149;--yw:#d2991d;--pr:#bc8cff;--t1:#e6edf3;--t2:#8b949e;--t3:#484f58;
--radius:8px;--shadow:0 4px 24px rgba(0,0,0,.4);
}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif;
background:var(--bg);color:var(--t1);height:100vh;overflow:hidden}
#app{display:flex;height:100vh}
/*== Sidebar ==*/
.sidebar{width:250px;background:var(--bg2);border-right:1px solid var(--border);
display:flex;flex-direction:column;flex-shrink:0}
.sidebar .logo{padding:18px 18px 14px;border-bottom:1px solid var(--border)}
.sidebar .logo h1{font-size:17px;font-weight:700;color:var(--t1)}
.sidebar .logo h1 span{color:var(--ac)}
.sidebar .logo p{font-size:10px;color:var(--t3);margin-top:3px}
.sidebar .nav{flex:1;overflow-y:auto;padding:6px 0}
.nav-grp{padding:10px 16px 3px;font-size:10px;font-weight:600;text-transform:uppercase;
letter-spacing:1.5px;color:var(--t3)}
.nav-item{display:flex;align-items:center;gap:8px;padding:9px 16px;margin:1px 8px;
border-radius:6px;cursor:pointer;font-size:13px;color:var(--t2);transition:all .15s;
border-left:2px solid transparent;user-select:none}
.nav-item:hover{background:var(--bg3);color:var(--t1)}
.nav-item.active{background:var(--bg3);color:var(--t1);border-left-color:var(--ac)}
.nav-item .nicon{font-size:15px;width:18px;text-align:center;flex-shrink:0}
.sidebar .footer{padding:14px 18px;border-top:1px solid var(--border);font-size:10px;color:var(--t3)}
.dot{display:inline-block;width:5px;height:5px;border-radius:50%;margin-right:5px}
.dot.live{background:var(--gr);animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}
/*== Main ==*/
.main{flex:1;display:flex;flex-direction:column;overflow:hidden}
.topbar{display:flex;align-items:center;padding:12px 20px;border-bottom:1px solid var(--border);
background:var(--bg2);gap:12px;flex-shrink:0}
.search-box{flex:1;max-width:420px;position:relative}
.search-box input{width:100%;padding:8px 14px 8px 34px;background:var(--bg);
border:1px solid var(--border);border-radius:6px;color:var(--t1);font-size:13px;outline:none}
.search-box input:focus{border-color:var(--ac)}
.search-box .sicon{position:absolute;left:10px;top:9px;color:var(--t3);font-size:13px}
.suggestions{position:absolute;top:100%;left:0;right:0;background:var(--bg2);
border:1px solid var(--border);border-radius:6px;max-height:260px;overflow-y:auto;
display:none;z-index:999;margin-top:2px}
.suggestions.show{display:block}
.s-item{padding:8px 14px;cursor:pointer;font-size:12px;border-bottom:1px solid var(--border);
display:flex;justify-content:space-between;transition:background .1s}
.s-item:hover{background:var(--bg3)}
.s-item .scode{color:var(--ac);font-weight:600}
.status-bar{margin-left:auto;font-size:11px;color:var(--t3);display:flex;align-items:center;gap:12px}
/*== Content ==*/
.content{flex:1;overflow-y:auto;padding:20px 24px}
.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:20px}
.kpi{background:var(--bg2);border:1px solid var(--border);border-radius:var(--radius);
padding:18px 22px;position:relative;overflow:hidden}
.kpi::before{content:'';position:absolute;top:0;left:0;right:0;height:2px}
.kpi.k1::before{background:var(--ac)}.kpi.k2::before{background:var(--pr)}
.kpi.k3::before{background:var(--gr)}.kpi.k4::before{background:var(--yw)}
.kpi .klabel{font-size:10px;text-transform:uppercase;letter-spacing:1px;color:var(--t3);margin-bottom:4px}
.kpi .kval{font-size:26px;font-weight:700;font-variant-numeric:tabular-nums}
.kpi .ksub{font-size:10px;color:var(--t3);margin-top:3px}
/*== Grids & Cards ==*/
.g2{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.g3{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}
.card{background:var(--bg2);border:1px solid var(--border);border-radius:var(--radius);padding:20px}
.card h3{font-size:14px;font-weight:600;margin-bottom:14px}
.card .sub{font-size:11px;color:var(--t3);margin-top:-10px;margin-bottom:14px}
/*== Chart ==*/
#tvchart{height:380px;border-radius:var(--radius);overflow:hidden;border:1px solid var(--border)}
.chart-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px}
.chart-header .sym-info{font-size:14px;font-weight:600}
.chart-header .sym-info .price{color:var(--ac);margin-left:8px}
/*== Forms ==*/
.frow{display:flex;gap:10px;margin-bottom:10px;align-items:flex-end;flex-wrap:wrap}
.fg{display:flex;flex-direction:column;gap:3px}
.fg label{font-size:10px;color:var(--t3);text-transform:uppercase;letter-spacing:.5px}
.fg input,.fg select{padding:7px 10px;background:var(--bg);border:1px solid var(--border);
border-radius:5px;color:var(--t1);font-size:12px;outline:none}
.fg input:focus,.fg select:focus{border-color:var(--ac)}
/*== Buttons ==*/
.btn{padding:8px 18px;border:none;border-radius:5px;font-size:12px;font-weight:600;cursor:pointer;
transition:all .15s;white-space:nowrap}
.btn-p{background:var(--ac);color:#fff}.btn-p:hover{filter:brightness(1.2)}
.btn-s{background:var(--gr);color:#fff}.btn-s:hover{filter:brightness(1.2)}
.btn-o{background:transparent;border:1px solid var(--border);color:var(--t2)}
.btn-o:hover{border-color:var(--ac);color:var(--t1)}
.btn-sm{padding:5px 12px;font-size:11px}
/*== Table ==*/
table{width:100%;border-collapse:collapse;font-size:12px}
th{text-align:left;padding:8px 12px;font-size:10px;text-transform:uppercase;letter-spacing:.5px;
color:var(--t3);border-bottom:2px solid var(--border);font-weight:600}
td{padding:7px 12px;border-bottom:1px solid var(--border);color:var(--t2)}
tr:hover td{background:rgba(88,166,255,.03)}
.cg{color:var(--gr)}.cr{color:var(--rd)}.cb{color:var(--ac)}.cy{color:var(--yw)}.cp{color:var(--pr)}
/*== Console ==*/
.console{background:var(--bg);border:1px solid var(--border);border-radius:var(--radius);
padding:14px 16px;font-family:'SF Mono','Cascadia Code','Consolas',monospace;
font-size:11px;color:var(--t2);max-height:400px;overflow-y:auto;white-space:pre-wrap;
line-height:1.5;tab-size:2}
.console .ok{color:var(--gr)}.console .err{color:var(--rd)}.console .warn{color:var(--yw)}.console .info{color:var(--ac)}
/*== Tabs ==*/
.tabs{display:flex;gap:0;margin-bottom:16px;border-bottom:2px solid var(--border)}
.tab{padding:8px 18px;font-size:12px;color:var(--t2);cursor:pointer;border-bottom:2px solid transparent;
margin-bottom:-2px;transition:all .15s}
.tab:hover{color:var(--t1)}
.tab.active{color:var(--ac);border-bottom-color:var(--ac)}
/*== Scroll ==*/
::-webkit-scrollbar{width:5px;height:5px}
::-webkit-scrollbar-track{background:transparent}
::-webkit-scrollbar-thumb{background:var(--border);border-radius:3px}
::-webkit-scrollbar-thumb:hover{background:var(--t3)}
/*== Toast ==*/
.toast{position:fixed;bottom:20px;right:20px;padding:10px 18px;border-radius:6px;
font-size:12px;color:#fff;z-index:9999;animation:slideUp .3s ease}
.toast.ok{background:var(--gr)}.toast.err{background:var(--rd)}
@keyframes slideUp{from{transform:translateY(16px);opacity:0}to{transform:translateY(0);opacity:1}}
@media(max-width:1100px){.kpis{grid-template-columns:repeat(2,1fr)}.g2{grid-template-columns:1fr}}
</style>
</head>
<body>
<div id="app">
<div class="sidebar">
<div class="logo"><h1>LXL<span>·</span>QuantAxis</h1><p>量化交易平台 v5.0</p></div>
<div class="nav" id="nav"></div>
<div class="footer"><span class="dot live"></span>5533只A股 · 11个策略 · 实时数据</div>
</div>
<div class="main">
<div class="topbar">
<div class="search-box">
<span class="sicon">🔍</span>
<input type="text" id="globalSearch" placeholder="搜索: 600498 烽火通信 / 茅台 / 宁德..." autocomplete="off">
<div class="suggestions" id="suggestions"></div>
</div>
<div class="status-bar">
<span id="statusText">就绪</span>
<span id="statusTime"></span>
</div>
</div>
<div class="content" id="content"></div>
</div>
</div>
<div id="toasts"></div>

<script>
// ═══════════════ State ═══════════════
const S={panel:'dashboard',sym:'600498',sname:'',data:null};

// ═══════════════ Navigation ═══════════════
const NAV=[
{sec:'总览',items:[{id:'dashboard',ic:'📊',lb:'仪表盘'}]},
{sec:'交易实战',items:[
{id:'backtest',ic:'🧪',lb:'快速回测'},
{id:'diagnosis',ic:'🩺',lb:'个股诊断'},
{id:'recommend',ic:'💡',lb:'智能推荐'},
{id:'scan',ic:'🔄',lb:'每日快扫'},
]},
{sec:'策略与因子',items:[
{id:'strategies',ic:'📈',lb:'策略列表'},
{id:'factors',ic:'🧬',lb:'因子体系'},
{id:'factor_builder',ic:'🔧',lb:'因子策略构建器'},
{id:'strategy_lab',ic:'🧪',lb:'AI策略战法'},
{id:'strategy_bank',ic:'🏦',lb:'我的策略银行'},
]},
{sec:'指数',items:[{id:'valuation',ic:'📊',lb:'指数估值'}]},
{sec:'数据',items:[{id:'database',ic:'🗄️',lb:'数据库管理'}]},
{sec:'AI智能',items:[
{id:'aichat',ic:'🤖',lb:'AI对话'},
{id:'aireview',ic:'📝',lb:'AI复盘'},
{id:'aimarket',ic:'📰',lb:'AI市场简报'},
]},
];
function buildNav(){
const n=document.getElementById('nav');
NAV.forEach(g=>{
const s=document.createElement('div');s.className='nav-grp';s.textContent=g.sec;n.appendChild(s);
g.items.forEach(it=>{
const el=document.createElement('div');
el.className='nav-item';el.id='nav-'+it.id;
el.innerHTML=`<span class="nicon">${it.ic}</span>${it.lb}`;
el.onclick=()=>switchTo(it.id);
n.appendChild(el);
});
});
document.getElementById('nav-dashboard').classList.add('active');
}
async function switchTo(id){
S.panel=id;
document.querySelectorAll('.nav-item').forEach(x=>x.classList.remove('active'));
const target=document.getElementById('nav-'+id);
if(target)target.classList.add('active');
await renderPanel(id);
}

// ═══════════════ API ═══════════════
async function api(url,data=null){
const o=data?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)}:{};
const r=await fetch(url,o);return r.json();
}
function toast(msg,ok=true){
const t=document.createElement('div');t.className='toast '+(ok?'ok':'err');t.textContent=msg;
document.getElementById('toasts').appendChild(t);setTimeout(()=>t.remove(),2500);
}
function updateStatus(txt){document.getElementById('statusText').textContent=txt;}
setInterval(()=>{document.getElementById('statusTime').textContent=new Date().toLocaleTimeString();},1000);

// ═══════════════ Panel Rendering ═══════════════
async function renderPanel(id){
const c=document.getElementById('content');
switch(id){
case 'dashboard':c.innerHTML=buildDashboard();refreshKPIs();loadChart();loadStratDropdown('quickStrat');break;
case 'backtest':c.innerHTML=buildBacktest();loadStratDropdown('btStrat');lookupStock('btSym','btName');break;
case 'diagnosis':c.innerHTML=buildDiagnosis();lookupStock('diagSym','diagName');break;
case 'recommend':c.innerHTML=buildRecommend();break;
case 'scan':c.innerHTML=buildScan();break;
case 'strategies':c.innerHTML=buildStrategies();loadStrategies();break;
case 'factors':c.innerHTML=buildFactors();loadFactors();break;
case 'factor_builder':c.innerHTML=buildFactorBuilder();loadFactorBuilder();break;
case 'strategy_lab':c.innerHTML=buildStrategyLab();break;
case 'strategy_bank':c.innerHTML=buildStrategyBank();loadStrategyBank();break;
case 'valuation':c.innerHTML=buildValuation();loadValuation();break;
case 'database':c.innerHTML=buildDatabase();loadDatabase();break;
case 'aichat':c.innerHTML=buildAIChat();break;
case 'aireview':c.innerHTML=buildAIReview();break;
case 'aimarket':c.innerHTML=buildAIMarket();break;
}
}

// ═══════════════ Dashboard ═══════════════
function buildDashboard(){
return `<div class="kpis" id="kpiRow">
<div class="kpi k1"><div class="klabel">交易记录</div><div class="kval cb" id="kpiT">--</div><div class="ksub">总交易笔数</div></div>
<div class="kpi k2"><div class="klabel">当前持仓</div><div class="kval cp" id="kpiP">--</div><div class="ksub">活跃持仓数</div></div>
<div class="kpi k3"><div class="klabel">持仓盈亏</div><div class="kval cg" id="briefPnl">--</div><div class="ksub" id="briefDate">--</div></div>
<div class="kpi k4"><div class="klabel">回测次数</div><div class="kval cy" id="kpiB">--</div><div class="ksub">已完成回测</div></div>
</div>
<div class="g2">
<div class="card"><h3>📦 我的持仓</h3><div class="sub">实时健康监测 · 自动风险预警</div><div id="briefPositions">加载中...</div></div>
<div class="card"><h3>🔥 今日强势股</h3><div class="sub">因子评分排名 · 买入信号筛选</div><div id="briefStrong">加载中...</div></div>
</div>
<div class="g2" style="margin-top:14px">
<div class="card">
<div class="chart-header"><span class="sym-info" id="chartTitle">📈 K线图</span></div><div id="tvchart"></div>
</div>
<div class="card"><h3>🧪 快速回测</h3>
<div class="frow"><div class="fg"><label>股票代码</label><input id="quickSym" value="600498" oninput="lookupStock('quickSym','quickName')" style="width:100px"></div>
<div class="fg"><label>名称</label><input id="quickName" readonly style="width:100px;background:var(--bg)"></div>
<div class="fg"><label>策略</label><select id="quickStrat" style="width:130px"></select></div></div>
<div class="frow"><div class="fg"><label>起始日期</label><input id="quickDate" value="2024-01-01" type="date" style="width:130px"></div>
<div class="fg"><label>&nbsp;</label><button class="btn btn-p" onclick="runQuickBT()">▶ 回测</button></div></div>
<div class="console" id="quickResult">选择股票和策略,点击回测查看结果</div></div>
</div>`;
}
async function refreshKPIs(){
try{const d=await api('/api/status');
document.getElementById('kpiT').textContent=d.trades||0;
document.getElementById('kpiP').textContent=d.positions||0;
const pnl=d.total_pnl||0;const el=document.getElementById('kpiPL');
el.textContent='¥'+pnl.toLocaleString();el.className='kval '+(pnl>=0?'cg':'cr');
document.getElementById('kpiB').textContent=d.backtests||0;}catch(e){}
// Auto-load daily brief
loadDailyBrief();
}
async function loadDailyBrief(){
try{const r=await api('/api/daily_brief');
const el=document.getElementById('dailyBrief');if(!el)return;
let h='';
if(r.positions&&r.positions.length){
h+=`<table><thead><tr><th>持仓</th><th>成本</th><th>现价</th><th>盈亏</th><th>健康度</th><th>建议</th></tr></thead><tbody>`;
r.positions.forEach(p=>{
const cls=p.pnl_pct>=0?'cg':'cr';const hcls=p.health>40?'cg':(p.health>20?'cy':'cr');
h+=`<tr><td>${p.symbol} ${p.name||''}</td><td>¥${p.cost}</td><td>¥${p.price}</td>
<td class="${cls}">${p.pnl_pct>=0?'+':''}${p.pnl_pct}%</td>
<td class="${hcls}">${p.health}分</td><td>${p.action}</td></tr>`;});
h+='</tbody></table>';
}else{h='<p style="color:var(--t3)">暂无持仓</p>';}
document.getElementById('briefPositions').innerHTML=h;
// Strong stocks
if(r.strong_stocks&&r.strong_stocks.length){
let sh='<table><thead><tr><th>代码</th><th>价格</th><th>评分</th><th>RSI</th><th>均线</th></tr></thead><tbody>';
r.strong_stocks.forEach(s=>{
sh+=`<tr><td class="cb">${s.symbol}</td><td>¥${s.price}</td><td class="cg">${s.score}分</td><td>${s.rsi}</td><td>${s.ma}</td></tr>`;});
sh+='</tbody></table>';
document.getElementById('briefStrong').innerHTML=sh;
}
document.getElementById('briefDate').textContent=r.date||'';
if(r.total_pnl!==undefined){
const pe=document.getElementById('briefPnl');
if(pe){pe.textContent='¥'+(r.total_pnl||0).toLocaleString();pe.className=r.total_pnl>=0?'cg':'cr';}
}
}catch(e){}
}
async function runQuickBT(){
const sym=document.getElementById('quickSym')?.value||'600498';
const strat=document.getElementById('quickStrat')?.value||'ma_cross';
const date=document.getElementById('quickDate')?.value||'2024-01-01';
const el=document.getElementById('quickResult');
el.innerHTML='<span class="info">⏳ 运行中...</span>';
try{const r=await api('/api/backtest',{symbol:sym,strategy:strat,start_date:date});
if(r.error){el.innerHTML=`<span class="err">❌ ${r.error}</span>`;return}
let h=`<span class="ok">✅ 回测完成</span> | ${r.data_rows}条 | ${r.date_range}\n\n═══ 绩效指标 ═══\n`;
if(r.metrics)for(const[k,v]of Object.entries(r.metrics))h+=`${k}: ${v}\n`;
if(r.trades){h+=`\n── 最近交易 ──\n`;r.trades.forEach(t=>{h+=`${t.date} ${t.action} ¥${t.price}×${t.qty}\n`;});}
el.innerHTML=h;toast('回测完成!');}catch(e){el.innerHTML=`<span class="err">❌ ${e}</span>`}
}

// ═══════════════ Charts ═══════════════
let chart=null,cs=null;
async function loadChart(sym){
sym=sym||S.sym;
document.getElementById('chartTitle').innerHTML=`📈 ${sym} ${S.sname} <span class="price">K线图</span>`;
try{const d=await api('/api/chart_data?symbol='+sym);
if(!d.data||!d.data.length)return;
const ct=document.getElementById('tvchart');
if(chart){chart.remove();chart=null;}
chart=LightweightCharts.createChart(ct,{
layout:{background:{color:'#161b22'},textColor:'#8b949e'},
grid:{vertLines:{color:'#21262d'},horzLines:{color:'#21262d'}},
crosshair:{mode:0},rightPriceScale:{borderColor:'#30363d'},
timeScale:{borderColor:'#30363d',timeVisible:true},
width:ct.clientWidth,height:ct.clientHeight,
});
cs=chart.addCandlestickSeries({
upColor:'#3fb950',downColor:'#f85149',borderUpColor:'#3fb950',borderDownColor:'#f85149',
wickUpColor:'#3fb950',wickDownColor:'#f85149',
});
cs.setData(d.data.map(r=>({time:r.time,open:r.open,high:r.high,low:r.low,close:r.close})));
chart.timeScale().fitContent();
}catch(e){console.error(e)}
}
window.addEventListener('resize',()=>{if(chart){const ct=document.getElementById('tvchart');chart.resize(ct.clientWidth,ct.clientHeight);}});

// ═══════════════ Backtest Panel ═══════════════
function buildBacktest(){
return `<div class="g2"><div class="card"><h3>🧪 快速回测</h3><div class="sub">选股票 · 选策略 · 看结果</div>
<div class="frow"><div class="fg"><label>股票代码</label><input id="btSym" value="600498" oninput="lookupStock('btSym','btName')" style="width:100px"></div>
<div class="fg"><label>名称</label><input id="btName" readonly style="width:110px;background:var(--bg)"></div>
<div class="fg"><label>起始日期</label><input id="btStart" value="2024-01-01" type="date"></div>
<div class="fg"><label>截止日期(可选)</label><input id="btEnd" type="date"></div></div>
<div class="frow"><div class="fg"><label>策略</label><select id="btStrat" style="width:160px"></select></div>
<div class="fg"><label>&nbsp;</label><button class="btn btn-p" onclick="runBT()">▶ 运行回测</button></div></div>
<div class="console" id="btResult" style="max-height:300px">输入参数,点击运行回测...</div></div>
<div class="card"><h3>📊 回测权益曲线</h3><div id="btChart" style="height:360px;border-radius:8px;overflow:hidden;border:1px solid var(--border)"></div></div></div>`;
}
async function runBT(){
const sym=document.getElementById('btSym')?.value||'600498';
const strat=document.getElementById('btStrat')?.value||'ma_cross';
const start=document.getElementById('btStart')?.value||'2024-01-01';
const end=document.getElementById('btEnd')?.value||null;
const el=document.getElementById('btResult');
el.innerHTML='<span class="info">⏳ 运行中...</span>';updateStatus('回测中...');
try{const r=await api('/api/backtest',{symbol:sym,strategy:strat,start_date:start,end_date:end});
if(r.error){el.innerHTML=`<span class="err">❌ ${r.error}</span>`;updateStatus('错误');return}
let h=`<span class="ok">✅ ${sym} @ ${strat}</span> | ${r.data_rows}条 | ${r.date_range}\n\n═══ 指标 ═══\n`;
if(r.metrics)for(const[k,v]of Object.entries(r.metrics))h+=`${k}: ${v}\n`;
if(r.trades){h+=`\n── 最近交易(${r.trades.length}笔) ──\n`;r.trades.forEach(t=>{h+=`${t.date} ${t.action} ¥${t.price}×${t.qty}\n`;});}
el.innerHTML=h;updateStatus('回测完成');toast('回测完成!');
if(r.equity)drawEquityChart(r.equity);
}catch(e){el.innerHTML=`<span class="err">❌ ${e}</span>`;updateStatus('失败')}
}

// ═══════════════ Smart Recommend ═══════════════
function buildRecommend(){
return `<div class="card"><h3>💡 智能推荐</h3><div class="sub">全策略扫描 → 最优策略 → 买卖价位 → AI顾问讨论</div>
<div class="frow"><div class="fg"><label>股票代码</label><input id="recSym" value="600498" oninput="lookupStock('recSym','recName')" style="width:100px"></div>
<div class="fg"><label>名称</label><input id="recName" readonly style="width:120px;background:var(--bg)"></div>
<div class="fg"><label>&nbsp;</label><button class="btn btn-p" onclick="runRecommend()">▶ 获取推荐</button></div></div>
<div class="console" id="recResult" style="max-height:320px;font-size:13px;line-height:1.8;margin-bottom:14px">
点击获取推荐 — 系统将自动运行全部策略,匹配最优方案,给出具体买卖价位</div>
<h3 style="margin-bottom:10px">💬 和AI讨论你的思路</h3>
<div class="sub" style="margin-bottom:10px">在下方输入你的交易想法,AI会根据上面的推荐结果帮你分析是否可行、匹配什么策略</div>
<div class="console" id="recChat" style="max-height:200px;min-height:100px;margin-bottom:8px;font-size:12px">
AI顾问: 先点"获取推荐",然后告诉我你的想法,我来帮你分析。</div>
<div style="display:flex;gap:8px">
<input id="recMsg" placeholder="输入你的思路... 如: 我想在回调到30块时抄底,持有2周" style="flex:1"
onkeypress="if(event.key==='Enter')sendRecChat()">
<button class="btn btn-p" onclick="sendRecChat()">发送</button></div></div>`;
}
async function runRecommend(){
const sym=document.getElementById('recSym')?.value||'600498';
const el=document.getElementById('recResult');
el.innerHTML='<span class="info">正在分析: 运行15个策略 + 18个因子...</span>';updateStatus('智能推荐中...');
try{const r=await api('/api/recommend',{symbol:sym});
if(r.error){el.innerHTML=`<span class="err">${r.error}</span>`;return}
el.innerHTML=r.report;
// Store context for AI chat
window._recContext={symbol:sym,report:r.report};
document.getElementById('recChat').innerHTML='AI顾问: 推荐已生成。告诉我你的交易思路,我帮你分析是否可行、匹配什么策略。';
updateStatus('推荐完成');toast('推荐完成!');
}catch(e){el.innerHTML=`<span class="err">${e}</span>`;updateStatus('失败')}
}
async function sendRecChat(){
const msg=document.getElementById('recMsg')?.value.trim();if(!msg)return;
const chat=document.getElementById('recChat');
chat.innerHTML+=`\n<span style="color:var(--ac)">你: ${msg}</span>\n`;
chat.innerHTML+='<span style="color:var(--t3)">AI: 分析中...</span>\n';
chat.scrollTop=chat.scrollHeight;
document.getElementById('recMsg').value='';
const ctx=window._recContext||{};
try{
const r=await api('/api/ai/recommend_chat',{
message:msg,
symbol:ctx.symbol||'',
context:ctx.report||''
});
chat.innerHTML=chat.innerHTML.replace('AI: 分析中...\n','');
chat.innerHTML+=`<span style="color:var(--gr)">AI: ${r.reply}</span>\n`;
chat.scrollTop=chat.scrollHeight;
}catch(e){
chat.innerHTML=chat.innerHTML.replace('AI: 分析中...\n','');
chat.innerHTML+=`<span class="err">AI: 连接失败,请先配置AI密钥</span>\n`;
}
}

// ═══════════════ Diagnosis Panel ═══════════════
function buildDiagnosis(){
return `<div class="card"><h3>🩺 个股诊断</h3><div class="sub">全策略扫描 · 投资者适配 · 入场时机 · 仓位建议</div>
<div class="frow"><div class="fg"><label>股票代码</label><input id="diagSym" value="600498" oninput="lookupStock('diagSym','diagName')" style="width:100px"></div>
<div class="fg"><label>名称</label><input id="diagName" readonly style="width:120px;background:var(--bg)"></div>
<div class="fg"><label>起始日期</label><input id="diagStart" value="2022-01-01" type="date"></div>
<div class="fg"><label>&nbsp;</label><button class="btn btn-s" onclick="runDiag()">▶ 开始诊断</button></div></div>
<div class="console" id="diagResult" style="max-height:520px">输入股票代码,点击开始诊断 (11个策略+18个因子)...</div></div>`;
}
async function runDiag(){
const sym=document.getElementById('diagSym')?.value||'600498';
const start=document.getElementById('diagStart')?.value||'2022-01-01';
const el=document.getElementById('diagResult');
el.innerHTML='<span class="info">⏳ 诊断中 (11策略回测+18因子分析)...</span>';updateStatus('诊断中...');
try{const r=await api('/api/diagnosis',{symbol:sym,start_date:start});
if(r.error){el.innerHTML=`<span class="err">❌ ${r.error}</span>`;updateStatus('错误');return}
el.innerHTML=r.report;updateStatus('诊断完成');toast('诊断完成!');
}catch(e){el.innerHTML=`<span class="err">❌ ${e}</span>`;updateStatus('失败')}
}

// ═══════════════ Daily Scan ═══════════════
function buildScan(){
return `<div class="card"><h3>🔄 每日快扫</h3><div class="sub">13只默认标的 · 自动刷新行情 · 因子评分排名</div>
<div class="frow"><button class="btn btn-p" onclick="runScan('quick')">⚡ 快速扫描(因子评分)</button>
<button class="btn btn-o" onclick="runScan('full')">🔬 完整诊断(含策略回测)</button></div>
<div class="console" id="scanResult" style="max-height:500px;margin-top:12px">点击扫描...</div></div>`;
}
async function runScan(mode){
const el=document.getElementById('scanResult');
el.innerHTML='<span class="info">⏳ 扫描中...</span>';updateStatus('扫描中...');
try{const r=await api('/api/daily_scan',{full:mode==='full'});
if(r.error){el.innerHTML=`<span class="err">❌ ${r.error}</span>`;return}
let h=`<span class="ok">✅ 扫描完成</span> | ${r.count}只标的\n\n`;
h+=`信号: <span class="cg">🟢${r.summary?.buy||0}只</span> <span class="cy">⚪${r.summary?.wait||0}只</span> <span class="cr">🔴${r.summary?.avoid||0}只</span>\n\n`;
if(r.results){h+=`── 排名 ──\n`;r.results.forEach((s,i)=>{
const cls=s.score>=60?'cg':(s.score>=40?'cy':'cr');
h+=`${i+1}. ${s.symbol} ${s.name||''} ¥${s.price} <span class="${cls}">${s.score}分 ${s.level||''}</span>\n`;
});}
el.innerHTML=h;updateStatus('扫描完成');toast('扫描完成!');
}catch(e){el.innerHTML=`<span class="err">❌ ${e}</span>`;updateStatus('失败')}
}

// ═══════════════ Strategies & Factors ═══════════════
function buildStrategies(){return `<div class="card"><h3>📈 策略列表</h3><div id="stratList">加载中...</div></div>`;}
async function loadStrategies(){
try{const r=await api('/api/strategies');
let h=`<table><thead><tr><th>#</th><th>策略名称</th><th>Key</th><th>描述</th><th>参数范围</th></tr></thead><tbody>`;
r.strategies.forEach((s,i)=>{h+=`<tr><td>${i+1}</td><td>${s.name}</td><td class="cb">${s.key}</td><td style="color:var(--t2)">${s.desc||''}</td><td style="color:var(--t3);font-size:10px">${s.params||''}</td></tr>`;});
h+='</tbody></table>';document.getElementById('stratList').innerHTML=h;}catch(e){}
}
function buildFactors(){return `<div class="card"><h3>🧬 因子体系 (18个)</h3><div id="factorList">加载中...</div></div>`;}
async function loadFactors(){
try{const r=await api('/api/factors');
let h=`<table><thead><tr><th>因子名</th><th>分类</th><th>描述</th></tr></thead><tbody>`;
r.factors.forEach(f=>{h+=`<tr><td class="cb">${f.name}</td><td>${f.category}</td><td style="color:var(--t2)">${f.desc}</td></tr>`;});
h+='</tbody></table>';document.getElementById('factorList').innerHTML=h;}catch(e){}
}
function buildValuation(){return `<div class="card"><h3>📊 指数估值</h3><div id="valContent">加载中...</div></div>`;}
function buildStrategyBank(){return `<div class="card"><h3>🏦 我的策略银行</h3><div class="sub">你创建的所有策略 · 回测记录 · 收藏复用</div>
<div id="bankContent">加载中...</div></div>`;}
async function loadStrategyBank(){
try{const r=await api('/api/strategy_bank');
if(!r.strategies||!r.strategies.length){document.getElementById('bankContent').innerHTML='<p style="color:var(--t3)">策略银行是空的。去 AI策略战法 或 因子策略构建器 创建你的第一个策略吧!</p>';return}
let h=`<p style="color:var(--t2);margin-bottom:12px">共 <b>${r.stats?.strategies||0}</b> 个策略 | ${r.stats?.backtests||0} 次回测 | ${r.stats?.notes||0} 条笔记</p>`;
h+='<table><thead><tr><th>#</th><th>策略名</th><th>逻辑</th><th>因子数</th><th>标签</th><th>创建时间</th><th>操作</th></tr></thead><tbody>';
r.strategies.forEach((s,i)=>{
h+=`<tr><td>${i+1}</td><td class="cb">${s.name}</td><td>${s.logic}≥${s.threshold}</td>
<td>${s.conditions?.length||0}</td><td style="font-size:10px">${s.tags||''}</td><td style="font-size:10px;color:var(--t3)">${(s.created_at||'').slice(0,10)}</td>
<td><button class="btn btn-sm btn-o" onclick="loadStrategyDetail(${s.id})">查看</button>
<button class="btn btn-sm btn-o" onclick="deleteStrategy(${s.id})">删除</button></td></tr>`;
});
h+='</tbody></table><div id="bankDetail" style="margin-top:14px"></div>';
document.getElementById('bankContent').innerHTML=h;}catch(e){}
}
async function loadStrategyDetail(sid){
try{const r=await api('/api/strategy_bank/'+sid);
if(!r.strategy)return;
let h=`<div class="card"><h4>${r.strategy.name}</h4>`;
h+=`<p style="color:var(--t2)">逻辑: ${r.strategy.logic} | 阈值: ${r.strategy.threshold}</p>`;
h+='<p style="color:var(--t2)">因子条件:</p><ul>';
r.strategy.conditions.forEach(c=>{h+=`<li>${c.factor} ${c.operator} ${c.threshold} (权重${c.weight})</li>`;});
h+='</ul>';
if(r.backtests&&r.backtests.length){
h+='<p style="color:var(--t2);margin-top:8px">回测记录:</p><table><thead><tr><th>标的</th><th>夏普</th><th>收益</th><th>回撤</th><th>胜率</th><th>时间</th></tr></thead><tbody>';
r.backtests.forEach(b=>{h+=`<tr><td>${b.symbol}</td><td>${b.sharpe?.toFixed(2)||'-'}</td><td>${b.total_return||'-'}</td><td>${b.max_dd||'-'}</td><td>${b.win_rate||'-'}</td><td style="font-size:10px;color:var(--t3)">${(b.run_at||'').slice(0,16)}</td></tr>`;});
h+='</tbody></table>';}
h+='</div>';document.getElementById('bankDetail').innerHTML=h;}catch(e){}
}
async function deleteStrategy(sid){if(confirm('确定删除这个策略?')){await api('/api/strategy_bank/'+sid,{method:'DELETE'});loadStrategyBank();}}
function buildDatabase(){return `<div class="card"><h3>🗄️ 数据库管理</h3><div class="sub">SQLite统一行情库 · 30,000+条数据 · 替代CSV缓存</div>
<div class="frow"><button class="btn btn-p" onclick="loadDatabase()">刷新</button>
<button class="btn btn-o" onclick="migrateData()">从CSV迁移数据</button></div>
<div id="dbContent" style="margin-top:12px">加载中...</div></div>`;}
function buildDatabase(){return `<div class="card"><h3>🗄️ 数据库管理</h3><div class="sub">SQLite统一行情库 · 30,000+条数据 · 替代CSV缓存</div>
<div class="frow"><button class="btn btn-p" onclick="loadDatabase()">刷新</button>
<button class="btn btn-o" onclick="migrateData()">从CSV迁移数据</button></div>
<div id="dbContent" style="margin-top:12px">加载中...</div></div>`;}
async function loadDatabase(){
try{const r=await api('/api/database/status');
let h=`<table><thead><tr><th>代码</th><th>市场</th><th>起始日期</th><th>最新日期</th><th>数据条数</th><th>更新时间</th></tr></thead><tbody>`;
if(r.stocks)r.stocks.forEach(s=>{
h+=`<tr><td class="cb">${s.symbol}</td><td>${s.market}</td><td>${s.first_date}</td><td>${s.last_date}</td><td>${s.row_count}</td><td style="font-size:10px;color:var(--t3)">${s.updated_at||''}</td></tr>`;
});
h+='</tbody></table>';
h+=`<p style="margin-top:12px;color:var(--t2)">总计: <b>${r.total_stocks||0}</b> 只股票, <b>${r.total_rows||0}</b> 条数据 | 数据库: ${r.db_path||''}</p>`;
document.getElementById('dbContent').innerHTML=h;}catch(e){}
}
async function migrateData(){
document.getElementById('dbContent').innerHTML='<span class="info">迁移中...</span>';
try{const r=await api('/api/database/migrate');
document.getElementById('dbContent').innerHTML=`<span class="ok">迁移完成! 处理了${r.count||0}个文件</span>`;
loadDatabase();}catch(e){document.getElementById('dbContent').innerHTML=`<span class="err">${e}</span>`}
}
return `<div class="card"><h3>🤖 AI 量化助手</h3><div class="sub">和AI聊量化 · 策略 · 市场 · 复盘</div>
<div style="display:flex;gap:8px;margin-bottom:12px">
<input id="aiMsg" placeholder="输入问题... 如: 分析一下最近的行情" style="flex:1"
onkeypress="if(event.key==='Enter')sendAI()">
<button class="btn btn-p" onclick="sendAI()">发送</button></div>
<div style="display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap">
<button class="btn btn-sm btn-o" onclick="quickAI('跑回测 600498')">跑回测</button>
<button class="btn btn-sm btn-o" onclick="quickAI('看估值')">看估值</button>
<button class="btn btn-sm btn-o" onclick="quickAI('系统状态')">系统状态</button>
<button class="btn btn-sm btn-o" onclick="quickAI('最近什么策略表现好')">策略分析</button>
</div>
<div class="console" id="aiChat" style="max-height:400px;min-height:200px">AI助手就绪,输入问题开始对话...</div></div>`;}
function quickAI(msg){document.getElementById('aiMsg').value=msg;sendAI();}
async function sendAI(){
const msg=document.getElementById('aiMsg')?.value.trim();if(!msg)return;
const el=document.getElementById('aiChat');
el.innerHTML+=`\n<span style="color:var(--ac)">你: ${msg}</span>\n`;
el.innerHTML+='<span style="color:var(--t3)">AI: 思考中...</span>\n';
document.getElementById('aiMsg').value='';
try{const r=await api('/api/ai/chat',{message:msg});
el.innerHTML=el.innerHTML.replace('AI: 思考中...\n','');
el.innerHTML+=`<span style="color:var(--gr)">AI: ${r.reply||'无回复'}</span>\n`;
el.scrollTop=el.scrollHeight;}catch(e){
el.innerHTML=el.innerHTML.replace('AI: 思考中...\n','');
el.innerHTML+=`<span class="err">AI连接失败,请先配置AI</span>\n`;}
}
function buildAIReview(){return `<div class="card"><h3>📝 AI 交易复盘</h3><div class="sub">AI分析你的交易记录,找出行为偏差</div>
<button class="btn btn-p" onclick="runAIReview()">▶ AI复盘</button>
<div class="console" id="aiReviewResult" style="margin-top:12px;max-height:500px">点击按钮,AI将分析交易日志...</div></div>`;}
async function runAIReview(){
const el=document.getElementById('aiReviewResult');
el.innerHTML='<span class="info">AI分析交易记录中...</span>';
try{const r=await api('/api/ai/review');
el.innerHTML=r.review||r.error||'无结果';}catch(e){el.innerHTML=`<span class="err">${e}</span>`}
}
function buildAIMarket(){return `<div class="card"><h3>📰 AI 市场简报</h3><div class="sub">AI生成今日市场概况</div>
<button class="btn btn-p" onclick="runAIMarket()">▶ 生成简报</button>
<div class="console" id="aiMarketResult" style="margin-top:12px;max-height:500px">点击按钮生成市场简报...</div></div>`;}
async function runAIMarket(){
const el=document.getElementById('aiMarketResult');
el.innerHTML='<span class="info">AI生成市场简报...</span>';
try{const r=await api('/api/ai/market');
el.innerHTML=r.brief||r.error||'无结果';}catch(e){el.innerHTML=`<span class="err">${e}</span>`}
}
function buildStrategyLab(){
return `<div class="g2"><div class="card"><h3>🧪 AI策略战法实验室</h3>
<div class="sub">用自然语言描述你的交易思路,AI帮你转成可回测的策略</div>
<div class="frow"><div class="fg"><label>回测股票</label><input id="labSym" value="600498" style="width:100px"></div>
<div class="fg"><label>起始日期</label><input id="labDate" value="2024-01-01" type="date"></div></div>
<div class="frow"><textarea id="labIdea" placeholder="描述你的交易战法...

例如:
- 当5日均线上穿20日均线且成交量放大1.5倍时买入,跌破10日低点卖出
- RSI低于25且出现锤子线时抄底,RSO高于75时分批止盈
- 股价突破60日高点+MACD金叉买入,持有5天无条件卖出
- 每天下午2:30如果当日涨幅超过3%就追涨,第二天开盘卖

越具体越好! AI会理解你的思路并构建策略。"
style="width:100%;height:160px;background:var(--bg);border:1px solid var(--border);border-radius:6px;color:var(--t1);padding:12px;font-size:13px;resize:vertical;font-family:inherit"></textarea></div>
<div class="frow"><button class="btn btn-p" onclick="createStrategy()">🧬 AI生成策略</button>
<button class="btn btn-o" onclick="document.getElementById('labIdea').value=''">清空</button></div>
<div id="labStatus" style="margin-top:8px;font-size:12px;color:var(--t3)"></div></div>
<div class="card"><h3>📋 生成的策略详情</h3>
<div class="console" id="labResult" style="max-height:400px;font-size:12px;line-height:1.6">
AI生成的策略会显示在这里。包括:解析出的因子条件、逻辑规则、回测结果。</div></div></div>`;
}
async function createStrategy(){
const idea=document.getElementById('labIdea')?.value.trim();
if(!idea||idea.length<10){document.getElementById('labStatus').innerHTML='<span class="err">请描述你的交易思路(至少10个字)</span>';return}
const sym=document.getElementById('labSym')?.value||'600498';
const date=document.getElementById('labDate')?.value||'2024-01-01';
const status=document.getElementById('labStatus');
const result=document.getElementById('labResult');
status.innerHTML='<span class="info">AI分析你的思路中...</span>';
result.innerHTML='<span class="info">正在: 1)AI解析战法 2)提取因子条件 3)构建策略 4)回测验证</span>';
updateStatus('AI创建策略...');
try{const r=await api('/api/ai/create_strategy',{idea:idea,symbol:sym,start_date:date});
if(r.error){status.innerHTML=`<span class="err">${r.error}</span>`;result.innerHTML='';return}
status.innerHTML='<span class="ok">策略创建成功!</span>';
let h=`<b>策略名称:</b> ${r.name||'AI策略'}\n\n`;
h+=`<b>AI解析:</b>\n${r.explanation||''}\n\n`;
h+=`<b>因子条件:</b>\n`;
if(r.conditions)r.conditions.forEach(c=>{h+=`  · ${c.factor} ${c.operator} ${c.threshold} (权重${c.weight})\n`;});
h+=`\n<b>买入逻辑:</b> ${r.logic||'weighted'} | 触发阈值: ${r.threshold||'3.0'}\n\n`;
h+=`<b>回测结果 (${sym}):</b>\n`;
if(r.metrics)for(const[k,v]of Object.entries(r.metrics))h+=`  ${k}: ${v}\n`;
if(r.trades){h+=`\n<b>交易记录:</b>\n`;r.trades.forEach(t=>{h+=`  ${t.date} ${t.action} ${t.price}x${t.qty}\n`;});}
result.innerHTML=h;updateStatus('策略创建完成');toast('AI策略创建成功!');
}catch(e){status.innerHTML=`<span class="err">${e}</span>`;updateStatus('失败')}
}

function buildFactorBuilder(){return `<div class="card"><h3>🔧 因子策略构建器</h3><div class="sub">选因子·配权重·建策略·直接回测</div>
<div class="frow"><div class="fg"><label>股票代码</label><input id="fbSym" value="600498" style="width:100px"></div>
<div class="fg"><label>策略名称</label><input id="fbName" value="我的因子策略" style="width:150px"></div>
<div class="fg"><label>逻辑</label><select id="fbLogic"><option value="weighted">Weighted</option><option value="and">AND</option><option value="or">OR</option></select></div>
<div class="fg"><label>阈值</label><input id="fbThresh" value="3.0" style="width:60px"></div>
<div class="fg"><label>&nbsp;</label><button class="btn btn-p" onclick="runFactorBT()">▶ 构建并回测</button></div></div>
<div id="fbFactors" style="margin-bottom:12px">加载因子列表...</div>
<div class="console" id="fbResult" style="max-height:300px">选择因子,设定条件,点击构建并回测</div></div>`;}

async function loadFactorBuilder(){
try{const r=await api('/api/factors');if(!r.factors)return;
let h='<table><thead><tr><th>选择</th><th>因子</th><th>描述</th><th>运算符</th><th>阈值</th><th>权重</th></tr></thead><tbody>';
r.factors.forEach(f=>{h+=`<tr><td><input type="checkbox" id="fb_${f.name}"></td><td class="cb">${f.name}</td><td style="color:var(--t2);font-size:11px">${f.desc}</td>
<td><select id="fbop_${f.name}" style="width:50px;font-size:11px"><option value="lt">lt</option><option value="gt">gt</option></select></td>
<td><input id="fbth_${f.name}" value="0.5" style="width:50px;font-size:11px"></td>
<td><input id="fbw_${f.name}" value="1" style="width:40px;font-size:11px"></td></tr>`;});
h+='</tbody></table>';document.getElementById('fbFactors').innerHTML=h;}catch(e){}
}

async function runFactorBT(){
const sym=document.getElementById('fbSym')?.value||'600498';
const name=document.getElementById('fbName')?.value||'策略';
const logic=document.getElementById('fbLogic')?.value||'weighted';
const thresh=parseFloat(document.getElementById('fbThresh')?.value||'3');
const factors=[];
try{const r=await api('/api/factors');
if(r.factors)r.factors.forEach(f=>{
const cb=document.getElementById('fb_'+f.name);
if(cb&&cb.checked){
factors.push({factor:f.name,operator:document.getElementById('fbop_'+f.name)?.value||'lt',
threshold:parseFloat(document.getElementById('fbth_'+f.name)?.value||'0.5'),
weight:parseFloat(document.getElementById('fbw_'+f.name)?.value||'1')});
}});}catch(e){}
if(!factors.length){document.getElementById('fbResult').innerHTML='<span class="err">请至少选择一个因子</span>';return}
const el=document.getElementById('fbResult');
el.innerHTML='<span class="info">运行中...</span>';updateStatus('因子策略回测中...');
try{const r=await api('/api/factor_backtest',{symbol:sym,name:name,logic:logic,threshold:thresh,factors:factors});
if(r.error){el.innerHTML=`<span class="err">${r.error}</span>`;return}
let h=`<span class="ok">${name}</span> | ${sym} | ${logic}>=${thresh}\n\n═══ 回测结果 ═══\n`;
if(r.metrics)for(const[k,v]of Object.entries(r.metrics))h+=`${k}: ${v}\n`;
el.innerHTML=h;updateStatus('因子策略完成');toast('因子策略回测完成!');
}catch(e){el.innerHTML=`<span class="err">${e}</span>`;updateStatus('失败')}
}
async function loadValuation(){
try{const r=await api('/api/valuation');if(!r.snapshot||!r.snapshot.length){document.getElementById('valContent').innerHTML='<span class="warn">暂无估值数据</span>';return}
let h=`<table><thead><tr><th>指数</th><th>名称</th><th>PE</th><th>PE分位</th><th>PB分位</th><th>评级</th></tr></thead><tbody>`;
r.snapshot.forEach(s=>{h+=`<tr><td>${s['指数']||''}</td><td>${s['名称']||''}</td><td>${s['PE']||'N/A'}</td><td>${s['PE分位']||'N/A'}</td><td>${s['PB分位']||'N/A'}</td><td>${s['PE评级']||'-'}</td></tr>`;});
h+='</tbody></table>';document.getElementById('valContent').innerHTML=h;}catch(e){}
}

// ═══════════════ Stock Search ═══════════════
let searchTimer;
function initSearch(){
const inp=document.getElementById('globalSearch');
inp.addEventListener('input',function(){
clearTimeout(searchTimer);
const q=this.value.trim();
if(q.length<2){document.getElementById('suggestions').classList.remove('show');return}
searchTimer=setTimeout(async()=>{
try{const r=await api('/api/stock/search?q='+encodeURIComponent(q));
const sug=document.getElementById('suggestions');
if(!r.results||!r.results.length){sug.classList.remove('show');return}
sug.innerHTML=r.results.map(s=>`<div class="s-item" onclick="pickStock('${s.code}','${s.name}')"><span class="scode">${s.code}</span><span>${s.name}</span><span style="color:var(--t3)">${s.market||''}</span></div>`).join('');
sug.classList.add('show');}catch(e){}},200);
});
document.addEventListener('click',e=>{if(!e.target.closest('.search-box'))document.getElementById('suggestions')?.classList.remove('show');});
}
function pickStock(code,name){
S.sym=code;S.sname=name;
document.getElementById('globalSearch').value=code+' - '+name;
document.getElementById('suggestions').classList.remove('show');
['btSym','diagSym','quickSym'].forEach(id=>{const el=document.getElementById(id);if(el)el.value=code;});
['btName','diagName','quickName'].forEach(id=>{const el=document.getElementById(id);if(el)el.value=name;});
loadChart(code);toast('已选择: '+code+' '+name);
}
async function lookupStock(inpId,nameId){
const v=document.getElementById(inpId)?.value;if(!v||v.length<4)return;
try{const r=await api('/api/stock/lookup?code='+encodeURIComponent(v));
if(r.name&&r.name!==v)document.getElementById(nameId).value=r.name;}catch(e){}
}
async function loadStratDropdown(id){
try{const r=await api('/api/strategies');if(!r.strategies)return;
document.getElementById(id).innerHTML=r.strategies.map(s=>`<option value="${s.key}">${s.name}</option>`).join('');}catch(e){}
}

// ═══════════════ Init ═══════════════
window.addEventListener('DOMContentLoaded',()=>{
buildNav();initSearch();renderPanel('dashboard');
});
</script>
</body>
</html>'''

# ═══════════════════════════════════════════════════════════
# API Routes (完整)
# ═══════════════════════════════════════════════════════════

@app.route('/')
def index():
    return HTML

@app.route('/metrics')
def api_metrics():
    """Prometheus 格式监控指标"""
    return metrics.render(), 200, {"Content-Type": "text/plain; charset=utf-8"}

@app.route('/api/metrics/update', methods=['POST'])
def api_metrics_update():
    """更新监控指标"""
    d = request.json or {}
    if "signals" in d:
        for action, count in d["signals"].items():
            metrics.inc_signals(action, count)
    if "latency" in d:
        metrics.observe_latency(float(d["latency"]))
    if "equity" in d:
        metrics.update_drawdown(float(d["equity"]))
    if "heartbeat" in d:
        metrics.heartbeat()
    return jsonify({"ok": True})

@app.route('/api/metrics/status')
def api_metrics_status():
    """监控状态摘要"""
    stall = metrics.check_stall()
    return jsonify({
        "signals_total": metrics.strategy_signals_total,
        "drawdown_pct": metrics.portfolio_drawdown_percent,
        "latency": metrics.trade_execution_latency,
        "stalled": stall["stalled"],
        "since_last_signal": stall["since_last_signal"],
        "uptime_seconds": (datetime.now() - metrics.start_time).total_seconds(),
    })

@app.route('/api/status')
def api_status():
    try:
        from src.models.trade import TradeRepository
        from src.backtest.batch_runner import ResultDB
        repo = TradeRepository(); db = ResultDB()
        pnl = [p["net_pnl"] for p in repo.get_all_pnl()]
        return jsonify({"trades": repo.count(), "positions": len(repo.find_open_positions()),
                       "total_pnl": sum(pnl) if pnl else 0,
                       "backtests": db.summary().get("总回测数", 0)})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/backtest', methods=['POST'])
def api_backtest():
    d = request.json
    try:
        from src.backtest.data_feed import get_data
        from src.backtest.engine import BacktestEngine
        from src.backtest.batch_runner import _make_strategy_instance
        sym = d.get("symbol", "601398"); sk = d.get("strategy", "ma_cross")
        start = d.get("start_date", "2024-01-01"); end = d.get("end_date") or None
        data = get_data(sym, "A股", start_date=start, end_date=end)
        s = _make_strategy_instance(sk, {}, sym)
        r = BacktestEngine().run(s, data)
        equity = [{"time": str(x["date"])[:10], "value": x["total_value"]} for x in r["portfolio"].daily_values[::5]]
        return jsonify({"data_rows": len(data),
                       "date_range": f"{str(data['date'].iloc[0])[:10]} ~ {str(data['date'].iloc[-1])[:10]}",
                       "metrics": r["metrics"], "equity": equity,
                       "trades": [{"date": t["date"], "action": t["action"], "price": round(t["price"],2),
                                   "qty": t["quantity"]} for t in r["portfolio"].trade_log[-15:]]})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/diagnosis', methods=['POST'])
def api_diagnosis():
    d = request.json; sym = d.get("symbol", "601398"); start = d.get("start_date", "2022-01-01")
    try:
        from src.backtest.data_feed import get_data, download_watchlist, get_data_summary
        from src.backtest.engine import BacktestEngine
        from src.backtest.batch_runner import _make_strategy_instance
        from src.strategies.library import STRATEGIES
        from src.factors.composer import PRESET_STRATEGIES
        from src.factors.definitions import FactorCalculator
        from datetime import datetime

        today = datetime.now().strftime("%Y-%m-%d")
        try:
            cdf = get_data_summary(); target = f"A股_{sym}_daily.csv"
            if not cdf.empty and target in cdf["文件"].values:
                m = cdf["文件"] == target; latest = str(cdf[m].iloc[0]["结束日期"]).strip()[:10]
                if latest < today: download_watchlist([{"symbol":sym,"market":"A股","name":sym}], verbose=False)
        except: pass

        data = get_data(sym, "A股", start_date=start)
        if data is None or len(data)==0: return jsonify({"error":f"未获取到{sym}的数据"})

        price = float(data["close"].iloc[-1])
        de = str(data["date"].iloc[-1])[:10]; ds = str(data["date"].iloc[0])[:10]
        fresh = "🟢今日" if de>=today else f"⚠️仅到{de}"

        lines = [f"═══ 个股诊断: {sym} ═══",
                 f"数据:{len(data)}条 | {ds}~{de} | {fresh} | ¥{price:.2f}",""]

        all_s = list(STRATEGIES.keys()) + list(PRESET_STRATEGIES.keys())
        results = []
        for key in all_s:
            name = key
            for src in [STRATEGIES, PRESET_STRATEGIES]:
                if key in src: name = src[key].get("name", key); break
            try:
                s = _make_strategy_instance(key, {}, sym)
                r = BacktestEngine().run(s, data); m = r["metrics"]
                try: sh = float(str(m.get("夏普比率",-99)))
                except: sh = -99
                results.append((sh, name, m.get("总收益率","-"), m.get("最大回撤","-"), m.get("胜率","-")))
            except: pass
        results.sort(key=lambda x: x[0], reverse=True)

        lines.append("── 策略排名(按夏普) ──")
        for i,(sh,name,ret,dd,wr) in enumerate(results[:15],1):
            lines.append(f"  {i:>2}. {name:<14} Sharpe={sh:>6.2f} 收益={ret} 回撤={dd} 胜率={wr}")

        try:
            calc = FactorCalculator(data)
            cf = calc.compute_all().iloc[-1]
            def _fv(n,dft=0.5):
                try: return float(cf.get(n,dft))
                except: return dft
            score=50;rsi=_fv("rsi_norm")
            if rsi<0.3:score+=int((0.3-rsi)/0.3*20)
            elif rsi>0.7:score-=int((rsi-0.7)/0.3*20)
            else:score+=5
            bb=_fv("bollinger_pos")
            if bb<0.2:score+=int((0.2-bb)/0.2*20)
            elif bb>0.8:score-=int((bb-0.8)/0.2*20)
            else:score+=5
            ma=_fv("ma_alignment")
            if ma>0.7:score+=15
            elif ma<0.3:score-=10
            macd=_fv("macd_hist",0.5)
            if macd>0.55:score+=15
            elif macd<0.45:score-=10
            score=max(0,min(100,score))
            lvl="🟢强烈买入" if score>=80 else ("🟡谨慎买入" if score>=60 else ("⚪观望" if score>=40 else "🔴回避"))
            lines.append("");lines.append("── 入场时机 ──")
            lines.append(f"  RSI:{rsi*100:.0f} 布林:{bb:.2f} 均线:{ma:.2f} MACD:{macd:.2f}")
            lines.append(f"  评分:{score}/100 → {lvl}")
        except: pass

        return jsonify({"report":"\n".join(lines)})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/daily_scan', methods=['POST'])
def api_daily_scan():
    data = request.json; full = data.get("full", False)
    try:
        from daily_runner import quick_diagnosis, DEFAULT_WATCHLIST
        results = []
        for item in DEFAULT_WATCHLIST[:13]:
            r = quick_diagnosis(item["symbol"], item.get("market","A股"), item.get("name",item["symbol"]), full=full)
            results.append(r)
        results.sort(key=lambda r: r["score"], reverse=True)
        scan = [{"symbol":r["symbol"],"name":r.get("name",""),"price":r["price"],"score":r["score"],
                 "level":r["level"].split()[-1] if r["level"] else "N/A"} for r in results]
        buys=len([r for r in results if not r.get("error") and r["score"]>=60])
        waits=len([r for r in results if not r.get("error") and 40<=r["score"]<60])
        avoids=len([r for r in results if not r.get("error") and r["score"]<40])
        return jsonify({"count":len(results),"results":scan,"summary":{"buy":buys,"wait":waits,"avoid":avoids}})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/strategies')
def api_strategies():
    try:
        from src.strategies.library import STRATEGIES
        from src.factors.composer import PRESET_STRATEGIES
        result = []
        for key, info in STRATEGIES.items():
            params = info.get("params", {})
            params_str = ", ".join(f"{k}:{v}" for k,v in params.items()) if params else "默认"
            result.append({"key":key,"name":info["name"],"desc":info.get("description",""),"params":params_str})
        for key, info in PRESET_STRATEGIES.items():
            result.append({"key":key,"name":info["name"],"desc":info.get("description",""),"params":"因子组合"})
        return jsonify({"strategies": result})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/factors')
def api_factors():
    try:
        from src.factors.definitions import FACTOR_REGISTRY
        cats = {"trend":"趋势","momentum":"动量","volatility":"波动","volume":"成交量","pattern":"形态"}
        result = [{"name":f.name,"category":cats.get(f.category,f.category),"desc":f.description} for f in FACTOR_REGISTRY.values()]
        return jsonify({"factors": result})
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

@app.route('/api/stock/lookup')
def api_stock_lookup():
    try:
        from src.data.stock_db import ensure_stock_db
        db = ensure_stock_db(); code = request.args.get("code","").strip()
        name = db.get_name(code)
        return jsonify({"code":code,"name":name if name!=code else ""})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/stock/search')
def api_stock_search():
    try:
        from src.data.stock_db import ensure_stock_db
        db = ensure_stock_db(); q = request.args.get("q","").strip()
        results = db.search(q, limit=10)
        return jsonify({"results":[{"code":r["code"],"name":r["name"],"market":r["market"]} for r in results]})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/daily_brief')
def api_daily_brief():
    """每日开盘简报: 持仓检查 + 强势股 + AI分析"""
    try:
        from src.models.trade import TradeRepository
        from src.backtest.data_feed import get_data, get_data_summary, download_watchlist
        from src.factors.definitions import FactorCalculator
        from datetime import datetime

        today = datetime.now().strftime("%Y-%m-%d")
        repo = TradeRepository()

        # 1. 持仓分析
        positions = repo.find_open_positions()
        pos_analysis = []
        for p in positions:
            try:
                d = get_data(p.symbol, "A股", start_date="2023-01-01")
                price = float(d["close"].iloc[-1])
                cost = p.price
                pnl_pct = (price/cost - 1) * 100
                calc = FactorCalculator(d)
                cf = calc.compute_all().iloc[-1]
                rsi = float(cf.get("rsi_norm", 0.5))
                ma = float(cf.get("ma_alignment", 0.5))
                bb = float(cf.get("bollinger_pos", 0.5))
                # Health score
                health = 50
                if rsi < 0.3: health -= 20; rsi_sig = "超卖"
                elif rsi > 0.7: health -= 10; rsi_sig = "超买"
                else: rsi_sig = "正常"
                if ma > 0.6: health += 15
                elif ma < 0.3: health -= 15
                pos_analysis.append({
                    "symbol": p.symbol, "name": p.name, "cost": cost, "price": round(price,2),
                    "pnl_pct": round(pnl_pct,1), "qty": p.quantity,
                    "value": round(price * p.quantity, 0),
                    "health": health, "rsi": f"{rsi*100:.0f}", "rsi_sig": rsi_sig,
                    "ma": f"{ma:.2f}", "bb": f"{bb:.2f}",
                    "action": "持有" if health > 30 else ("减仓" if health > 10 else "建议离场")
                })
            except: pass

        # 2. 强势股扫描 (默认列表)
        watchlist = ["600498","601398","000858","600519","300750","000001","600036","002594","000333","601318","600900","688981","300059"]
        strong_stocks = []
        for sym in watchlist:
            try:
                d = get_data(sym, "A股", start_date="2024-01-01")
                price = float(d["close"].iloc[-1])
                calc = FactorCalculator(d)
                cf = calc.compute_all().iloc[-1]
                rsi = float(cf.get("rsi_norm", 0.5))
                ma = float(cf.get("ma_alignment", 0.5))
                mom = float(cf.get("momentum_score", 0.5))
                score = 0
                if rsi < 0.3: score += 25
                elif rsi > 0.7: score -= 15
                else: score += 10
                if ma > 0.7: score += 20
                elif ma < 0.3: score -= 10
                if mom > 0.6: score += 15
                if score >= 25:
                    strong_stocks.append({"symbol": sym, "price": round(price,2), "score": score,
                                         "rsi": f"{rsi*100:.0f}", "ma": f"{ma:.2f}", "mom": f"{mom:.2f}"})
            except: pass
        strong_stocks.sort(key=lambda x: x["score"], reverse=True)

        # 3. AI 简报
        ai_brief = ""
        try:
            from src.ai.assistants import AIMarketAnalyst
            ai_brief = AIMarketAnalyst().daily_brief()
        except: pass

        total_value = sum(p["value"] for p in pos_analysis)
        total_pnl = sum((p["price"]-p["cost"])*p["qty"] for p in pos_analysis)

        return jsonify({
            "date": today, "positions": pos_analysis,
            "total_positions": len(positions), "total_value": round(total_value,0),
            "total_pnl": round(total_pnl,0),
            "strong_stocks": strong_stocks[:8],
            "ai_brief": ai_brief[:500] if ai_brief else ""
        })
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/recommend', methods=['POST'])
def api_recommend():
    """智能推荐: 全策略+全因子 → 最优策略 → 买卖价位"""
    d = request.json; sym = d.get("symbol", "600498")
    try:
        from src.backtest.data_feed import get_data, download_watchlist, get_data_summary
        from src.backtest.engine import BacktestEngine
        from src.backtest.batch_runner import _make_strategy_instance
        from src.strategies.library import STRATEGIES
        from src.factors.composer import PRESET_STRATEGIES
        from src.factors.definitions import FactorCalculator
        from datetime import datetime
        import pandas as pd

        today = datetime.now().strftime("%Y-%m-%d")
        try:
            cdf = get_data_summary(); target = f"A股_{sym}_daily.csv"
            if not cdf.empty and target in cdf["文件"].values:
                m = cdf["文件"] == target; latest = str(cdf[m].iloc[0]["结束日期"]).strip()[:10]
                if latest < today: download_watchlist([{"symbol":sym,"market":"A股","name":sym}], verbose=False)
        except: pass

        data = get_data(sym, "A股", start_date="2022-01-01")
        if data is None or len(data)==0: return jsonify({"error":f"未获取到{sym}的数据"})

        current_price = float(data["close"].iloc[-1])
        de = str(data["date"].iloc[-1])[:10]; ds = str(data["date"].iloc[0])[:10]
        fresh = "今日" if de>=today else f"仅到{de}"

        # 1. 全策略回测排名
        all_s = list(STRATEGIES.keys()) + list(PRESET_STRATEGIES.keys())
        results = []
        for key in all_s:
            name = key
            for src in [STRATEGIES, PRESET_STRATEGIES]:
                if key in src: name = src[key].get("name", key); break
            try:
                s = _make_strategy_instance(key, {}, sym)
                r = BacktestEngine().run(s, data); m = r["metrics"]
                try: sh = float(str(m.get("夏普比率",-99)))
                except: sh = -99
                try: ret = float(str(m.get("总收益率","0")).replace("%","").replace("+","").replace("N/A","0"))
                except: ret = 0
                try: wr = float(str(m.get("胜率","0")).replace("%","").replace("N/A","0"))
                except: wr = 0
                try: dd = float(str(m.get("最大回撤","0")).replace("%","").replace("-","").replace("N/A","0"))
                except: dd = 0
                results.append({"key":key,"name":name,"sharpe":sh,"return":ret,"winrate":wr,"drawdown":dd,"trades":len(r["portfolio"].trade_log)})
            except: pass
        results.sort(key=lambda x: x["sharpe"], reverse=True)

        best = results[0] if results else None

        # 2. 当前因子分析 → 买卖价位
        calc = FactorCalculator(data)
        cf = calc.compute_all().iloc[-1]
        def _fv(n,dft=0.5):
            try: return float(cf.get(n,dft))
            except: return dft

        rsi = _fv("rsi_norm")
        bb_pos = _fv("bollinger_pos")
        ma_align = _fv("ma_alignment")
        macd = _fv("macd_hist", 0.5)
        atr_ratio = _fv("atr_ratio", current_price*0.0001)

        # 计算布林带价位
        bb = data["close"].rolling(20).mean().iloc[-1]
        bb_std = data["close"].rolling(20).std().iloc[-1]
        bb_upper = float(bb + 2*bb_std)
        bb_lower = float(bb - 2*bb_std)
        bb_mid = float(bb)
        atr = float(atr_ratio * current_price) if atr_ratio > 0 else current_price * 0.02

        # 入场评分
        score = 50
        if rsi < 0.3: score += int((0.3-rsi)/0.3*20)
        elif rsi > 0.7: score -= int((rsi-0.7)/0.3*20)
        else: score += 5
        if bb_pos < 0.2: score += int((0.2-bb_pos)/0.2*20)
        elif bb_pos > 0.8: score -= int((bb_pos-0.8)/0.2*20)
        else: score += 5
        if ma_align > 0.7: score += 15
        elif ma_align < 0.3: score -= 10
        if macd > 0.55: score += 15
        elif macd < 0.45: score -= 10
        score = max(0, min(100, score))

        # 推荐买入价: 布林下轨附近, 或当前价回调N%
        buy_price_support = round(bb_lower, 2)
        buy_price_rsi = round(current_price * (1 - max(0, 0.3-rsi)), 2)
        recommended_buy = round((buy_price_support + buy_price_rsi) / 2, 2)
        if recommended_buy > current_price: recommended_buy = round(current_price * 0.98, 2)

        # 推荐卖出价: 布林上轨, 或ATR止盈
        sell_target = round(bb_upper, 2)
        sell_trailing = round(current_price + 3*atr, 2)
        recommended_sell = round(min(sell_target, sell_trailing), 2)
        stop_loss = round(max(bb_lower * 0.95, current_price - 2*atr), 2)

        # 持仓周期建议
        if best and best["trades"] > 0:
            hold_days = max(5, len(data) // max(best["trades"], 1))
        else:
            hold_days = 20

        lines = []
        lines.append(f"════ 智能推荐报告: {sym} ════")
        lines.append(f"数据: {len(data)}条 | {ds}~{de} | {fresh}")
        lines.append(f"当前价格: ¥{current_price:.2f}")
        lines.append("")

        # 策略排名
        lines.append("── 策略排名 (TOP 5) ──")
        for i,r in enumerate(results[:5],1):
            lines.append(f"  {'🏆🥈🥉'[i-1] if i<=3 else '  '}{i}. {r['name']:<14} Sharpe={r['sharpe']:>6.2f} 收益={r['return']:>+6.1f}% 胜率={r['winrate']:>5.0f}% 回撤={r['drawdown']:>5.1f}%")

        lines.append("")
        lines.append("── 推荐策略 ──")
        if best:
            lines.append(f"  ★ {best['name']} (夏普{best['sharpe']:.2f}, 胜率{best['winrate']:.0f}%)")
        lines.append(f"  入场评分: {score}/100")

        lines.append("")
        lines.append("── 买卖价位 ──")
        lines.append(f"  当前价格:   ¥{current_price:.2f}")
        lines.append(f"  📥 建议买入: ¥{recommended_buy:.2f}  (布林下轨¥{buy_price_support:.2f} | RSI回调¥{buy_price_rsi:.2f})")
        lines.append(f"  📤 建议卖出: ¥{recommended_sell:.2f}  (布林上轨¥{sell_target:.2f} | ATR止盈¥{sell_trailing:.2f})")
        lines.append(f"  🛑 止损价位: ¥{stop_loss:.2f}  (跌破建议立即离场)")

        profit_pct = (recommended_sell/recommended_buy - 1) * 100 if recommended_buy > 0 else 0
        loss_pct = (stop_loss/recommended_buy - 1) * 100 if recommended_buy > 0 else 0
        rr_ratio = abs(profit_pct/loss_pct) if loss_pct != 0 else 0
        lines.append(f"  预期收益: +{profit_pct:.1f}% | 风险: {loss_pct:.1f}% | 盈亏比: {rr_ratio:.1f}:1")

        lines.append("")
        lines.append("── 仓位与持仓 ──")
        risk_pct = 1.5 if best and best["drawdown"] < 10 else 1.0
        risk_amount = 100000 * risk_pct / 100
        pos_shares = int(risk_amount / (recommended_buy - stop_loss)) if (recommended_buy - stop_loss) > 0 else 0
        pos_shares = max(100, pos_shares // 100 * 100)
        pos_value = pos_shares * recommended_buy
        lines.append(f"  建议仓位: {pos_shares}股 ({pos_shares//100}手) ≈ ¥{pos_value:,.0f}")
        lines.append(f"  建议持仓: {hold_days}个交易日")
        lines.append(f"  资金占用: {pos_value/100000*100:.1f}%")

        lines.append("")
        lines.append("── 当前因子信号 ──")
        lines.append(f"  RSI:{rsi*100:.0f} | 布林位置:{bb_pos:.2f} | 均线排列:{ma_align:.2f} | MACD:{macd:.2f}")
        rsi_signal = "超卖,反弹概率大" if rsi<0.3 else ("超买,注意回调" if rsi>0.7 else "中性")
        bb_signal = "接近下轨,支撑强" if bb_pos<0.2 else ("接近上轨,压力大" if bb_pos>0.8 else "中轨附近")
        ma_signal = "多头排列,趋势好" if ma_align>0.7 else ("空头排列,趋势弱" if ma_align<0.3 else "方向不明")
        lines.append(f"  RSI解读: {rsi_signal}")
        lines.append(f"  布林解读: {bb_signal}")
        lines.append(f"  均线解读: {ma_signal}")

        lines.append("")
        if score >= 70:
            lines.append(f"  ✅ 综合建议: 当前评分{score}分,技术面偏多。建议在¥{recommended_buy}附近买入{pos_shares}股,止损¥{stop_loss},目标¥{recommended_sell}")
        elif score >= 50:
            lines.append(f"  ⚠️ 综合建议: 当前评分{score}分,信号中性。可轻仓试探,严格止损¥{stop_loss}")
        else:
            lines.append(f"  ❌ 综合建议: 当前评分{score}分,技术面偏空。建议等待更好的入场时机")

        return jsonify({"report": "\n".join(lines)})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/ai/recommend_chat', methods=['POST'])
def api_ai_recommend_chat():
    """AI推荐讨论 — 用户描述思路,AI分析匹配策略和可行性"""
    msg = request.json.get("message","")
    sym = request.json.get("symbol","")
    ctx = request.json.get("context","")
    try:
        from src.ai.engine import LLMClient
        system = f"""你是LXL QuantAxis的AI量化顾问。用户正在分析股票{sym}。
以下是系统对该股票的智能推荐结果：
{ctx[:1500] if ctx else '暂无推荐数据'}

用户会描述他们的交易思路。请你：
1. 判断用户的思路与哪个策略最匹配（从15个策略中选：双均线交叉、RSI、MACD、布林带、海龟、均值回归、动量突破、逆势交易V1、趋势跟踪V1、量价突破V1、均值回归V2、自适应复合、趋势做空、双向交易、状态感知）
2. 分析这个思路的可行性（结合推荐数据中的因子信号、支撑阻力位）
3. 给出具体建议（买入价位、止损位、仓位比例、持仓周期）
4. 如果思路有问题，指出风险和改进方向

用中文回复，控制在150字以内，直接给结论不要客套。"""
        reply = LLMClient().ask(msg, system=system)
        return jsonify({"reply": reply})
    except Exception as e:
        return jsonify({"reply": f"AI未连接: {e}"})

@app.route('/api/ai/chat', methods=['POST'])
def api_ai_chat():
    msg = request.json.get("message","")
    try:
        from src.ai.engine import LLMClient
        reply = LLMClient().ask(msg, system="你是LXL QuantAxis的AI量化助手。简洁回复(100字内)。涉及投资声明仅供参考。")
        return jsonify({"reply": reply})
    except Exception as e:
        return jsonify({"reply": f"AI未连接: {e}. 请在桌面应用左侧菜单 > AI > 配置AI 中设置API密钥。"})

@app.route('/api/ai/review')
def api_ai_review():
    try:
        from src.ai.assistants import AITradeReviewer
        return jsonify({"review": AITradeReviewer().review()})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/ai/market')
def api_ai_market():
    try:
        from src.ai.assistants import AIMarketAnalyst
        return jsonify({"brief": AIMarketAnalyst().daily_brief()})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/ai/create_strategy', methods=['POST'])
def api_ai_create_strategy():
    """AI策略战法: 用户用自然语言描述思路→AI解析→构建策略→回测"""
    d = request.json
    idea = d.get("idea","")
    sym = d.get("symbol","600498")
    start_date = d.get("start_date","2024-01-01")

    if not idea or len(idea) < 10:
        return jsonify({"error": "请提供更详细的交易思路描述"})

    try:
        from src.ai.engine import LLMClient
        from src.factors.definitions import FACTOR_REGISTRY

        # 列出可用因子供AI参考
        factor_list = []
        for name, f in FACTOR_REGISTRY.items():
            factor_list.append(f"{name}({f.category}): {f.description}")
        factor_info = "\n".join(factor_list)

        # Step 1: AI解析用户的交易思路
        parse_prompt = f"""你是量化策略构建专家。用户描述了一个交易思路,请解析为具体的因子条件组合。

可用因子列表(必须从这里选):
{factor_info}

运算符: lt(小于阈值触发), gt(大于阈值触发)
逻辑模式: weighted(加权总分>=阈值触发), and(全部满足触发), or(任一满足触发)

关键规则:
1. 仔细分析用户提到的每一个条件,全部映射到因子。不要遗漏任何一个条件
2. 至少选择3个因子。如果用户只提了一个条件,请自动补充相关的确认因子
3. threshold取值0-1,如RSI<30%即rsi_norm<0.3
4. weight取值1-3,越核心的条件权重越高
5. 用户提到的形态(如锤子线、吞没)对应hammer/engulfing因子,它们值为0或1,阈值设0.5
6. 如果用户提到了多个独立的买入条件,用weighted逻辑;如果条件互相确认,用and逻辑

只返回JSON:
{{"name":"策略名称","explanation":"解析说明(50字内)","conditions":[{{"factor":"rsi_norm","operator":"lt","threshold":0.3,"weight":2}}],"logic":"weighted","threshold":3.0}}

用户思路: {idea}"""

        reply = LLMClient().ask(parse_prompt, system="你是量化策略构建专家。只返回JSON,不要其他文字。")
        # Extract JSON
        import re, json
        json_match = re.search(r'\{.*\}', reply, re.DOTALL)
        if not json_match:
            return jsonify({"error": f"AI解析失败,请重新描述。AI回复: {reply[:200]}"})
        strategy_def = json.loads(json_match.group(0))

        # Step 2: 构建策略
        from src.backtest.data_feed import get_data
        from src.backtest.engine import BacktestEngine
        from src.factors.composer import SignalComposer
        from src.models.strategy import StrategyConfig

        data = get_data(sym, "A股", start_date=start_date)
        composer = SignalComposer(strategy_def.get("name", "AI策略"))
        for c in strategy_def.get("conditions", []):
            composer.add_condition(
                c["factor"], c["operator"], float(c["threshold"]),
                weight=int(c.get("weight", 1)), action="BUY"
            )
        logic = strategy_def.get("logic", "weighted")
        threshold = float(strategy_def.get("threshold", 3.0))
        composer.set_logic(logic, threshold, action="BUY")

        strategy = composer.to_strategy(StrategyConfig(name=sym))
        r = BacktestEngine().run(strategy, data)

        # 自动存入策略银行
        saved_id = None
        try:
            from src.data.strategy_store import bank
            saved_id = bank.save_strategy(
                name=strategy_def.get("name", "AI策略"),
                conditions=strategy_def.get("conditions", []),
                logic=logic, threshold=threshold,
                description=strategy_def.get("explanation", ""),
                tags="AI生成"
            )
            if saved_id:
                bank.save_backtest(saved_id, sym, r["metrics"])
        except: pass

        return jsonify({
            "name": strategy_def.get("name", "AI策略"),
            "explanation": strategy_def.get("explanation", ""),
            "conditions": strategy_def.get("conditions", []),
            "logic": logic,
            "threshold": threshold,
            "metrics": r["metrics"],
            "saved_id": saved_id,
            "trades": [{"date": t["date"], "action": t["action"],
                       "price": round(t["price"],2), "qty": t["quantity"]}
                      for t in r["portfolio"].trade_log[-10:]]
        })
    except json.JSONDecodeError as e:
        return jsonify({"error": f"AI返回格式错误: {e}"})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/factor_backtest', methods=['POST'])
def api_factor_backtest():
    d = request.json
    try:
        from src.backtest.data_feed import get_data
        from src.backtest.engine import BacktestEngine
        from src.factors.composer import SignalComposer
        from src.models.strategy import StrategyConfig
        sym = d.get("symbol","601398")
        factors = d.get("factors",[])
        logic = d.get("logic","weighted")
        threshold = float(d.get("threshold",3.0))
        strategy_name = d.get("name","因子策略")
        data = get_data(sym, "A股", start_date="2022-01-01")
        composer = SignalComposer(strategy_name)
        for f in factors:
            composer.add_condition(f["factor"], f["operator"], float(f["threshold"]),
                                   weight=float(f.get("weight",1)), action="BUY")
        composer.set_logic(logic, threshold, action="BUY")
        strategy = composer.to_strategy(StrategyConfig(name=sym))
        r = BacktestEngine().run(strategy, data)
        return jsonify({"metrics": r["metrics"]})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/database/status')
def api_database_status():
    try:
        from src.data.market_db import market_db
        meta = market_db.get_meta_summary()
        total_rows = sum(m["row_count"] for m in meta)
        return jsonify({"stocks": meta, "total_stocks": len(meta), "total_rows": total_rows,
                       "db_path": "D:/trading_data/market_data.db"})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/database/migrate')
def api_database_migrate():
    import os, pandas as pd
    from src.data.market_db import market_db
    cache_dir = "D:/trading_data/cache"
    count = 0
    if os.path.exists(cache_dir):
        for f in os.listdir(cache_dir):
            if not f.endswith('.csv'): continue
            parts = f.replace('.csv','').split('_')
            if len(parts) >= 3:
                try:
                    df = pd.read_csv(os.path.join(cache_dir, f), parse_dates=['date'])
                    market_db.insert_kline(parts[1], parts[0], df)
                    count += 1
                except: pass
    return jsonify({"count": count, "ok": True})

@app.route('/api/strategy_bank', methods=['GET','POST'])
def api_strategy_bank():
    from src.data.strategy_store import bank
    if request.method == 'POST':
        d = request.json
        sid = bank.save_strategy(
            name=d.get("name","策略"),
            conditions=d.get("conditions",[]),
            logic=d.get("logic","weighted"),
            threshold=float(d.get("threshold",3.0)),
            description=d.get("description",""),
            tags=d.get("tags",""),
        )
        return jsonify({"id": sid, "ok": True})
    else:
        tag = request.args.get("tag")
        strategies = bank.list_strategies(tag=tag)
        return jsonify({"strategies": strategies, "stats": bank.stats()})

@app.route('/api/strategy_bank/<int:sid>', methods=['GET','DELETE'])
def api_strategy_detail(sid):
    from src.data.strategy_store import bank
    if request.method == 'DELETE':
        bank.delete_strategy(sid)
        return jsonify({"ok": True})
    s = bank.get_strategy(sid)
    if not s: return jsonify({"error": "策略不存在"}), 404
    bts = bank.get_backtests(strategy_id=sid)
    return jsonify({"strategy": s, "backtests": bts})

@app.route('/api/chart_data')
def api_chart_data():
    try:
        from src.backtest.data_feed import get_data
        sym = request.args.get("symbol","600498")
        d = get_data(sym, "A股", start_date="2023-01-01")
        if d is None or len(d)==0: return jsonify({"data":[]})
        result = []
        for _, row in d.tail(252).iterrows():
            result.append({"time":str(row["date"])[:10],"open":float(row["open"]),"high":float(row["high"]),
                          "low":float(row["low"]),"close":float(row["close"])})
        return jsonify({"data":result})
    except Exception as e:
        return jsonify({"error":str(e),"data":[]})

# ═══════════════════════════════════════════════════════════
if __name__ == '__main__':
    import webbrowser, threading
    def open_browser():
        time.sleep(1)
        webbrowser.open('http://127.0.0.1:5000')
    threading.Thread(target=open_browser, daemon=True).start()
    print("\n  ╔══════════════════════════════════════╗")
    print("  ║  QuantAxis v5.0  Web 量化平台        ║")
    print("  ║  http://127.0.0.1:5000              ║")
    print("  ╚══════════════════════════════════════╝\n")
    app.run(host='0.0.0.0', port=5000, debug=False)
