"""
LXL·QuantAxis 每日自动诊断脚本

用法:
    python daily_runner.py                          # 扫描默认关注列表（13只）
    python daily_runner.py 000858 601398 600519     # 扫描指定股票
    python daily_runner.py --full                   # 完整诊断（含全策略回测）

功能:
    1. 刷新最新行情数据
    2. 计算因子 + 入场评分
    3. 保存诊断快报到 reports/ 目录
    4. 可选：完整诊断（含11策略回测）

适用场景:
    - Windows 定时任务每天收盘后（15:30）自动运行
    - 手动快速扫描多只股票
"""

import sys
import os
import io
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

# 默认关注列表
DEFAULT_WATCHLIST = [
    {"symbol": "000858", "market": "A股", "name": "五粮液"},
    {"symbol": "600519", "market": "A股", "name": "贵州茅台"},
    {"symbol": "601398", "market": "A股", "name": "工商银行"},
    {"symbol": "600036", "market": "A股", "name": "招商银行"},
    {"symbol": "000333", "market": "A股", "name": "美的集团"},
    {"symbol": "601318", "market": "A股", "name": "中国平安"},
    {"symbol": "600900", "market": "A股", "name": "长江电力"},
    {"symbol": "300750", "market": "A股", "name": "宁德时代"},
    {"symbol": "002415", "market": "A股", "name": "海康威视"},
    {"symbol": "600276", "market": "A股", "name": "恒瑞医药"},
    {"symbol": "601899", "market": "A股", "name": "紫金矿业"},
    {"symbol": "300059", "market": "A股", "name": "东方财富"},
    {"symbol": "688981", "market": "A股", "name": "中芯国际"},
]


def capture_output(func, *args, **kwargs):
    """捕获函数 print 输出"""
    buf = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = buf
    try:
        result = func(*args, **kwargs)
    finally:
        sys.stdout = old_stdout
    return result, buf.getvalue()


def quick_diagnosis(symbol, market, name="", full=False):
    """
    快速诊断单只股票
    返回: dict with score, level, price, data_rows, data_fresh
    """
    from src.backtest.data_feed import get_data, download_watchlist, get_data_summary
    from src.factors.definitions import FactorCalculator

    today = datetime.now().strftime("%Y-%m-%d")
    result = {"symbol": symbol, "name": name, "market": market,
              "error": None, "score": 50, "level": "N/A",
              "price": 0, "data_rows": 0, "data_fresh": False}

    # 1. 检查并刷新数据
    try:
        cache_df = get_data_summary()
        target_file = f"{market}_{symbol}_daily.csv"
        data_fresh = False
        if not cache_df.empty:
            mask = cache_df["文件"] == target_file
            if mask.any():
                row = cache_df[mask].iloc[0]
                latest = str(row["结束日期"]).strip()[:10]
                if latest >= today:
                    data_fresh = True

        if not data_fresh:
            download_watchlist([{"symbol": symbol, "market": market, "name": name or symbol}],
                              verbose=False)
    except Exception as e:
        result["error"] = f"数据刷新失败: {e}"
        return result

    # 2. 加载数据
    try:
        data = get_data(symbol, market, start_date="2024-01-01")
    except Exception as e:
        result["error"] = f"数据加载失败: {e}"
        return result

    if data is None or len(data) == 0:
        result["error"] = "无数据"
        return result

    result["data_rows"] = len(data)
    latest_date = str(data["date"].iloc[-1])[:10]
    result["data_fresh"] = (latest_date >= today)
    result["price"] = float(data["close"].iloc[-1])

    # 3. 计算因子和入场评分
    try:
        calc = FactorCalculator(data)
        factors_df = calc.compute_all()
        current_factors = factors_df.iloc[-1]

        # 复用 main.py 中的入场评分逻辑
        timing = _quick_entry_score(current_factors)
        result["score"] = timing["score"]
        result["level"] = timing["level"]
        result["signals_summary"] = timing["summary"]
    except Exception as e:
        result["error"] = f"因子分析失败: {e}"

    # 4. 可选：完整回测
    if full:
        try:
            from src.backtest.engine import BacktestEngine
            from src.backtest.batch_runner import _make_strategy_instance
            from src.strategies.library import STRATEGIES
            from src.factors.composer import PRESET_STRATEGIES

            all_strategies = list(STRATEGIES.keys()) + list(PRESET_STRATEGIES.keys())
            best_sharpe = -999
            best_strategy = ""
            for key in all_strategies:
                try:
                    strategy = _make_strategy_instance(key, {}, symbol)
                    engine = BacktestEngine()
                    res = engine.run(strategy, data)
                    m = res["metrics"]
                    s = m.get("夏普比率", -999)
                    try:
                        s_val = float(str(s))
                    except (ValueError, TypeError):
                        s_val = -999
                    if s_val > best_sharpe:
                        best_sharpe = s_val
                        # get name from dicts
                        name_key = key
                        for d in [STRATEGIES, PRESET_STRATEGIES]:
                            if key in d:
                                name_key = d[key].get("name", key)
                                break
                        best_strategy = name_key
                except Exception:
                    pass
            result["best_strategy"] = best_strategy
            result["best_sharpe"] = best_sharpe
        except Exception as e:
            result["full_backtest_error"] = str(e)

    return result


