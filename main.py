
"""
投资策略模型系统 v0.3 — 主入口

═══════════════════════════════════════════
  用数据驱动交易决策 · 属于你自己的量化体系
═══════════════════════════════════════════

菜单结构:
  【管理中枢】
    0. 系统总览 → 仪表盘
    7. 数据管理

  【交易实战】
    1. 交易日志

  【策略研发】
    2. 单策略回测
    3. 批量回测
    5. 参数优化

  【分析复盘】
    4. 绩效分析
    6. 因子体系
"""

import sys
import os

if sys.platform == "win32":
    try:
        sys.stdin.reconfigure(encoding="utf-8")
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(__file__))


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def print_banner():
    from src.console import Style
    print(f"""
{Style.CYAN}{Style.BOLD}╔══════════════════════════════════════════════════╗
║     📈 LXL·QuantAxis 投资策略模型 v0.3               ║
║        用数据驱动交易决策 · 属于自己的量化体系         ║
╚══════════════════════════════════════════════════╝{Style.RESET}
    """)


def main():
    while True:
        print_banner()

        print("  【管理中枢】")
        print("    0. 📊 系统总览    — 仪表盘 · 状态 · 可视化")
        print("    7. 📥 数据管理    — 下载 · 缓存 · 一览")
        print()
        print("  【交易实战】")
        print("    V. 🔍 快速验证    — 选股票 → 设时间 → 选策略 → 一键回测")
        print("    D. 🩺 个股诊断    — 全策略扫描 · 投资者适配 · 时机仓位")
        print("    R. 🔄 每日快扫    — 刷新行情 · 扫描关注列表 · 信号汇总")
        print("    1. 📒 交易日志    — 记录买卖 · 持仓 · 复盘 · 盈亏")
        print()
        print("  【策略研发】")
        print("    2. 🧪 策略回测    — 单标的 × 策略")
        print("    3. 🔬 批量回测    — N标的×N策略 一键跑")
        print("    5. ⚙️ 参数优化    — 网格搜索 · Walk-Forward")
        print()
        print("  【指数增强】")
        print("    8. 📊 指数估值    — PE/PB分位 · 估值评级 · 低估机会")
        print("    9. 🔄 指数轮动    — 动量轮动 · 定投回测 · 策略对比")
        print()
        print("  【AI 助手】🆕")
        print("    A. 🤖 AI 量化助手  — 复盘 · 策略 · 市场 · 对话")
        print()
        print("  【分析复盘】")
        print("    4. 📊 绩效分析    — 报表 · 图表 · 对比")
        print("    6. 🧬 因子体系    — 18因子 · 信号组合 · 自建策略")
        print()
        print("  ──────────────────────────────────────────")
        print("    Q. 👋 退出")
        print()

        choice = input("  请输入选项: ").strip().upper()

        if choice == "0":
            _dashboard_menu()
        elif choice == "V":
            _quick_validate()
        elif choice == "D":
            _stock_diagnosis()
        elif choice == "R":
            _daily_scan()
        elif choice == "1":
            _journal_menu()
        elif choice == "2":
            _backtest_menu()
        elif choice == "3":
            _batch_menu()
        elif choice == "4":
            _analysis_menu()
        elif choice == "5":
            _optimize_menu()
        elif choice == "6":
            _factor_menu()
        elif choice == "7":
            _data_menu()
        elif choice == "8":
            _index_valuation_menu()
        elif choice == "9":
            _index_strategy_menu()
        elif choice == "A":
            _ai_menu()
        elif choice == "Q":
            print("\n  再见，祝交易顺利！📈\n")
            break
        else:
            print("  ❌ 无效选择。")


# ============================================================
# V. 快速验证 — 选股票 → 设时间 → 选策略 → 一键回测
# ============================================================

def _quick_validate():
    """快速验证：选股票 → 设时间 → 选策略 → 出结果"""
    from src.strategies.library import STRATEGIES
    from src.factors.composer import PRESET_STRATEGIES
    from src.backtest.data_feed import get_data
    from src.backtest.engine import BacktestEngine
    from src.backtest.batch_runner import _make_strategy_instance
    from datetime import datetime as _dt

    print("\n" + "=" * 54)
    print("  🔍 快速验证 — 用数据验证你的交易想法")
    print("=" * 54)

    # —— 步骤1: 选股票 ——
    print("\n  📌 步骤1/3: 选择标的")
    symbol = input("    股票代码 [601398]: ").strip() or "601398"
    market = input("    市场 (A股/美股/港股) [A股]: ").strip() or "A股"

    # —— 步骤2: 设时间 ——
    print(f"\n  📅 步骤2/3: 设定回测区间")
    start = input("    起始日期 [2024-01-01]: ").strip() or "2024-01-01"
    today = _dt.now().strftime("%Y-%m-%d")
    end = input(f"    截止日期 (回车=最新) [{today}]: ").strip() or None

    # —— 步骤3: 选策略 ——
    strategy_key = _pick_strategy()
    if strategy_key is None:
        return  # 用户选择返回
    if strategy_key == "__custom__":
        _custom_strategy_backtest()
        return

    # 获取策略中文名
    strategy_name = strategy_key
    for d in [STRATEGIES, PRESET_STRATEGIES]:
        if strategy_key in d:
            strategy_name = d[strategy_key].get("name", strategy_key)
            break

    # 确认参数
    print(f"\n  ═══════════════════════════════════")
    print(f"  📋 回测参数确认:")
    print(f"     标的: {symbol}  ({market})")
    print(f"     区间: {start} ~ {end or '最新'}")
    print(f"     策略: {strategy_name} ({strategy_key})")
    print(f"  ═══════════════════════════════════")

    # 加载数据
    print(f"\n  ⏳ 加载数据...")
    try:
        data = get_data(symbol, market, start_date=start, end_date=end)
    except Exception as e:
        print(f"  ❌ 数据获取失败: {e}")
        return

    if data is None or len(data) == 0:
        print(f"  ❌ 未获取到数据，请检查代码和市场。")
        return

    print(f"  ✅ {len(data)} 条 ({str(data['date'].iloc[0])[:10]} ~ {str(data['date'].iloc[-1])[:10]})")

    # 运行回测
    print(f"  ⏳ 运行 {strategy_name} ...")
    try:
        strategy = _make_strategy_instance(strategy_key, {}, symbol)
        engine = BacktestEngine()
        result = engine.run(strategy, data)
    except Exception as e:
        print(f"  ❌ 回测失败: {e}")
        return

    _print_backtest_metrics(result["metrics"])

    # 可选图表
    gen = input("\n  生成 HTML 图表? (y/n): ").strip().lower()
    if gen == "y":
        try:
            from src.analysis.charts import plot_from_backtest
            out = os.path.join(config.data_dir, "charts", f"{symbol}_{strategy_key}")
            os.makedirs(out, exist_ok=True)
            plot_from_backtest(result, save_dir=out)
            print(f"  ✅ 图表已保存到: {out}")
        except Exception as e:
            print(f"  ⚠️ 图表失败: {e}")

    # 可选仪表盘
    dash = input("  打开绩效仪表盘? (y/n): ").strip().lower()
    if dash == "y":
        from src.dashboard.visual import open_dashboard
        open_dashboard("performance")


def _pick_strategy():
    """交互式策略选择器，返回 strategy_key 或 None"""
    from src.strategies.library import STRATEGIES
    from src.factors.composer import PRESET_STRATEGIES

    # 构建统一列表
    all_s = []
    for key, info in STRATEGIES.items():
        all_s.append((key, info["name"], info["description"]))
    for key, info in PRESET_STRATEGIES.items():
        all_s.append((key, info["name"], info["description"]))

    print(f"\n  🧪 步骤3/3: 选择策略")
    print("  " + "-" * 50)

    for i, (key, name, desc) in enumerate(all_s, 1):
        print(f"  {i:>2}. {name:<14} — {desc}")

    print(f"  {len(all_s)+1:>2}. 🧬 因子组合策略 (自建)")
    print("   0. 返回")

    while True:
        choice = input("\n  请选择策略: ").strip()
        if choice == "0":
            return None
        if choice == str(len(all_s) + 1):
            return "__custom__"
        try:
            idx = int(choice)
            if 1 <= idx <= len(all_s):
                return all_s[idx - 1][0]
        except ValueError:
            pass
        print("  ❌ 无效选择，请重试。")


