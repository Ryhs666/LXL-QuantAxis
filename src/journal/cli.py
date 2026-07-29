"""
交易日志 CLI — 交互式命令行工具

功能：
- 录交易（买入/卖出），卖出时自动配对
- 写复盘笔记 + 评分
- 查看交易历史（支持筛选）
- CSV 导入 / 导出
- 盈亏汇总
"""

import sys
import os
from datetime import datetime
from typing import Optional

# ---- Windows 中文编码修复 ----
if sys.platform == "win32":
    try:
        sys.stdin.reconfigure(encoding="utf-8")
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# 确保 src 在 path 中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.models.trade import Trade, TradeRepository


# ============================================================
# 工具函数
# ============================================================

def _input(prompt: str, default: str = "", allow_empty: bool = False) -> str:
    """带默认值的输入"""
    if default:
        result = input(f"{prompt} [{default}]: ").strip()
        return result if result else default
    while True:
        result = input(f"{prompt}: ").strip()
        if result or allow_empty:
            return result
        print("  ❌ 此项不能为空，请重新输入。")


def _input_float(prompt: str, default: float = None) -> float:
    """输入浮点数"""
    hint = f" [{default}]" if default is not None else ""
    while True:
        try:
            s = input(f"{prompt}{hint}: ").strip()
            if s == "" and default is not None:
                return default
            return float(s)
        except ValueError:
            print("  ❌ 请输入有效数字。")


def _input_int(prompt: str, default: int = None) -> int:
    """输入整数"""
    hint = f" [{default}]" if default is not None else ""
    while True:
        try:
            s = input(f"{prompt}{hint}: ").strip()
            if s == "" and default is not None:
                return default
            return int(s)
        except ValueError:
            print("  ❌ 请输入有效整数。")


def _input_date(prompt: str) -> str:
    """输入日期（YYYY-MM-DD），默认今天"""
    today = datetime.now().strftime("%Y-%m-%d")
    while True:
        s = input(f"{prompt} [{today}]: ").strip()
        if s == "":
            return today
        try:
            datetime.strptime(s, "%Y-%m-%d")
            return s
        except ValueError:
            print("  ❌ 日期格式错误，请用 YYYY-MM-DD。")


def _select(options: list, prompt: str = "请选择") -> str:
    """选择一个选项"""
    print(f"\n  {prompt}：")
    for i, opt in enumerate(options, 1):
        print(f"    {i}. {opt}")
    while True:
        try:
            idx = int(input("  > ").strip()) - 1
            if 0 <= idx < len(options):
                return options[idx]
            print(f"  ❌ 请输入 1-{len(options)}。")
        except ValueError:
            print(f"  ❌ 请输入数字 1-{len(options)}。")


def _confirm(prompt: str) -> bool:
    """确认操作"""
    s = input(f"{prompt} (y/n): ").strip().lower()
    return s in ("y", "yes", "是")


# ============================================================
# 交易日志 CLI
# ============================================================