def _quick_entry_score(current_factors):
    """Quick entry timing score (mirrors _analyze_entry_timing logic)"""
    def _fv(name, default=0.5):
        v = current_factors.get(name, default)
        try:
            return float(v)
        except (ValueError, TypeError):
            return default

    score = 50

    rsi = _fv("rsi_norm")
    if rsi < 0.3:
        score += int((0.3 - rsi) / 0.3 * 20)
    elif rsi > 0.7:
        score -= int((rsi - 0.7) / 0.3 * 20)
    else:
        score += 5

    bb = _fv("bollinger_pos")
    if bb < 0.2:
        score += int((0.2 - bb) / 0.2 * 20)
    elif bb > 0.8:
        score -= int((bb - 0.8) / 0.2 * 20)
    else:
        score += 5

    ma = _fv("ma_alignment")
    if ma > 0.7:
        score += 15
    elif ma < 0.3:
        score -= 10

    macd_h = _fv("macd_hist", 0.5)
    if macd_h > 0.55:
        score += 15
    elif macd_h < 0.45:
        score -= 10

    vol = _fv("volume_ratio")
    if vol > 0.7:
        score += 10
    elif vol < 0.3:
        score -= 5
    else:
        score += 3

    hammer = _fv("hammer", 0)
    engulf = _fv("engulfing", 0)
    if hammer > 0.5:
        score += 10
    if engulf > 0.5:
        score += 10

    mom = _fv("momentum_score")
    if mom > 0.6:
        score += 10
    elif mom < 0.4:
        score -= 5
    else:
        score += 2

    trend = _fv("trend_strength")
    if trend > 0.5:
        score += 5
    else:
        score -= 3

    score = max(0, min(100, score))

    if score >= 80:
        level = "🟢 强烈买入"
        summary = "多指标共振看涨"
    elif score >= 60:
        level = "🟡 谨慎买入"
        summary = "部分指标支持，可小仓试探"
    elif score >= 40:
        level = "⚪ 观望等待"
        summary = "信号中性，等待明朗"
    elif score >= 20:
        level = "🔴 建议回避"
        summary = "指标偏空，耐心等待"
    else:
        level = "⛔ 强烈回避"
        summary = "风险极高，不建议入场"

    return {"score": score, "level": level, "summary": summary}


def run_daily_scan(symbols=None, full=False):
    """每日扫描主函数"""
    from src.config import config

    if symbols is None:
        watchlist = DEFAULT_WATCHLIST
    else:
        watchlist = [{"symbol": s, "market": "A股", "name": s} for s in symbols]

    now = datetime.now()
    report_lines = []
    report_lines.append(f"═" * 62)
    report_lines.append(f"  📊 QuantAxis 每日诊断快报")
    report_lines.append(f"  {now.strftime('%Y-%m-%d %H:%M')}")
    report_lines.append(f"═" * 62)
    report_lines.append(f"  扫描标的: {len(watchlist)} 只")
    report_lines.append(f"  模式: {'完整诊断' if full else '快速扫描(因子+评分)'}")
    report_lines.append("")

    results = []
    for i, item in enumerate(watchlist, 1):
        sym = item["symbol"]
        name = item.get("name", sym)
        market = item.get("market", "A股")
        print(f"  [{i}/{len(watchlist)}] {sym} {name} ...", end=" ", flush=True)
        r = quick_diagnosis(sym, market, name, full=full)
        results.append(r)
        if r["error"]:
            print(f"❌ {r['error']}")
        else:
            print(f"¥{r['price']:.2f} | 评分:{r['score']}/100 {r['level']}")

    # 按评分排序
    results.sort(key=lambda r: r["score"], reverse=True)

    # 生成报告
    report_lines.append(f"  {'─' * 58}")
    report_lines.append(f"  {'排名':<4} {'代码':<8} {'名称':<8} {'价格':>8} {'评分':>6} {'信号':<16}")
    report_lines.append(f"  {'─' * 58}")

    for i, r in enumerate(results, 1):
        if r["error"]:
            report_lines.append(f"  {i:<4} {r['symbol']:<8} {r['name']:<8} {'ERR':>8} {'-':>6} {r['error'][:16]}")
        else:
            level_short = r["level"].split()[-1] if r["level"] else "N/A"
            report_lines.append(f"  {i:<4} {r['symbol']:<8} {r['name']:<8} "
                              f"¥{r['price']:>7.2f} {r['score']:>5}  {level_short:<16}")

    report_lines.append(f"  {'─' * 58}")
    report_lines.append("")

    # 信号汇总
    buys = [r for r in results if not r["error"] and r["score"] >= 60]
    waits = [r for r in results if not r["error"] and 40 <= r["score"] < 60]
    avoids = [r for r in results if not r["error"] and r["score"] < 40]

    report_lines.append(f"  📈 信号汇总:")
    report_lines.append(f"     🟢 可关注 ({len(buys)}只): {', '.join(r['symbol'] for r in buys) if buys else '无'}")
    report_lines.append(f"     ⚪ 观望 ({len(waits)}只): {', '.join(r['symbol'] for r in waits) if waits else '无'}")
    report_lines.append(f"     🔴 回避 ({len(avoids)}只): {', '.join(r['symbol'] for r in avoids) if avoids else '无'}")
    report_lines.append("")

    # 数据新鲜度
    fresh_count = sum(1 for r in results if r.get("data_fresh"))
    report_lines.append(f"  📡 数据新鲜度: {fresh_count}/{len(results)} 只已更新到今日")
    report_lines.append(f"═" * 62)

    # 输出到控制台
    report = "\n".join(report_lines)
    print(f"\n{report}")

    # 保存到文件
    reports_dir = os.path.join(config.data_dir, "reports")
    os.makedirs(reports_dir, exist_ok=True)
    filename = f"daily_scan_{now.strftime('%Y%m%d_%H%M')}.txt"
    filepath = os.path.join(reports_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"  ✅ 报告已保存: {filepath}")

    return results


if __name__ == "__main__":
    full_mode = "--full" in sys.argv
    symbols = [a for a in sys.argv[1:] if not a.startswith("--")]

    if symbols:
        results = run_daily_scan(symbols, full=full_mode)
    else:
        results = run_daily_scan(full=full_mode)