def _print_backtest_metrics(metrics: dict):
    """分组展示回测指标"""
    if not metrics:
        print("  ⚠️ 无回测指标数据。")
        return

    print(f"\n  {'='*46}")
    print(f"  📊 回测结果")
    print(f"  {'='*46}")

    # 收益
    print(f"  💰 收益概况")
    for k in ["初始资金", "最终权益", "总收益率", "年化收益率"]:
        if k in metrics:
            print(f"     {k}: {metrics[k]}")

    # 风险
    print(f"  📉 风险指标")
    for k in ["夏普比率", "最大回撤", "最大回撤区间", "卡尔玛比率"]:
        if k in metrics:
            print(f"     {k}: {metrics[k]}")

    # 交易
    print(f"  📈 交易统计")
    for k in ["交易次数", "盈利次数", "亏损次数", "胜率", "盈亏比", "盈利因子"]:
        if k in metrics:
            print(f"     {k}: {metrics[k]}")

    print(f"  {'='*46}")


# ============================================================
# 0. 管理中枢 — 仪表盘
# ============================================================

def _dashboard_menu():
    """系统总览 — 可视化管理面板"""
    while True:
        print("\n" + "=" * 54)
        print("  📊 系统总览 — 管理面板")
        print("=" * 54)
        print("  1. 🖥️ 打开系统总览仪表盘     (交易+持仓+策略总览)")
        print("  2. 📈 打开绩效对比仪表盘     (夏普/收益矩阵 + TOP排名)")
        print("  3. 📥 打开数据健康仪表盘     (缓存状态 + 覆盖范围)")
        print("  4. 📂 一键打开全部仪表盘")
        print("  5. 📋 系统状态摘要 (终端)")
        print("  6. ⚙️ 查看/修改配置")
        print("  7. 🗑️ 清空回测结果数据库")
        print("  0. 返回主菜单")

        choice = input("\n  请选择 [0-7]: ").strip()

        if choice == "1":
            try:
                from src.dashboard.visual import open_dashboard
                open_dashboard("overview")
            except Exception as e:
                print(f"  ❌ {e}")

        elif choice == "2":
            try:
                from src.dashboard.visual import open_dashboard
                open_dashboard("performance")
            except Exception as e:
                print(f"  ❌ {e}")

        elif choice == "3":
            try:
                from src.dashboard.visual import open_dashboard
                open_dashboard("data_health")
            except Exception as e:
                print(f"  ❌ {e}")

        elif choice == "4":
            try:
                from src.dashboard.visual import open_all
                open_all()
            except Exception as e:
                print(f"  ❌ {e}")

        elif choice == "5":
            _system_status()

        elif choice == "6":
            _config_menu()

        elif choice == "7":
            confirm = input("  ⚠️ 确认清空回测结果数据库? (yes/no): ").strip()
            if confirm.lower() == "yes":
                from src.config import config
                db_path = os.path.join(config.data_dir, "backtest_results.db")
                if os.path.exists(db_path):
                    os.remove(db_path)
                    print(f"  ✅ 已删除: {db_path}")
                else:
                    print("  📭 数据库不存在。")

        elif choice == "0":
            return


def _system_status():
    """终端系统状态摘要"""
    from src.models.trade import TradeRepository
    from src.backtest.data_feed import get_data_summary
    from src.backtest.batch_runner import ResultDB
    from src.config import config

    repo = TradeRepository()
    cache = get_data_summary()
    result_db = ResultDB()
    summary = result_db.summary()

    pnl_list = repo.get_all_pnl()
    total_pnl = sum(p["net_pnl"] for p in pnl_list) if pnl_list else 0
    wins = len([p for p in pnl_list if p["net_pnl"] > 0]) if pnl_list else 0

    print("\n  ╔══════════════════════════════════════╗")
    print("  ║        📊 系统状态摘要                ║")
    print("  ╠══════════════════════════════════════╣")
    print(f"  ║  版本: {config.version:<30}║")
    print(f"  ║  数据目录: {config.data_dir:<27}║")
    print(f"  ║  初始资金: ¥{config.initial_capital:,<27}║")
    print("  ╠══════════════════════════════════════╣")
    print(f"  ║  📒 交易记录: {repo.count():<4} 笔             ║")
    print(f"  ║  📦 当前持仓: {len(repo.find_open_positions()):<4} 只             ║")
    print(f"  ║  💰 总盈亏: ¥{total_pnl:+,.0f}            ║")
    print(f"  ║  🎯 胜率: {wins / max(len(pnl_list), 1) * 100:.1f}%                ║")
    print("  ╠══════════════════════════════════════╣")
    print(f"  ║  💾 缓存文件: {len(cache):<3} 个            ║")
    if not cache.empty:
        print(f"  ║  📊 缓存行数: {int(cache['行数'].sum()):<6}            ║")
    print(f"  ║  🔬 回测结果: {summary.get('总回测数', 0):<4} 条           ║")
    print(f"  ║  🏆 最佳: {summary.get('最佳策略', 'N/A')[:27]}║")
    print("  ╚══════════════════════════════════════╝")


def _config_menu():
    """查看/修改配置"""
    from src.config import config

    while True:
        print("\n  —— 系统配置 ——")
        print(f"  1. 数据目录: {config.data_dir}")
        print(f"  2. 初始资金: ¥{config.initial_capital:,}")
        print(f"  3. 手续费率: {config.commission_rate:.4f}")
        print(f"  4. 默认仓位: {config.position_size_pct*100:.0f}%")
        print(f"  5. 止损比例: {config.stop_loss_pct*100:.1f}%")
        print(f"  6. 止盈比例: {config.take_profit_pct*100:.1f}%")
        print(f"  7. 日志级别: {config.log_level}")
        print("  8. 💾 保存当前配置")
        print("  9. 📋 显示全部配置")
        print("  0. 返回")

        choice = input("\n  选择要修改的项 [0-9]: ").strip()
        if choice == "0":
            return
        elif choice == "1":
            config._data["data_dir"] = input("  新路径: ").strip() or config.data_dir
        elif choice == "2":
            config._data["initial_capital"] = float(input("  新资金: ").strip() or config.initial_capital)
        elif choice == "3":
            config._data["commission_rate"] = float(input("  新费率: ").strip() or config.commission_rate)
        elif choice == "4":
            config._data["position_size_pct"] = float(input("  新仓位(0-1): ").strip() or config.position_size_pct)
        elif choice == "5":
            config._data["stop_loss_pct"] = float(input("  新止损(0-1): ").strip() or config.stop_loss_pct)
        elif choice == "6":
            config._data["take_profit_pct"] = float(input("  新止盈(0-1): ").strip() or config.take_profit_pct)
        elif choice == "7":
            config._data["log_level"] = input("  日志级别(DEBUG/INFO/WARNING): ").strip().upper() or config.log_level
        elif choice == "8":
            config.save()
        elif choice == "9":
            print()
            for k, v in config.to_dict().items():
                print(f"  {k}: {v}")


# ============================================================
# 1. 交易日志
# ============================================================

def _journal_menu():
    from src.journal.cli import run_journal
    run_journal()


# ============================================================
# 2. 策略回测
# ============================================================

def _backtest_menu():
    print("\n" + "=" * 54)
    print("  🧪 策略回测 — 单标的 × 策略")
    print("=" * 54)
    print("  —— 经典策略 ——")
    print("    1. 双均线交叉      5. 海龟交易")
    print("    2. RSI超买超卖      6. 均值回归")
    print("    3. MACD金叉死叉     7. 动量突破")
    print("    4. 布林带")
    print("  —— 独有策略模板 ——")
    print("    8. 逆势交易V1      10. 量价突破V1")
    print("    9. 趋势跟踪V1      11. 均值回归V2")
    print("  —— 自定义 ——")
    print("   12. 🧬 因子组合策略 (用因子搭建自己的策略)")
    print("  0. 返回")

    choice = input("\n  请选择 [0-12]: ").strip()

    strategy_map = {
        "1": "ma_cross", "2": "rsi", "3": "macd", "4": "bollinger",
        "5": "turtle", "6": "mean_reversion", "7": "momentum",
        "8": "contrarian_v1", "9": "trend_following_v1",
        "10": "volume_breakout_v1", "11": "mean_reversion_v2",
    }

    if choice == "0":
        return
    if choice == "12":
        _custom_strategy_backtest()
        return
    if choice in strategy_map:
        _run_single_backtest(strategy_map[choice])
    else:
        print("  ❌ 无效选择。")