class JournalCLI:
    """交易日志交互式命令行"""

    def __init__(self, db_path: str = None):
        self.repo = TradeRepository(db_path)

    # ---- 主菜单 ----

    def menu(self):
        """显示交易日志子菜单"""
        while True:
            print("\n" + "=" * 50)
            print("  📒 交易日志")
            print("=" * 50)
            print("  1. 记录买入")
            print("  2. 记录卖出")
            print("  3. 查看交易历史")
            print("  4. 查看当前持仓")
            print("  5. 写复盘笔记")
            print("  6. 盈亏汇总")
            print("  7. 导出 CSV")
            print("  8. 导入 CSV")
            print("  0. 返回主菜单")

            choice = input("\n  请选择 [0-8]: ").strip()

            if choice == "1":
                self._record_buy()
            elif choice == "2":
                self._record_sell()
            elif choice == "3":
                self._view_history()
            elif choice == "4":
                self._view_positions()
            elif choice == "5":
                self._add_review()
            elif choice == "6":
                self._pnl_summary()
            elif choice == "7":
                self._export_csv()
            elif choice == "8":
                self._import_csv()
            elif choice == "0":
                break
            else:
                print("  ❌ 无效选择。")

    # ---- 1. 记录买入 ----

    def _record_buy(self):
        print("\n  —— 记录买入 ——")
        market = _select(["A股", "美股"], "选择市场")
        symbol = _input("股票代码", allow_empty=False)
        name = _input("股票名称", allow_empty=False)
        direction = _select(["做多", "做空"], "方向")
        trade_date = _input_date("交易日期")
        price = _input_float("成交价")
        quantity = _input_int("成交股数")
        fee = _input_float("手续费", default=0.0)
        reason = _input("买入理由", allow_empty=True)
        strategy = _input("所属策略（可留空）", allow_empty=True)
        tags = _input("标签（逗号分隔，可留空）", allow_empty=True)

        trade = Trade(
            market=market, symbol=symbol.upper(), name=name,
            direction=direction, trade_type="买入",
            trade_date=trade_date, price=price, quantity=quantity,
            fee=fee, reason=reason, strategy_name=strategy, tags=tags,
        )

        trade_id = self.repo.add(trade)
        print(f"\n  ✅ 买入记录已保存！ID: {trade_id}")
        print(f"     {trade.symbol} {trade.name} | "
              f"{trade.trade_date} | {trade.direction}买入 | "
              f"¥{trade.price} × {trade.quantity}股")

    # ---- 2. 记录卖出 ----

    def _record_sell(self):
        print("\n  —— 记录卖出 ——")

        # 先查持仓，方便选择
        market = _select(["A股", "美股", "不限"], "选择市场")
        market_filter = None if market == "不限" else market
        positions = self.repo.find_open_positions(market=market_filter)

        if not positions:
            print(f"  📭 当前{' ' + market if market != '不限' else ''}没有持仓。")
            return

        print(f"\n  当前持仓（{len(positions)} 只）：")
        for i, p in enumerate(positions, 1):
            print(f"    {i}. [{p.id}] {p.symbol} {p.name} | "
                  f"{p.trade_date} | ¥{p.price} × {p.quantity}股 | {p.direction}")

        use_existing = _confirm("\n  是否针对已有持仓卖出？")
        paired_id = None

        if use_existing:
            idx = _input_int(f"  选择持仓编号 1-{len(positions)}") - 1
            if 0 <= idx < len(positions):
                paired_id = positions[idx].id
                buy = positions[idx]
                print(f"  已选择: {buy.symbol} {buy.name} 买入价 ¥{buy.price}")

        market = _select(["A股", "美股"], "选择市场（卖出）")
        symbol = _input("股票代码", allow_empty=False)
        name = _input("股票名称", allow_empty=True)
        direction = _select(["做多", "做空"], "方向")
        trade_date = _input_date("交易日期")
        price = _input_float("卖出价")
        quantity = _input_int("成交股数")
        fee = _input_float("手续费", default=0.0)
        reason = _input("卖出理由", allow_empty=True)
        tags = _input("标签（逗号分隔，可留空）", allow_empty=True)

        trade = Trade(
            market=market, symbol=symbol.upper(), name=name,
            direction=direction, trade_type="卖出",
            trade_date=trade_date, price=price, quantity=quantity,
            fee=fee, reason=reason, tags=tags,
        )

        sell_id = self.repo.add(trade)

        # 自动配对
        if paired_id:
            self.repo.set_paired_trade(paired_id, sell_id)
            pnl = self.repo.calc_pnl(paired_id)
            if pnl:
                emoji = "🟢" if pnl["net_pnl"] >= 0 else "🔴"
                print(f"\n  ✅ 卖出记录已保存！ID: {sell_id}")
                print(f"     {emoji} 盈亏: ¥{pnl['net_pnl']:+,.2f} ({pnl['pnl_pct']:+.2f}%)")
        else:
            print(f"\n  ✅ 卖出记录已保存！ID: {sell_id}")

    # ---- 3. 查看历史 ----

    def _view_history(self):
        print("\n  —— 查看交易历史 ——")

        market = _select(["全部", "A股", "美股"], "选择市场")
        market = None if market == "全部" else market

        trade_type = _select(["全部", "买入", "卖出"], "交易类型")
        trade_type = None if trade_type == "全部" else trade_type

        strategy = _input("按策略筛选（回车跳过）", allow_empty=True)
        strategy = strategy if strategy else None

        date_from = _input("起始日期（YYYY-MM-DD，回车跳过）", allow_empty=True)
        date_from = date_from if date_from else None

        date_to = _input("结束日期（YYYY-MM-DD，回车跳过）", allow_empty=True)
        date_to = date_to if date_to else None

        trades = self.repo.find_all(
            market=market, symbol=None, trade_type=trade_type,
            strategy_name=strategy, date_from=date_from, date_to=date_to,
            limit=200,
        )

        if not trades:
            print("  📭 没有匹配的记录。")
            return

        self._print_trade_table(trades)

    # ---- 4. 查看持仓 ----

    def _view_positions(self):
        positions = self.repo.find_open_positions()
        if not positions:
            print("\n  📭 当前没有持仓。")
            return

        print(f"\n  —— 当前持仓（{len(positions)} 只） ——")
        total_cost = 0
        for i, p in enumerate(positions, 1):
            cost = p.price * p.quantity
            total_cost += cost
            days = (datetime.now() - datetime.strptime(p.trade_date, "%Y-%m-%d")).days
            print(f"  {i}. [{p.id}] {p.market} | {p.symbol} {p.name} | {p.direction}")
            print(f"     买入日: {p.trade_date}（持仓 {days} 天）| "
                  f"¥{p.price} × {p.quantity}股 | 成本: ¥{cost:,.0f}")

        print(f"\n  💰 持仓总成本: ¥{total_cost:,.0f}")

    # ---- 5. 写复盘 ----

    def _add_review(self):
        print("\n  —— 写复盘笔记 ——")

        market = _select(["A股", "美股", "不限"], "选择市场")
        market = None if market == "不限" else market

        # 找未复盘的交易（已完成配对、未写复盘）
        trades = self.repo.find_all(
            market=market, trade_type=None, limit=200,
        )
        unreviewed = [t for t in trades if not t.review_notes and t.review_score == 0]

        if not unreviewed:
            print("  📭 没有待复盘的交易。")
            return

        print(f"\n  待复盘的交易（{len(unreviewed)} 笔）：")
        for i, t in enumerate(unreviewed, 1):
            print(f"    {i}. [{t.id}] {t.trade_date} | {t.symbol} {t.name} | "
                  f"{t.trade_type} | {t.direction}")

        idx = _input_int(f"  选择要复盘的编号 1-{len(unreviewed)}") - 1
        if not (0 <= idx < len(unreviewed)):
            print("  ❌ 无效选择。")
            return

        trade = unreviewed[idx]
        print(f"\n  复盘: [{trade.id}] {trade.symbol} {trade.name}")
        print(f"    日期: {trade.trade_date} | 类型: {trade.trade_type}")
        print(f"    价格: ¥{trade.price} | 数量: {trade.quantity}股")
        if trade.reason:
            print(f"    当时理由: {trade.reason}")

        notes = _input("\n  复盘笔记（必填）", allow_empty=False)
        score = _input_int("  自我评分（1-5：大错 → 优秀）")

        if score < 1 or score > 5:
            print("  ❌ 评分需在 1-5 之间。")
            return

        self.repo.update_review(trade.id, notes, score)
        print(f"  ✅ 复盘已保存！")

    # ---- 6. 盈亏汇总 ----

    def _pnl_summary(self):
        print("\n  —— 盈亏汇总 ——")

        market = _select(["全部", "A股", "美股"], "选择市场")
        market = None if market == "全部" else market

        pnl_list = self.repo.get_all_pnl(market=market)

        if not pnl_list:
            print("  📭 还没有已完成的交易（已配对买卖）。")
            return

        # 整体统计
        total_pnl = sum(p["net_pnl"] for p in pnl_list)
        wins = [p for p in pnl_list if p["net_pnl"] > 0]
        losses = [p for p in pnl_list if p["net_pnl"] <= 0]
        win_rate = len(wins) / len(pnl_list) * 100 if pnl_list else 0

        print(f"\n  📊 整体统计（{len(pnl_list)} 笔已完成交易）：")
        print(f"     总盈亏: ¥{total_pnl:+,.2f}")
        print(f"     胜率: {win_rate:.1f}%（{len(wins)}赢 / {len(losses)}亏）")
        if wins:
            print(f"     平均盈利: ¥{sum(p['net_pnl'] for p in wins) / len(wins):,.2f}")
        if losses:
            print(f"     平均亏损: ¥{sum(p['net_pnl'] for p in losses) / len(losses):,.2f}")

        # 按市场
        for mkt in ["A股", "美股"]:
            mkt_trades = [p for p in pnl_list if p["market"] == mkt]
            if mkt_trades:
                mkt_pnl = sum(p["net_pnl"] for p in mkt_trades)
                mkt_wins = len([p for p in mkt_trades if p["net_pnl"] > 0])
                print(f"\n    {mkt}: ¥{mkt_pnl:+,.2f} | "
                      f"胜率 {mkt_wins / len(mkt_trades) * 100:.1f}% | "
                      f"{len(mkt_trades)}笔")

    # ---- 7. 导出 CSV ----

    def _export_csv(self):
        default_path = os.path.join(r"D:\trading_data", "trades_export.csv")
        filepath = _input("导出路径", default=os.path.abspath(default_path))
        self.repo.export_csv(filepath)
        print(f"  ✅ 已导出到: {filepath}")

    # ---- 8. 导入 CSV ----

    def _import_csv(self):
        filepath = _input("CSV 文件路径", allow_empty=False)
        if not os.path.exists(filepath):
            print(f"  ❌ 文件不存在: {filepath}")
            return
        count = self.repo.import_csv(filepath)
        print(f"  ✅ 已导入 {count} 条记录。")

    # ---- 工具 ----

    def _print_trade_table(self, trades: list):
        """格式化打印交易列表"""
        print(f"\n  📋 共 {len(trades)} 条记录：\n")
        header = f"  {'ID':<5} {'日期':<12} {'市场':<5} {'代码':<10} {'名称':<8} {'类型':<4} {'价格':>8} {'数量':>6} {'理由':<20} {'评分':<4}"
        print(header)
        print("  " + "-" * (len(header) - 2))
        for t in trades:
            reason_short = t.reason[:18] + ".." if len(t.reason) > 20 else t.reason
            score_str = f"{t.review_score}⭐" if t.review_score > 0 else "-"
            print(f"  {t.id:<5} {t.trade_date:<12} {t.market:<5} {t.symbol:<10} "
                  f"{t.name:<8} {t.trade_type:<4} {t.price:>8.2f} {t.quantity:>6} "
                  f"{reason_short:<20} {score_str:<4}")


# ============================================================
# 入口
# ============================================================

def run_journal(db_path: str = None):
    """启动交易日志 CLI"""
    cli = JournalCLI(db_path)
    cli.menu()


if __name__ == "__main__":
    run_journal()
