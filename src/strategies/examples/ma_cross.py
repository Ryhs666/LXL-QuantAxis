"""
示例策略：双均线交叉

- 买入信号：短期均线上穿长期均线（金叉）
- 卖出信号：短期均线下穿长期均线（死叉）
- 配合成交量放大确认

用于验证整个回测链路是否跑通。
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

import pandas as pd
from typing import Optional
from src.strategies.base import BaseStrategy
from src.models.strategy import Signal, StrategyConfig


class MACrossStrategy(BaseStrategy):
    """
    双均线交叉策略

    参数:
        fast_period: 短期均线周期（默认 5）
        slow_period: 长期均线周期（默认 20）
        vol_confirm: 是否需要成交量放大确认（默认 True）
        vol_ratio: 成交量放大倍数（相对 20 日均量，默认 1.5 倍）
    """

    def __init__(self,
                 fast_period: int = 5,
                 slow_period: int = 20,
                 vol_confirm: bool = True,
                 vol_ratio: float = 1.5,
                 config: StrategyConfig = None):
        super().__init__(config)
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.vol_confirm = vol_confirm
        self.vol_ratio = vol_ratio

    def on_bar(self, i: int, data: pd.DataFrame,
               portfolio) -> Optional[Signal]:
        """每根 K 线的判断逻辑"""
        if i < self.slow_period + 1:
            return None  # 数据不足

        symbol = self.config.name or "STOCK"
        current_price = data["close"].iloc[-1]
        date = str(data.iloc[-1].get("date", ""))[:10]

        # 检查是否持有
        has_position = symbol in portfolio.positions

        if not has_position and self.buy_signal(data):
            return Signal(
                action="BUY",
                symbol=symbol,
                date=date,
                price=current_price,
                reason=f"金叉: MA{self.fast_period} 上穿 MA{self.slow_period}",
            )

        if has_position and self.sell_signal(data):
            return Signal(
                action="SELL",
                symbol=symbol,
                date=date,
                price=current_price,
                reason=f"死叉: MA{self.fast_period} 下穿 MA{self.slow_period}",
            )

        return None

    def buy_signal(self, data: pd.DataFrame) -> bool:
        """买入条件：短期均线上穿长期均线 + 成交量放大"""
        fast_ma = self.sma(data, self.fast_period)
        slow_ma = self.sma(data, self.slow_period)

        golden_cross = self.cross_above(fast_ma, slow_ma)

        if not golden_cross:
            return False

        if self.vol_confirm:
            vol_ma = self.volume_sma(data, 20)
            if len(vol_ma) < 2:
                return False
            current_vol = data["volume"].iloc[-1]
            avg_vol = vol_ma.iloc[-1]
            if current_vol < avg_vol * self.vol_ratio:
                return False

        return True

    def sell_signal(self, data: pd.DataFrame) -> bool:
        """卖出条件：短期均线下穿长期均线"""
        fast_ma = self.sma(data, self.fast_period)
        slow_ma = self.sma(data, self.slow_period)

        return self.cross_below(fast_ma, slow_ma)


# ============================================================
# 快捷测试入口
# ============================================================

def run_example():
    """运行示例回测"""
    from src.backtest.data_feed import get_data
    from src.backtest.engine import BacktestEngine

    print("=" * 60)
    print("  示例策略：双均线交叉回测")
    print("=" * 60)

    # 获取数据
    print("\n  获取行情数据...")
    try:
        # 先试美股 AAPL
        data = get_data("AAPL", "美股", start_date="2023-01-01")
        symbol = "AAPL"
    except Exception:
        try:
            # 再试 A 股贵州茅台
            data = get_data("600519", "A股", start_date="2023-01-01")
            symbol = "600519"
        except Exception as e:
            print(f"  ❌ 获取行情失败: {e}")
            print("  提示：请检查网络连接，或手动运行回测。")
            return

    print(f"  ✅ 获取到 {symbol} 共 {len(data)} 条日线数据")
    print(f"     时间范围: {data['date'].iloc[0]} ~ {data['date'].iloc[-1]}")

    # 配置策略
    config = StrategyConfig(
        name=symbol,
        initial_capital=100_000,
        position_size_pct=0.3,
    )
    strategy = MACrossStrategy(
        fast_period=5,
        slow_period=20,
        vol_confirm=True,
        vol_ratio=1.5,
        config=config,
    )

    # 运行回测
    print("\n  运行回测...")
    engine = BacktestEngine(
        initial_capital=config.initial_capital,
        commission_rate=config.commission_rate,
    )
    result = engine.run(strategy, data, position_size_pct=config.position_size_pct)

    # 输出结果
    metrics = result["metrics"]
    print("\n  📊 回测结果：")
    for k, v in metrics.items():
        print(f"    {k}: {v}")

    # 生成图表
    print("\n  生成图表...")
    try:
        from src.analysis.charts import plot_from_backtest
        output_dir = r"D:\trading_data\charts"
        plot_from_backtest(result, save_dir=os.path.join(output_dir, "backtest_output"))
    except Exception as e:
        print(f"  ⚠️ 图表生成失败: {e}")

    return result


if __name__ == "__main__":
    run_example()