def _run_single_backtest(strategy_key: str):
    from src.backtest.data_feed import get_data
    from src.backtest.engine import BacktestEngine
    from src.backtest.batch_runner import _make_strategy_instance
    from datetime import datetime as _dt

    symbol = input("\n  股票代码 [601398]: ").strip() or "601398"
    market = input("  市场 (A股/美股/港股) [A股]: ").strip() or "A股"
    start = input("  起始日期 [2024-01-01]: ").strip() or "2024-01-01"
    today = _dt.now().strftime("%Y-%m-%d")
    end = input(f"  截止日期 (回车=最新) [{today}]: ").strip() or None

    print(f"\n  加载数据 {market} {symbol} ...")
    try:
        data = get_data(symbol, market, start_date=start, end_date=end)
    except Exception as e:
        print(f"  ❌ 数据获取失败: {e}")
        return
    print(f"  ✅ {len(data)} 条 ({str(data['date'].iloc[0])[:10]} ~ {str(data['date'].iloc[-1])[:10]})")

    print(f"  运行策略 {strategy_key} ...")
    strategy = _make_strategy_instance(strategy_key, {}, symbol)
    engine = BacktestEngine()
    result = engine.run(strategy, data)

    _print_backtest_metrics(result["metrics"])

    # 图表
    gen = input("\n  生成 HTML 图表? (y/n): ").strip().lower()
    if gen == "y":
        try:
            from src.analysis.charts import plot_from_backtest
            out = os.path.join(config.data_dir, "charts", f"{symbol}_{strategy_key}")
            os.makedirs(out, exist_ok=True)
            plot_from_backtest(result, save_dir=out)
            print(f"  ✅ 图表已保存到: {out}")
        except Exception as e:
            print(f"  ⚠️ 图表失败: {e}")

    # 仪表盘
    dash = input("  打开绩效仪表盘? (y/n): ").strip().lower()
    if dash == "y":
        from src.dashboard.visual import open_dashboard
        open_dashboard("performance")

    # ── 自动生成复现清单 (v2.0) ──
    try:
        from src.journal.manifest import manifest_from_backtest
        manifest_from_backtest(
            strategy_name=strategy_key,
            symbol=symbol,
            metrics=result.get("metrics", {}),
            params={"start_date": start, "end_date": end or today},
        )
        print(f"  📋 复现清单已自动保存")
    except Exception as e:
        print(f"  ⚠️ 复现清单生成失败: {e}")


def _custom_strategy_backtest():
    from src.factors.composer import SignalComposer
    from src.backtest.data_feed import get_data
    from src.backtest.engine import BacktestEngine
    from src.models.strategy import StrategyConfig

    print("\n  —— 🧬 自定义因子策略 ——")
    print("  可用因子: rsi_norm, ma_deviation, ma_alignment, trend_strength,")
    print("           momentum_score, bollinger_pos, volume_ratio, hammer, 等18个")

    symbol = input("\n  股票代码 [601398]: ").strip() or "601398"
    start = input("  起始日期 [2024-01-01]: ").strip() or "2024-01-01"

    composer = SignalComposer("自定义策略")

    print("\n  ▶ 配置买入条件:")
    i = 1
    while True:
        factor = input(f"    条件{i} 因子名 (回车完成): ").strip()
        if not factor:
            break
        op = input("        运算符 (gt/lt) [lt]: ").strip() or "lt"
        thresh = float(input("        阈值 [0.5]: ").strip() or "0.5")
        weight = float(input("        权重 [1]: ").strip() or "1")
        composer.add_condition(factor, op, thresh, weight=weight, action="BUY")
        i += 1

    logic = input("\n  买入逻辑 (and/or/weighted) [weighted]: ").strip() or "weighted"
    threshold = float(input("  触发阈值 [2.0]: ").strip() or "2.0")
    composer.set_logic(logic, threshold, action="BUY")

    print("\n  ▶ 配置卖出条件:")
    j = 1
    while True:
        factor = input(f"    条件{j} 因子名 (回车完成): ").strip()
        if not factor:
            break
        op = input("        运算符 (gt/lt) [gt]: ").strip() or "gt"
        thresh = float(input("        阈值 [0.7]: ").strip() or "0.7")
        weight = float(input("        权重 [1]: ").strip() or "1")
        composer.add_condition(factor, op, thresh, weight=weight, action="SELL")
        j += 1

    sell_logic = input("\n  卖出逻辑 (and/or/weighted) [and]: ").strip() or "and"
    composer.set_logic(sell_logic, action="SELL")

    print(f"\n  加载数据...")
    data = get_data(symbol, "A股", start_date=start)
    strategy = composer.to_strategy(StrategyConfig(name=symbol))
    engine = BacktestEngine()
    result = engine.run(strategy, data)

    metrics = result["metrics"]
    print(f"\n  📊 回测结果:")
    for k, v in metrics.items():
        print(f"  {k}: {v}")


# ============================================================
# 3. 批量回测
# ============================================================

def _batch_menu():
    print("\n" + "=" * 54)
    print("  🔬 批量回测 — N标的 × N策略")
    print("=" * 54)
    print("  1. 🚀 快速批量 (5默认标的 × 3策略)")
    print("  2. 🎯 自定义批量 (自选标的 + 策略)")
    print("  3. 🏆 查看历史回测排名")
    print("  4. 📊 同一标的策略对比")
    print("  5. 📈 打开绩效仪表盘")
    print("  6. 🗑️ 清空回测结果")
    print("  0. 返回主菜单")

    choice = input("\n  请选择 [0-6]: ").strip()

    if choice == "1":
        from src.backtest.batch_runner import quick_batch
        start = input("  起始日期 [2024-01-01]: ").strip() or "2024-01-01"
        df = quick_batch(start_date=start)

    elif choice == "2":
        _custom_batch()

    elif choice == "3":
        from src.backtest.batch_runner import ResultDB
        db = ResultDB()
        strategy = input("  按策略筛选 (回车=全部): ").strip() or None
        df = db.ranking(strategy=strategy, top_n=30)
        if not df.empty:
            print(f"\n  🏆 回测排名 (TOP 30):")
            print(df.to_string())
        else:
            print("  📭 暂无回测结果。")

    elif choice == "4":
        from src.backtest.batch_runner import compare_strategies
        symbol = input("  股票代码: ").strip() or "601398"
        compare_strategies(symbol)

    elif choice == "5":
        from src.dashboard.visual import open_dashboard
        open_dashboard("performance")

    elif choice == "6":
        confirm = input("  ⚠️ 确认清空? (yes/no): ").strip()
        if confirm.lower() == "yes":
            db_path = os.path.join(config.data_dir, "backtest_results.db")
            if os.path.exists(db_path):
                os.remove(db_path)
                print("  ✅ 已清空。")

    elif choice == "0":
        return


def _custom_batch():
    from src.backtest.batch_runner import BatchRunner
    from src.strategies.library import STRATEGIES
    from src.factors.composer import PRESET_STRATEGIES

    symbols = input("\n  股票代码 (空格分隔): ").strip().split()
    if not symbols:
        symbols = ["601398", "600036", "000858"]

    print("\n  可用策略:")
    all_s = list(STRATEGIES.keys()) + list(PRESET_STRATEGIES.keys())
    for i, s in enumerate(all_s, 1):
        print(f"    {i:>2}. {s}")

    strat_input = input("\n  策略 (空格分隔编号或名称, 回车=全部): ").strip()
    if strat_input:
        if strat_input[0].isdigit():
            indices = [int(x) - 1 for x in strat_input.split()]
            strategies = [all_s[i] for i in indices if 0 <= i < len(all_s)]
        else:
            strategies = strat_input.split()
    else:
        strategies = list(STRATEGIES.keys()) + list(PRESET_STRATEGIES.keys())

    start = input("  起始日期 [2024-01-01]: ").strip() or "2024-01-01"

    runner = BatchRunner()
    runner.add_symbols(symbols)
    runner.add_strategies(strategies)
    runner.start_date = start
    df = runner.run()

    if not df.empty:
        runner.show_ranking()


# ============================================================
# 4. 绩效分析
# ============================================================

