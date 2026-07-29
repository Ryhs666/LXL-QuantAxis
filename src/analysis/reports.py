"""
绩效分析报表

从交易数据库中生成：
- 按市场/策略/时间段的盈亏汇总
- 胜率、盈亏比统计
- 持仓天数分析
- 标签（tags）盈亏分布
"""

import sys
import os
from collections import defaultdict
from typing import Optional, List

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.models.trade import TradeRepository


class ReportGenerator:
    """分析报表生成器"""

    def __init__(self, db_path: str = None):
        self.repo = TradeRepository(db_path)

    # ---- 整体概览 ----

    def overview(self, market: str = None) -> dict:
        """整体交易概况"""
        pnl_list = self.repo.get_all_pnl(market=market)
        total = self.repo.count()
        buys = self.repo.count(trade_type="买入")
        sells = self.repo.count(trade_type="卖出")

        if not pnl_list:
            return {
                "总记录数": total,
                "买入记录": buys,
                "卖出记录": sells,
                "已完成交易": 0,
                "胜率": "N/A",
                "总盈亏": "N/A",
            }

        wins = [p for p in pnl_list if p["net_pnl"] > 0]
        losses = [p for p in pnl_list if p["net_pnl"] <= 0]
        total_pnl = sum(p["net_pnl"] for p in pnl_list)

        return {
            "总记录数": total,
            "买入记录": buys,
            "卖出记录": sells,
            "已完成交易": len(pnl_list),
            "盈利笔数": len(wins),
            "亏损笔数": len(losses),
            "胜率": f"{len(wins) / len(pnl_list) * 100:.1f}%",
            "总盈亏": f"¥{total_pnl:+,.2f}",
            "平均每笔盈亏": f"¥{total_pnl / len(pnl_list):+,.2f}",
            "最佳单笔": f"¥{max(p['net_pnl'] for p in pnl_list):+,.2f}",
            "最差单笔": f"¥{min(p['net_pnl'] for p in pnl_list):+,.2f}",
        }

    # ---- 按市场分组 ----

    def by_market(self) -> dict:
        """按市场分组统计"""
        result = {}
        for market in ["A股", "美股"]:
            pnl_list = self.repo.get_all_pnl(market=market)
            if not pnl_list:
                result[market] = {"交易数": 0, "总盈亏": "¥0"}
                continue
            wins = [p for p in pnl_list if p["net_pnl"] > 0]
            total_pnl = sum(p["net_pnl"] for p in pnl_list)
            result[market] = {
                "交易数": len(pnl_list),
                "胜率": f"{len(wins) / len(pnl_list) * 100:.1f}%",
                "总盈亏": f"¥{total_pnl:+,.2f}",
                "平均盈亏": f"¥{total_pnl / len(pnl_list):+,.2f}",
            }
        return result

    # ---- 按策略分组 ----

    def by_strategy(self) -> dict:
        """按策略分组统计"""
        pnl_list = self.repo.get_all_pnl()
        all_trades = self.repo.find_all(limit=10000)

        # 建立 buy_id -> strategy_name 的映射
        strategy_map = {}
        for t in all_trades:
            if t.strategy_name:
                strategy_map[t.id] = t.strategy_name

        groups = defaultdict(list)
        for p in pnl_list:
            strategy = strategy_map.get(p["buy_id"], "未分类")
            groups[strategy].append(p)

        result = {}
        for strategy, trades in sorted(groups.items()):
            wins = [t for t in trades if t["net_pnl"] > 0]
            total_pnl = sum(t["net_pnl"] for t in trades)
            result[strategy] = {
                "交易数": len(trades),
                "胜率": f"{len(wins) / len(trades) * 100:.1f}%",
                "总盈亏": f"¥{total_pnl:+,.2f}",
            }
        return result

    # ---- 按标签分组 ----

    def by_tags(self) -> dict:
        """按标签统计盈亏分布（找出哪些标签赚钱/亏钱）"""
        pnl_list = self.repo.get_all_pnl()
        all_trades = self.repo.find_all(limit=10000)

        tag_map = {}
        for t in all_trades:
            if t.tags:
                tag_map[t.id] = t.tags

        tag_stats = defaultdict(lambda: {"count": 0, "pnl": 0.0, "wins": 0})

        for p in pnl_list:
            tags_str = tag_map.get(p["buy_id"], "")
            if not tags_str:
                continue
            for tag in tags_str.split(","):
                tag = tag.strip()
                if tag:
                    tag_stats[tag]["count"] += 1
                    tag_stats[tag]["pnl"] += p["net_pnl"]
                    if p["net_pnl"] > 0:
                        tag_stats[tag]["wins"] += 1

        # 按总盈亏排序
        result = {}
        for tag, stats in sorted(tag_stats.items(),
                                  key=lambda x: x[1]["pnl"], reverse=True):
            result[tag] = {
                "次数": stats["count"],
                "胜率": f"{stats['wins'] / stats['count'] * 100:.1f}%",
                "总盈亏": f"¥{stats['pnl']:+,.2f}",
            }
        return result

    # ---- 月度汇总 ----

    def by_month(self) -> dict:
        """按月汇总盈亏"""
        pnl_list = self.repo.get_all_pnl()
        monthly = defaultdict(lambda: {"count": 0, "pnl": 0.0, "wins": 0})

        for p in pnl_list:
            month = p["sell_date"][:7]  # YYYY-MM
            monthly[month]["count"] += 1
            monthly[month]["pnl"] += p["net_pnl"]
            if p["net_pnl"] > 0:
                monthly[month]["wins"] += 1

        result = {}
        for month in sorted(monthly.keys()):
            m = monthly[month]
            result[month] = {
                "交易数": m["count"],
                "胜率": f"{m['wins'] / m['count'] * 100:.1f}%",
                "月盈亏": f"¥{m['pnl']:+,.2f}",
            }
        return result

    # ---- 文本报表 ----

    def print_all(self, market: str = None):
        """打印完整分析报告"""
        print("\n" + "=" * 60)
        print("  📊 交易绩效分析报告")
        print("=" * 60)

        # 概览
        overview = self.overview(market)
        print("\n  【整体概览】")
        for k, v in overview.items():
            print(f"    {k}: {v}")

        # 按市场
        print("\n  【按市场分组】")
        for market, stats in self.by_market().items():
            print(f"    {market}:")
            for k, v in stats.items():
                print(f"      {k}: {v}")

        # 按策略
        by_strat = self.by_strategy()
        if by_strat:
            print("\n  【按策略分组】")
            for strategy, stats in by_strat.items():
                print(f"    {strategy}:")
                for k, v in stats.items():
                    print(f"      {k}: {v}")

        # 月度
        by_month = self.by_month()
        if by_month:
            print("\n  【月度收益】")
            for month, stats in by_month.items():
                print(f"    {month}: {stats['月盈亏']} ({stats['交易数']}笔, 胜率{stats['胜率']})")

        # 标签
        by_tag = self.by_tags()
        if by_tag:
            print("\n  【标签分析】（按盈亏排序）")
            for tag, stats in list(by_tag.items())[:10]:
                print(f"    [{tag}]: {stats['总盈亏']} ({stats['次数']}次, 胜率{stats['胜率']})")

        print("\n" + "=" * 60)


def run_report(db_path: str = None):
    """快捷入口：生成并打印报告"""
    gen = ReportGenerator(db_path)
    gen.print_all()


if __name__ == "__main__":
    run_report()