def _analysis_menu():
    print("\n" + "=" * 54)
    print("  📊 绩效分析")
    print("=" * 54)
    print("  1. 📋 文本分析报告 (交易日志)")
    print("  2. 📈 生成回测图表 (资金曲线+热力图)")
    print("  3. 🖥️ 打开绩效仪表盘")
    print("  0. 返回主菜单")

    choice = input("\n  请选择 [0-3]: ").strip()

    if choice == "1":
        from src.analysis.reports import run_report
        run_report()

    elif choice == "2":
        print("\n  请先运行回测（菜单 2 或 3），图表会自动生成。")

    elif choice == "3":
        from src.dashboard.visual import open_dashboard
        open_dashboard("performance")

    elif choice == "0":
        return


# ============================================================
# 5. 参数优化
# ============================================================

def _optimize_menu():
    print("\n" + "=" * 54)
    print("  ⚙️ 参数优化")
    print("=" * 54)
    print("  1. 🔍 网格搜索 (遍历参数组合)")
    print("  2. 🚶 Walk-Forward (滚动窗口样本外)")
    print("  3. ⚡ 一键快速优化")
    print("  0. 返回主菜单")

    choice = input("\n  请选择 [0-3]: ").strip()

    if choice == "1":
        from src.backtest.optimizer import GridSearch
        symbol = input("  股票代码 [601398]: ").strip() or "601398"
        strategy = input("  策略 [ma_cross]: ").strip() or "ma_cross"
        rank = input("  排名指标 [sharpe]: ").strip() or "sharpe"
        gs = GridSearch(symbol, "A股", start_date="2022-01-01", rank_by=rank)
        gs.run(strategy, {"fast_period": [5, 10, 20], "slow_period": [20, 30, 60]})

    elif choice == "2":
        from src.backtest.optimizer import quick_walkforward
        symbol = input("  股票代码 [601398]: ").strip() or "601398"
        strategy = input("  策略 [ma_cross]: ").strip() or "ma_cross"
        quick_walkforward(symbol, strategy)

    elif choice == "3":
        from src.backtest.optimizer import quick_optimize
        symbol = input("  股票代码 [601398]: ").strip() or "601398"
        strategy = input("  策略 [ma_cross]: ").strip() or "ma_cross"
        quick_optimize(symbol, strategy)

    elif choice == "0":
        return


# ============================================================
# 6. 因子体系
# ============================================================

def _factor_menu():
    print("\n" + "=" * 54)
    print("  🧬 因子体系 — 你的独有量化武器")
    print("=" * 54)
    print("  1. 📋 查看全部因子 (18个)")
    print("  2. 💾 导出因子数据 (某股票的完整因子CSV)")
    print("  3. 🧬 查看独有策略模板 (4个)")
    print("  4. 🔧 创建自定义因子策略 → 回测")
    print("  0. 返回主菜单")

    choice = input("\n  请选择 [0-4]: ").strip()

    if choice == "1":
        from src.factors.definitions import FACTOR_REGISTRY
        print()
        for name, factor in FACTOR_REGISTRY.items():
            print(f"  [{factor.category}] {name:<20} — {factor.description}")

    elif choice == "2":
        from src.backtest.data_feed import get_data
        from src.factors.definitions import FactorCalculator

        symbol = input("  股票代码 [601398]: ").strip() or "601398"
        print("  计算因子中...")
        data = get_data(symbol, "A股", start_date="2024-01-01")
        calc = FactorCalculator(data)
        factors = calc.compute_all()

        out = os.path.join(config.data_dir, f"factors_{symbol}.csv")
        factors.to_csv(out, index=False)
        print(f"  ✅ 已导出: {out}")
        print(f"     {len(factors.columns)} 个因子, {len(factors)} 行")

    elif choice == "3":
        from src.factors.composer import PRESET_STRATEGIES
        print()
        for key, info in PRESET_STRATEGIES.items():
            print(f"  {key:<25} — {info['description']}")

    elif choice == "4":
        _custom_strategy_backtest()

    elif choice == "0":
        return


# ============================================================
# 7. 数据管理
# ============================================================

def _data_menu():
    print("\n" + "=" * 54)
    print("  📥 数据管理")
    print("=" * 54)
    print("  1. 📥 下载默认关注列表 (13只)")
    print("  2. 🔍 查看数据缓存")
    print("  3. 🔄 刷新全部缓存")
    print("  4. 📥 自定义下载")
    print("  5. 🖥️ 打开数据健康仪表盘")
    print("  0. 返回主菜单")

    choice = input("\n  请选择 [0-5]: ").strip()

    if choice == "1":
        from src.backtest.data_feed import download_all_default
        download_all_default()

    elif choice == "2":
        from src.backtest.data_feed import get_data_summary
        df = get_data_summary()
        if df.empty:
            print("\n  📭 缓存为空。")
        else:
            print(f"\n  📊 缓存 ({len(df)} 文件, {int(df['行数'].sum())} 行):")
            print(df.to_string())

    elif choice == "3":
        from src.backtest.data_feed import refresh_cache
        refresh_cache()

    elif choice == "4":
        from src.backtest.data_feed import download_watchlist
        syms = input("  代码 (空格分隔): ").strip().split()
        market = input("  市场 (A股/美股/港股) [A股]: ").strip() or "A股"
        watchlist = [{"symbol": s, "market": market, "name": s} for s in syms]
        download_watchlist(watchlist)

    elif choice == "5":
        from src.dashboard.visual import open_dashboard
        open_dashboard("data_health")

    elif choice == "0":
        return


# ============================================================
# 8. 指数估值
# ============================================================

def _index_valuation_menu():
    """指数估值面板"""
    while True:
        print("\n" + "=" * 54)
        print("  📊 指数估值")
        print("=" * 54)
        print("  1. 📊 估值快照 (终端)")
        print("  2. 🖥️ 打开估值仪表盘")
        print("  3. 📋 查看所有支持的指数 ETF")
        print("  4. 📥 刷新估值数据")
        print("  0. 返回主菜单")

        choice = input("\n  请选择 [0-4]: ").strip()

        if choice == "1":
            from src.index.valuation import show_valuation
            show_valuation()

        elif choice == "2":
            from src.index.valuation import build_valuation_dashboard
            import webbrowser
            from src.config import config as cfg
            path = os.path.join(cfg.data_dir, "dashboards", "valuation.html")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(build_valuation_dashboard())
            webbrowser.open(f"file:///{path.replace(chr(92), '/')}")
            print(f"  ✅ 已打开: {path}")

        elif choice == "3":
            from src.index.valuation import list_indices
            list_indices()

        elif choice == "4":
            from src.index.valuation import get_valuation_snapshot
            print("  刷新估值数据...")
            snapshot = get_valuation_snapshot()
            if not snapshot.empty:
                print(f"  ✅ 已刷新 {len(snapshot)} 个指数")

        elif choice == "0":
            return


# ============================================================
# 9. 指数轮动 + 定投
# ============================================================

def _index_strategy_menu():
    """指数策略"""
    while True:
        print("\n" + "=" * 54)
        print("  🔄 指数策略 — 轮动 + 定投")
        print("=" * 54)
        print("  1. 🔄 动量轮动回测 (追最强的指数)")
        print("  2. 💰 普通定投回测")
        print("  3. 📈 增强定投回测 (越跌越买)")
        print("  4. 📊 三种策略大对比")
        print("  5. 🔬 自定义定投参数")
        print("  0. 返回主菜单")

        choice = input("\n  请选择 [0-5]: ").strip()

        if choice == "1":
            from src.index.rotation import IndexRotation
            top_k = int(input("  持有几个最强指数 [2]: ").strip() or "2")
            lookback = int(input("  动量周期(交易日) [20]: ").strip() or "20")
            start = input("  起始日期 [2020-01-01]: ").strip() or "2020-01-01"

            rot = IndexRotation(top_k=top_k, lookback_days=lookback)
            result = rot.run(start_date=start)
            if result:
                print()
                for k, v in result["metrics"].items():
                    print(f"  {k}: {v}")

        elif choice == "2" or choice == "3":
            from src.index.rotation import DCABacktest
            enhanced = (choice == "3")

            code = input("  标的代码/ETF [510300]: ").strip() or "510300"
            market = input("  市场 [A股]: ").strip() or "A股"
            amount = float(input("  每期金额 [5000]: ").strip() or "5000")
            freq = input("  频率 weekly/biweekly/monthly [monthly]: ").strip() or "monthly"
            start = input("  起始日期 [2018-01-01]: ").strip() or "2018-01-01"

            dca = DCABacktest(code, market)
            result = dca.run(amount_per_period=amount, frequency=freq,
                             start_date=start, enhanced=enhanced)

        elif choice == "4":
            from src.index.rotation import compare_index_strategies
            start = input("  起始日期 [2020-01-01]: ").strip() or "2020-01-01"
            compare_index_strategies(start)

        elif choice == "5":
            from src.index.rotation import DCABacktest
            code = input("  标的代码/ETF [510300]: ").strip() or "510300"
            amount = float(input("  每期金额 [5000]: ").strip() or "5000")
            freq = input("  频率 [monthly]: ").strip() or "monthly"
            start = input("  起始 [2018-01-01]: ").strip() or "2018-01-01"

            dca = DCABacktest(code, "A股")
            print("\n  —— 跑普通 vs 增强对比 ——")
            r1 = dca.run(amount_per_period=amount, frequency=freq,
                         start_date=start, enhanced=False, verbose=False)
            r2 = dca.run(amount_per_period=amount, frequency=freq,
                         start_date=start, enhanced=True, verbose=False)

            m1, m2 = r1["metrics"], r2["metrics"]
            print(f"\n  {'指标':<16} {'普通定投':<16} {'增强定投':<16}")
            print("  " + "-" * 48)
            for k in ["总收益率", "年化收益", "总投入", "最终市值", "持有份额", "平均成本"]:
                print(f"  {k:<16} {str(m1.get(k,'')):<16} {str(m2.get(k,'')):<16}")

        elif choice == "0":
            return


# ============================================================
# A. AI 量化助手
# ============================================================

def _ai_menu():
    """AI 量化助手"""
    while True:
        print("\n" + "=" * 54)
        print("  🤖 AI 量化助手")
        print("=" * 54)
        print("  1. 📝 AI 复盘教练    — 分析交易记录，找行为偏差")
        print("  2. 🧪 AI 策略顾问    — 评估策略表现，给优化建议")
        print("  3. 💡 策略头脑风暴    — 用自然语言描述想法，AI完善")
        print("  4. 📰 今日市场简报    — AI 生成市场分析")
        print("  5. 🗣️ AI 自由对话     — 跟 AI 聊量化")
        print("  6. ⚙️ 配置 AI 连接")
        print("  7. 🧪 测试 AI 连接")
        print("  0. 返回主菜单")

        choice = input("\n  请选择 [0-7]: ").strip()

        if choice == "1":
            from src.ai.assistants import AITradeReviewer
            print("\n  ⏳ AI 分析交易记录中...")
            reviewer = AITradeReviewer()
            result = reviewer.review()
            print(f"\n{result}")

        elif choice == "2":
            from src.ai.assistants import AIStrategyAdvisor
            strategy = input("  策略名称 (回车=全部): ").strip() or None
            print("\n  ⏳ AI 分析回测数据中...")
            advisor = AIStrategyAdvisor()
            result = advisor.analyze(strategy)
            print(f"\n{result}")

        elif choice == "3":
            from src.ai.assistants import AIStrategyAdvisor
            idea = input("\n  描述你的策略想法:\n  > ").strip()
            if idea:
                print("\n  ⏳ AI 头脑风暴中...")
                advisor = AIStrategyAdvisor()
                result = advisor.brainstorm(idea)
                print(f"\n{result}")

        elif choice == "4":
            from src.ai.assistants import AIMarketAnalyst
            print("\n  ⏳ AI 生成市场简报...")
            analyst = AIMarketAnalyst()
            result = analyst.daily_brief()
            print(f"\n{result}")

        elif choice == "5":
            from src.ai.assistants import AIChat
            chat = AIChat()
            print("\n  🗣️ AI 自由对话 (输入 'exit' 退出)")
            print("  " + "-" * 50)
            while True:
                msg = input("\n  你: ").strip()
                if msg.lower() == "exit":
                    break
                if not msg:

                    continue
                print("  AI: ", end="", flush=True)
                try:
                    chat.ask_stream(msg)
                except Exception as e:
                    print(f"\n  ❌ {e}")

        elif choice == "6":
            from src.ai.assistants import setup_ai_config
            setup_ai_config()

        elif choice == "7":
            from src.ai.engine import llm
            print("\n  ⏳ 测试 AI 连接...")
            result = llm.ask("回复'连接成功！我是你的量化助手。'（20字以内）")
            print(f"\n  {result}")

        elif choice == "0":
            return


# ============================================================
# R. 每日快扫 — 刷新行情 · 扫描关注列表 · 信号汇总
# ============================================================

def _daily_scan():
    """每日快扫：刷新数据 + 默认列表因子扫描 + 信号排名"""
    import subprocess
    import os as _os

    print("\n" + "=" * 54)
    print("  🔄 每日快扫 — 刷新行情 & 信号扫描")
    print("=" * 54)

    choice = input("\n  模式: 1=快速扫描(因子评分) 2=完整诊断(含全策略回测) [1]: ").strip() or "1"

    full_flag = "--full" if choice == "2" else ""
    script = _os.path.join(_os.path.dirname(__file__), "daily_runner.py")
    python = _os.path.join(_os.path.dirname(__file__), ".venv", "Scripts", "python.exe")

    if not _os.path.exists(python):
        python = "python"

    print(f"\n  ⏳ 启动扫描...\n")
    cmd = f'"{python}" "{script}" {full_flag}'
    result = subprocess.run(cmd, shell=True, cwd=_os.path.dirname(__file__),
                           capture_output=False)

    if result.returncode != 0:
        print(f"\n  ⚠️ 扫描过程出错，请检查网络和依赖。")
    else:
        input("\n  按回车返回主菜单...")


# ============================================================
# D. 个股诊断 — 全策略扫描 · 投资者适配 · 时机仓位
# ============================================================

def _stock_diagnosis():
    """个股诊断：运行全部策略 → 投资者适配 → 入场时机 → 仓位建议 → 综合报告"""
    from src.strategies.library import STRATEGIES
    from src.factors.composer import PRESET_STRATEGIES
    from src.backtest.data_feed import get_data
    from src.factors.definitions import FactorCalculator
    from datetime import datetime as _dt

    print("\n" + "=" * 60)
    print("  🩺 个股诊断 — 全面策略体检")
    print("=" * 60)

    # 输入
    print("\n  📌 选择诊断标的")
    symbol = input("    股票代码 [601398]: ").strip() or "601398"
    market = input("    市场 (A股/美股/港股) [A股]: ").strip() or "A股"
    start = input("    回测起始日期 [2022-01-01]: ").strip() or "2022-01-01"

    # 加载数据 — 自动检查并刷新到最新
    print(f"\n  ⏳ 检查 {market} {symbol} 数据新鲜度...")
    today_str = _dt.now().strftime("%Y-%m-%d")
    data_fresh = False
    try:
        from src.backtest.data_feed import get_data_summary, download_watchlist
        cache_df = get_data_summary()
        if not cache_df.empty:
            target_file = f"{market}_{symbol}_daily.csv"
            mask = cache_df["文件"] == target_file
            if mask.any():
                row = cache_df[mask].iloc[0]
                latest = str(row["结束日期"]).strip()[:10]
                if latest >= today_str:
                    data_fresh = True
                    print(f"  ✅ 数据已是最新 ({latest})")
    except Exception:
        pass

    if not data_fresh:
        print(f"  🔄 拉取最新行情数据...")
        try:
            download_watchlist([{"symbol": symbol, "market": market, "name": symbol}], verbose=False)
            print(f"  ✅ 数据已更新到 {today_str}")
        except Exception as e:
            print(f"  ⚠️ 自动刷新失败: {e}，使用缓存数据")

    print(f"  ⏳ 加载行情数据...")
    try:
        data = get_data(symbol, market, start_date=start)
    except Exception as e:
        print(f"  ❌ 数据获取失败: {e}")
        return

    if data is None or len(data) == 0:
        print(f"  ❌ 未获取到 {symbol} 的数据，请检查代码和市场。")
        return
    print(f"  ✅ {len(data)} 条 ({str(data['date'].iloc[0])[:10]} ~ {str(data['date'].iloc[-1])[:10]})")

    # 阶段1: 全策略回测
    print(f"\n  ⏳ 运行全部策略回测 (11个)...")
    strategies_results = _run_all_strategies_on_stock(symbol, market, data)
    success_count = sum(1 for r in strategies_results if not r["error"])
    print(f"  ✅ {success_count}/{len(strategies_results)} 策略完成")

    # 阶段2: 因子分析
    print(f"  ⏳ 计算18个因子...")
    try:
        calc = FactorCalculator(data)
        factors_df = calc.compute_all()
        current_factors = factors_df.iloc[-1]
    except Exception:
        current_factors = None
        print(f"  ⚠️ 因子计算失败，入场时机分析将跳过")

    # 生成报告
    _print_diagnosis_report(symbol, market, data, strategies_results, current_factors)


def _run_all_strategies_on_stock(symbol, market, data):
    """对单只股票运行全部11个策略，返回排序后的结果列表"""
    from src.strategies.library import STRATEGIES
    from src.factors.composer import PRESET_STRATEGIES
    from src.backtest.engine import BacktestEngine
    from src.backtest.batch_runner import _make_strategy_instance

    results = []
    all_strategies = list(STRATEGIES.keys()) + list(PRESET_STRATEGIES.keys())

    for key in all_strategies:
        # 获取中文名
        name = key
        for d in [STRATEGIES, PRESET_STRATEGIES]:
            if key in d:
                name = d[key].get("name", key)
                break
        try:
            strategy = _make_strategy_instance(key, {}, symbol)
            engine = BacktestEngine()
            result = engine.run(strategy, data)
            results.append({
                "key": key, "name": name,
                "metrics": result["metrics"],
                "error": None,
            })
        except Exception as e:
            results.append({
                "key": key, "name": name,
                "metrics": {}, "error": str(e),
            })

    # 按夏普降序排列
    def _parse_sharpe(r):
        if r["error"]:
            return -999
        v = r["metrics"].get("夏普比率", -999)
        try:
            return float(str(v))
        except (ValueError, TypeError):
            return -999

    results.sort(key=_parse_sharpe, reverse=True)
    return results


def _match_investor_profiles(strategies_results):
    """根据策略表现匹配投资者画像，返回画像评分列表"""
    import math

    def _parse_metric(m, key):
        """安全解析指标值为 float"""
        v = m.get(key, 0)
        if isinstance(v, str):
            v = v.replace("%", "").replace("+", "").replace("¥", "").replace(",", "").strip()
        try:
            return float(v)
        except (ValueError, TypeError):
            return 0.0

    profiles = [
        {
            "name": "保守型", "icon": "🛡️",
            "strategies": ["mean_reversion", "bollinger", "mean_reversion_v2"],
            "max_dd": 5.0, "min_wr": 50.0, "min_sharpe": 0.2,
            "risk_pct": 0.01, "desc": "注重本金安全，追求低波动下的稳定收益",
        },
        {
            "name": "稳健型", "icon": "⚖️",
            "strategies": ["ma_cross", "macd", "rsi", "trend_following_v1"],
            "max_dd": 15.0, "min_wr": 40.0, "min_sharpe": 0.5,
            "risk_pct": 0.015, "desc": "平衡风险收益，追求中等回报与可控回撤",
        },
        {
            "name": "进取型", "icon": "🚀",
            "strategies": ["momentum", "turtle", "volume_breakout_v1"],
            "max_dd": 30.0, "min_wr": 35.0, "min_sharpe": 0.3,
            "risk_pct": 0.02, "desc": "容忍较大波动，追求超额收益",
        },
        {
            "name": "逆向型", "icon": "🔄",
            "strategies": ["contrarian_v1", "mean_reversion", "mean_reversion_v2"],
            "max_dd": 15.0, "min_wr": 45.0, "min_sharpe": 0.2,
            "risk_pct": 0.015, "desc": "逆势交易，善于在市场恐慌时入场",
        },
    ]

    total = len(strategies_results)
    result_profiles = []

    for prof in profiles:
        # 筛选相关策略
        relevant = [(i, r) for i, r in enumerate(strategies_results)
                    if r["key"] in prof["strategies"] and not r["error"]]

        if not relevant:
            result_profiles.append({
                **prof, "matched": False, "match_score": 0,
                "reasons": ["无相关策略数据"], "top_strategies": [],
            })
            continue

        # 排名分 (0-25)
        rank_scores = sum((total - (idx + 1)) / total * 25 for idx, _ in relevant) / len(relevant)

        # 夏普分 (0-30)
        avg_sharpe = sum(_parse_metric(r["metrics"], "夏普比率") for _, r in relevant) / len(relevant)
        sharpe_score = min(30, max(0, avg_sharpe / max(prof["min_sharpe"], 0.01) * 15))

        # 回撤分 (0-25)
        avg_dd = sum(abs(_parse_metric(r["metrics"], "最大回撤")) for _, r in relevant) / len(relevant)
        dd_score = max(0, min(25, (1 - avg_dd / max(prof["max_dd"], 0.1)) * 25))

        # 胜率分 (0-20)
        avg_wr = sum(_parse_metric(r["metrics"], "胜率") for _, r in relevant) / len(relevant)
        wr_score = min(20, avg_wr / max(prof["min_wr"], 1) * 15)

        match_score = round(rank_scores + sharpe_score + dd_score + wr_score, 1)
        matched = match_score >= 40

        reasons = []
        if avg_sharpe >= prof["min_sharpe"]:
            reasons.append(f"夏普({avg_sharpe:.2f})达标 ✓")
        else:
            reasons.append(f"夏普({avg_sharpe:.2f})偏低 ✗")
        if abs(avg_dd) <= prof["max_dd"]:
            reasons.append(f"回撤({abs(avg_dd):.1f}%)可控 ✓")
        else:
            reasons.append(f"回撤({abs(avg_dd):.1f}%)偏高 ✗")
        if avg_wr >= prof["min_wr"]:
            reasons.append(f"胜率({avg_wr:.1f}%)满足 ✓")
        else:
            reasons.append(f"胜率({avg_wr:.1f}%)不足 ✗")

        # 该画像下最优策略
        top = sorted(relevant, key=lambda x: _parse_metric(x[1]["metrics"], "夏普比率"), reverse=True)[:3]
        top_list = [{
            "key": r["key"], "name": r["name"],
            "sharpe": _parse_metric(r["metrics"], "夏普比率"),
            "total_return": r["metrics"].get("总收益率", "N/A"),
            "max_drawdown": r["metrics"].get("最大回撤", "N/A"),
            "win_rate": r["metrics"].get("胜率", "N/A"),
        } for _, r in top]

        result_profiles.append({
            "name": prof["name"], "icon": prof["icon"],
            "desc": prof["desc"], "risk_pct": prof["risk_pct"],
            "matched": matched, "match_score": match_score,
            "reasons": reasons, "top_strategies": top_list,
        })

    return result_profiles


def _analyze_entry_timing(current_factors):
    """根据当前因子值计算入场时机评分 (0-100)"""
    if current_factors is None:
        return {"score": 50, "level": "⚠️ 无法判断", "signals": [],
                "summary": "因子数据不可用，请手动判断。"}

    def _fv(name, default=0.5):
        v = current_factors.get(name, default)
        try:
            return float(v)
        except (ValueError, TypeError):
            return default

    signals = []

    # RSI
    rsi = _fv("rsi_norm")
    if rsi < 0.3:
        s = int((0.3 - rsi) / 0.3 * 20)
        signals.append(("RSI 超卖", f"{rsi*100:.0f}", "买入信号: 超卖区域", s))
    elif rsi > 0.7:
        s = -int((rsi - 0.7) / 0.3 * 20)
        signals.append(("RSI 超买", f"{rsi*100:.0f}", "卖出信号: 超买区域", s))
    else:
        signals.append(("RSI 中性", f"{rsi*100:.0f}", "中性区间", 5))

    # 布林位置
    bb = _fv("bollinger_pos")
    if bb < 0.2:
        s = int((0.2 - bb) / 0.2 * 20)
        signals.append(("布林下轨", f"{bb:.2f}", "价格接近下轨, 支撑较强", s))
    elif bb > 0.8:
        s = -int((bb - 0.8) / 0.2 * 20)
        signals.append(("布林上轨", f"{bb:.2f}", "价格接近上轨, 压力较大", s))
    else:
        signals.append(("布林中轨", f"{bb:.2f}", "布林带中轨附近", 5))

    # 均线排列
    ma = _fv("ma_alignment")
    if ma > 0.7:
        signals.append(("均线多头", f"{ma:.2f}", "均线多头排列, 趋势健康", 15))
    elif ma < 0.3:
        signals.append(("均线空头", f"{ma:.2f}", "均线空头排列, 趋势偏弱", -10))
    else:
        signals.append(("均线缠绕", f"{ma:.2f}", "均线方向不明", 0))

    # MACD
    macd_h = _fv("macd_hist", 0.5)
    if macd_h > 0.55:
        signals.append(("MACD动能↑", f"{macd_h:.2f}", "动能向上, 看涨", 15))
    elif macd_h < 0.45:
        signals.append(("MACD动能↓", f"{macd_h:.2f}", "动能减弱, 谨慎", -10))
    else:
        signals.append(("MACD中性", f"{macd_h:.2f}", "动能中性", 0))

    # 量比
    vol = _fv("volume_ratio")
    if vol > 0.7:
        signals.append(("放量", f"{vol:.2f}", "成交量活跃, 参与度高", 10))
    elif vol < 0.3:
        signals.append(("缩量", f"{vol:.2f}", "交投清淡", -5))
    else:
        signals.append(("量能正常", f"{vol:.2f}", "成交量正常", 3))

    # 形态
    hammer = _fv("hammer", 0)
    engulf = _fv("engulfing", 0)
    if hammer > 0.5:
        signals.append(("锤子线", f"{hammer:.2f}", "底部反转形态", 10))
    if engulf > 0.5:
        signals.append(("吞没形态", f"{engulf:.2f}", "看涨吞没形态", 10))
    if hammer <= 0.5 and engulf <= 0.5:
        signals.append(("无形态信号", "-", "无显著反转形态", 0))

    # 动量
    mom = _fv("momentum_score")
    if mom > 0.6:
        signals.append(("动量强劲", f"{mom:.2f}", "多周期动量向上", 10))
    elif mom < 0.4:
        signals.append(("动量疲弱", f"{mom:.2f}", "多周期动量偏弱", -5))
    else:
        signals.append(("动量中性", f"{mom:.2f}", "动量不显著", 2))

    # 趋势强度
    trend = _fv("trend_strength")
    if trend > 0.5:
        signals.append(("趋势明确", f"{trend:.2f}", "存在明显趋势", 5))
    else:
        signals.append(("趋势不明", f"{trend:.2f}", "震荡市或趋势弱", -3))

    # 综合评分
    total = 50 + sum(s[3] for s in signals)
    total = max(0, min(100, total))

    if total >= 80:
        level = "🟢 强烈买入"
        summary = "多个技术指标共振看涨，是较好的入场时机。建议积极关注，可在回调时择机入场。"
    elif total >= 60:
        level = "🟡 谨慎买入"
        summary = "部分指标支持入场，但存在一定分歧。建议小仓位试探或等待更好时机。"
    elif total >= 40:
        level = "⚪ 观望等待"
        summary = "信号中性偏弱，方向不明朗。建议暂不操作，等待趋势明朗后再入场。"
    elif total >= 20:
        level = "🔴 建议回避"
        summary = "多个指标偏空，风险收益比不理想。建议耐心等待，不要急于入场。"
    else:
        level = "⛔ 强烈回避"
        summary = "几乎所有指标给出看空信号，风险极高。强烈建议回避。"

    return {"score": total, "level": level, "signals": signals, "summary": summary}


def _calculate_position_sizing(data, profile_name, config_obj):
    """基于ATR和风险偏好计算仓位建议"""
    from src.factors.definitions import FactorCalculator
    import pandas as pd

    calc = FactorCalculator(data)
    current_price = float(data["close"].iloc[-1])

    # ATR
    atr_ratio_val = calc.f_atr_ratio().iloc[-1]
    atr_value = float(atr_ratio_val * current_price) if not pd.isna(atr_ratio_val) else current_price * 0.02
    atr_pct = (atr_value / current_price) * 100 if current_price > 0 else 0

    # 风险参数
    risk_map = {"保守型": 0.01, "稳健型": 0.015, "进取型": 0.02, "逆向型": 0.015}
    stop_map = {"保守型": 2.0, "稳健型": 2.0, "进取型": 2.5, "逆向型": 2.0}
    risk_pct = risk_map.get(profile_name, 0.015)
    stop_mult = stop_map.get(profile_name, 2.0)

    capital = getattr(config_obj, 'initial_capital', 100000)

    # 止损
    stop_distance = atr_value * stop_mult
    stop_price = current_price - stop_distance
    stop_pct = (stop_distance / current_price) * 100

    # 风险金额
    risk_amount = capital * risk_pct

    # 股数
    lot_size = 100
    raw_qty = risk_amount / stop_distance if stop_distance > 0 else 0
    position_shares = int(raw_qty / lot_size) * lot_size

    position_value = position_shares * current_price
    position_pct = (position_value / capital) * 100 if capital > 0 else 0

    # 波动调整
    vol_val = float(calc.f_volatility().iloc[-1]) if not pd.isna(calc.f_volatility().iloc[-1]) else 0.5
    vol_mult = 0.7 + 0.6 * vol_val
    adj_shares = max(lot_size, int(position_shares * vol_mult / lot_size) * lot_size)
    adj_value = adj_shares * current_price
    adj_pct = (adj_value / capital) * 100

    # 总仓位建议
    if profile_name == "保守型":
        total_alloc_pct = min(adj_pct * 2, 20)
    elif profile_name == "进取型":
        total_alloc_pct = min(adj_pct * 3, 50)
    else:
        total_alloc_pct = min(adj_pct * 2.5, 35)

    notes = []
    if adj_pct > 30:
        notes.append("⚠️ 单笔仓位超过30%，建议分批建仓")
    if atr_pct > 5:
        notes.append("⚠️ 当前波动率较高，建议缩小仓位或等待波动率下降")
    if position_shares == 0:
        notes.append("⚠️ 资金不足以购买最小单位(100股)，建议增加本金")
    if adj_pct < 1:
        notes.append("💡 建议仓位极低，可考虑优先关注而非立即买入")

    return {
        "current_price": current_price,
        "atr_value": atr_value,
        "atr_pct": atr_pct,
        "stop_distance": stop_distance,
        "stop_price": stop_price,
        "stop_pct": stop_pct,
        "risk_pct": risk_pct * 100,
        "risk_amount": risk_amount,
        "suggested_shares": adj_shares,
        "suggested_value": round(adj_value, 2),
        "suggested_pct": round(adj_pct, 1),
        "total_alloc_pct": round(total_alloc_pct, 1),
        "total_alloc_value": round(capital * total_alloc_pct / 100, 2),
        "notes": notes,
    }


def _print_diagnosis_report(symbol, market, data, strategies_results, current_factors):
    """格式化打印个股诊断报告"""
    from datetime import datetime as _dt
    from src.config import config

    # 子分析
    profiles = _match_investor_profiles(strategies_results)
    best_profile = max(profiles, key=lambda p: p["match_score"])
    timing = _analyze_entry_timing(current_factors)
    sizing = _calculate_position_sizing(data, best_profile["name"], config)

    current_price = sizing["current_price"]
    date_start = str(data["date"].iloc[0])[:10]
    date_end = str(data["date"].iloc[-1])[:10]

    # ═══ 报告头 ═══
    # 数据新鲜度标记
    today_str = _dt.now().strftime("%Y-%m-%d")
    freshness_tag = "🟢 今日" if date_end >= today_str else f"⚠️ 仅到 {date_end}"

    print(f"\n{'═' * 62}")
    print(f"  🩺 个股诊断报告: {symbol}    {_dt.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'═' * 62}")
    print(f"  市场: {market}  |  数据区间: {date_start} ~ {date_end}  |  K线: {len(data)} 条")
    print(f"  数据状态: {freshness_tag}  |  当前价格: ¥{current_price:.2f}")

    # ═══ 一、历史策略表现 ═══
    print(f"\n{'─' * 62}")
    print(f"  📈 一、历史策略表现 (近{len(data)}条K线)")
    print(f"{'─' * 62}")
    print(f"  {'排名':<4} {'策略名称':<14} {'总收益':>8} {'夏普':>6} {'最大回撤':>8} {'胜率':>6}")
    print(f"  {'─' * 4} {'─' * 14} {'─' * 8} {'─' * 6} {'─' * 8} {'─' * 6}")

    for i, r in enumerate(strategies_results, 1):
        if r["error"]:
            print(f"  {i:<4} {r['name']:<14} {'ERR':>8} {'-':>6} {'-':>8} {'-':>6}")
        else:
            m = r["metrics"]
            sharpe = m.get("夏普比率", "-")
            ret = m.get("总收益率", "-")
            dd = m.get("最大回撤", "-")
            wr = m.get("胜率", "-")
            # 高亮前三
            prefix = "🏆" if i == 1 else ("🥈" if i == 2 else ("🥉" if i == 3 else "  "))
            print(f"  {prefix}{i:<2} {r['name']:<14} {str(ret):>8} {str(sharpe):>6} {str(dd):>8} {str(wr):>6}")

    # 最佳最差
    best = strategies_results[0]
    worst = strategies_results[-1]
    if not best["error"] and not worst["error"]:
        print(f"\n  🏆 最佳: {best['name']} (夏普 {best['metrics'].get('夏普比率','?')})"
              f"    ⚠️ 最差: {worst['name']} (夏普 {worst['metrics'].get('夏普比率','?')})")

    # ═══ 二、投资者适配 ═══
    print(f"\n{'─' * 62}")
    print(f"  👤 二、投资者适配分析")
    print(f"{'─' * 62}")

    for p in profiles:
        stars = "★" * int(p["match_score"] / 20) + "☆" * (5 - int(p["match_score"] / 20))
        status = "✅ 适合" if p["matched"] else "⚠️ 需谨慎"
        marker = " ← 最佳推荐" if p["name"] == best_profile["name"] else ""
        print(f"\n  {p['icon']} {p['name']}  匹配度: {p['match_score']:.0f}/100 {stars} {status}{marker}")
        print(f"     {p['desc']}")
        if p["reasons"]:
            print(f"     {' | '.join(p['reasons'])}")
        if p["top_strategies"]:
            print(f"     推荐策略:")
            for ts in p["top_strategies"]:
                print(f"       · {ts['name']:<12} 夏普 {ts['sharpe']}, 收益 {ts['total_return']}, "
                      f"回撤 {ts['max_drawdown']}, 胜率 {ts['win_rate']}")

    print(f"\n  📋 推荐画像: {best_profile['icon']} {best_profile['name']} (匹配度 {best_profile['match_score']:.0f}/100)")

    # ═══ 三、入场时机 ═══
    print(f"\n{'─' * 62}")
    print(f"  ⏰ 三、当前入场时机分析")
    print(f"{'─' * 62}")

    if timing["signals"]:
        print(f"  {'因子信号':<12} {'当前值':<10} {'判断':<30} {'贡献':>5}")
        print(f"  {'─' * 12} {'─' * 10} {'─' * 30} {'─' * 5}")
        for name, val, desc, contrib in timing["signals"]:
            contrib_str = f"+{contrib}" if contrib > 0 else str(contrib)
            print(f"  {name:<12} {val:<10} {desc:<30} {contrib_str:>5}")

    # 评分条
    score = timing["score"]
    bar_len = 20
    filled = int(score / 100 * bar_len)
    bar = "█" * filled + "░" * (bar_len - filled)
    print(f"\n  综合评分: {score}/100  [{bar}]  {timing['level']}")
    print(f"  💡 {timing['summary']}")

    # ═══ 四、仓位建议 ═══
    print(f"\n{'─' * 62}")
    print(f"  💰 四、仓位建议 (基于 {best_profile['icon']} {best_profile['name']} 偏好)")
    print(f"{'─' * 62}")

    print(f"  📊 风险参数:")
    print(f"     当前价格:  ¥{sizing['current_price']:.2f}")
    print(f"     ATR(14):   ¥{sizing['atr_value']:.2f} ({sizing['atr_pct']:.1f}%)")
    print(f"     止损距离:  ¥{sizing['stop_distance']:.2f} (ATR × 止损倍数)")
    print(f"     止损价:    ¥{sizing['stop_price']:.2f} ({sizing['stop_pct']:.1f}%)")
    print(f"     风险金额:  ¥{sizing['risk_amount']:,.0f} (本金 {sizing['risk_pct']:.1f}%)")

    print(f"\n  📐 仓位计算:")
    print(f"     建议股数:  {sizing['suggested_shares']:,} 股 ({sizing['suggested_shares']//100} 手)")
    print(f"     建议金额:  ¥{sizing['suggested_value']:,.0f}")
    print(f"     单笔仓位:  {sizing['suggested_pct']:.1f}%")
    print(f"     建议总仓位: {sizing['total_alloc_pct']:.1f}% (约 ¥{sizing['total_alloc_value']:,.0f})")

    if sizing["notes"]:
        print(f"\n  ⚠️ 注意事项:")
        for note in sizing["notes"]:
            print(f"     {note}")

    # ═══ 五、综合建议 ═══
    print(f"\n{'─' * 62}")
    print(f"  📋 五、综合建议")
    print(f"{'─' * 62}")

    # 自动生成行动建议
    action_parts = []
    if best_profile["matched"]:
        action_parts.append(f"该股票最适合{best_profile['icon']} {best_profile['name']}投资者")
    else:
        action_parts.append(f"该股票与各投资者画像匹配度均不高，建议谨慎对待")

    if timing["score"] >= 60:
        action_parts.append(f"当前入场评分为{score}分，技术面偏多")
        action = "可以考虑入场"
    elif timing["score"] >= 40:
        action_parts.append(f"当前入场评分为{score}分，信号中性")
        action = "建议观望等待"
    else:
        action_parts.append(f"当前入场评分为{score}分，技术面偏空")
        action = "建议暂时回避"

    action_parts.append(f"建议单笔仓位{sizing['suggested_pct']:.0f}%，总仓位不超{sizing['total_alloc_pct']:.0f}%")

    print(f"  {'；'.join(action_parts)}。")

    print(f"\n  ⚡ 行动计划:")
    if timing["score"] >= 60:
        print(f"     1. 以 ¥{current_price:.2f} 附近建仓 {sizing['suggested_shares']:,} 股")
        print(f"     2. 止损设置在 ¥{sizing['stop_price']:.2f} (ATR {sizing['stop_pct']:.1f}%)")
        print(f"     3. 首笔投入 ¥{sizing['suggested_value']:,.0f} ({sizing['suggested_pct']:.1f}%仓位)")
        print(f"     4. 若盈利趋势确认，可加仓至 {sizing['total_alloc_pct']:.0f}% (约 ¥{sizing['total_alloc_value']:,.0f})")
    else:
        print(f"     1. 将该股票加入关注列表，等待入场信号")
        print(f"     2. 关注 RSI 回落至 30 以下或布林下轨支撑确认")
        print(f"     3. 备好资金约 ¥{sizing['total_alloc_value']:,.0f} ({sizing['total_alloc_pct']:.0f}%仓位)")

    print(f"{'═' * 62}\n")


# ============================================================
# 入口
# ============================================================

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--report":
        print("\n  ⏳ 生成每日简报...")
        try:
            from src.report.generator import generate_daily_report
            path = generate_daily_report()
            print(f"\n  ✅ 简报已生成: {path}")
            import webbrowser
            webbrowser.open(f"file:///{path.replace(chr(92), '/')}")
        except Exception as e:
            print(f"\n  ❌ 生成失败: {e}")
    elif len(sys.argv) > 1 and sys.argv[1] == "--discover":
        symbol = sys.argv[2] if len(sys.argv) > 2 else "600519"
        gens = 30
        pop = 80
        for i, arg in enumerate(sys.argv):
            if arg == "--gens" and i + 1 < len(sys.argv):
                gens = int(sys.argv[i + 1])
            if arg == "--pop" and i + 1 < len(sys.argv):
                pop = int(sys.argv[i + 1])
        print(f"\n  [Miner] 因子发现: {symbol} ({gens}代, {pop}种群)")
        try:
            from src.ai.factor_discovery import run_discover_cli
            run_discover_cli(symbol, generations=gens, population=pop)
        except Exception as e:
            print(f"\n  FAIL: {e}")

    elif len(sys.argv) > 1 and sys.argv[1] == "--tune":
        strategy = sys.argv[2] if len(sys.argv) > 2 else "ma_cross"
        symbol = "601398"
        trials = 50
        for i, arg in enumerate(sys.argv):
            if arg == "--symbol" and i + 1 < len(sys.argv):
                symbol = sys.argv[i + 1]
            if arg == "--trials" and i + 1 < len(sys.argv):
                trials = int(sys.argv[i + 1])
        print(f"\n  [Tuner] 开始调优: {strategy} on {symbol} ({trials} trials)")
        try:
            from src.utils.strategy_tuner import run_tune_cli
            best = run_tune_cli(strategy, symbol=symbol, n_trials=trials)
            if best:
                print(f"\n  OK 最佳参数已保存到 config/best_params.json")
        except Exception as e:
            print(f"\n  FAIL 调优失败: {e}")
    else:
        main()





