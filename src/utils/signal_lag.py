# -*- coding: utf-8 -*-
"""
Signal Lag Shim — 信号延迟垫片

将因子/策略生成的原始信号整体下移一行，模拟 Next-Bar 成交 (T日信号 → T+1日执行)。
与 BacktestEngine._run_next_bar() 配合使用，形成双重保障。

集成方式:
    from src.utils.signal_lag import apply_signal_lag
    lagged = apply_signal_lag(signal_df, lag_periods=1)

为什么需要这个垫片:
    - 回测引擎的 _run_next_bar() 已经实现了 T+1 成交
    - 但外部信号 (如批量因子信号、AI 信号) 在传入引擎前没有这个保护
    - 本垫片在数据进入引擎前做一次统一的延迟，消除"同 Bar 成交"偏差
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict
import logging

logger = logging.getLogger("utils.signal_lag")


def apply_signal_lag(
    signal_df: pd.DataFrame,
    lag_periods: int = 1,
    drop_na: bool = True,
    inplace: bool = False,
) -> pd.DataFrame:
    """
    将信号向后延迟 N 个周期，消除"同 Bar 成交"偏差。

    Args:
        signal_df:   信号 DataFrame，索引为 DatetimeIndex，列为股票代码
        lag_periods: 延迟周期数，默认 1 (T+1 成交)
        drop_na:     是否删除前 N 行 (因延迟产生的 NaN)，默认 True
        inplace:     是否原地修改，默认 False

    Returns:
        延迟后的信号 DataFrame

    Raises:
        TypeError: 索引不是 DatetimeIndex
    """
    if signal_df.empty:
        return signal_df

    if not isinstance(signal_df.index, pd.DatetimeIndex):
        raise TypeError(
            f"信号索引必须是 DatetimeIndex，当前类型: {type(signal_df.index).__name__}。"
            f"请先执行 signal_df.index = pd.to_datetime(signal_df.index)"
        )

    if lag_periods <= 0:
        logger.warning("lag_periods <= 0，不做延迟处理")
        return signal_df

    logger.info(
        f"信号延迟: {lag_periods} 周期, "
        f"shape={signal_df.shape}, "
        f"日期范围: {signal_df.index[0]} → {signal_df.index[-1]}"
    )

    if inplace:
        signal_df.iloc[:, :] = signal_df.shift(lag_periods).values
        if drop_na:
            signal_df.dropna(how="all", inplace=True)
        return signal_df

    lagged = signal_df.shift(lag_periods)
    if drop_na:
        lagged.dropna(how="all", inplace=True)
    return lagged


def validate_signal_integrity(
    original: pd.DataFrame, lagged: pd.DataFrame
) -> Dict:
    """
    验证延迟前后的信号一致性 (审计用)。

    Returns:
        {
            "original_signals_count": int,
            "lagged_signals_count": int,
            "first_signal_date_original": str,
            "first_signal_date_lagged": str,
            "is_strictly_lagged": bool,
            "rows_dropped": int,
        }
    """
    orig_dates = original.dropna(how="all").index
    lag_dates = lagged.dropna(how="all").index

    rows_dropped = len(original) - len(lagged)

    result = {
        "original_signals_count": len(orig_dates),
        "lagged_signals_count": len(lag_dates),
        "first_signal_date_original": (
            str(orig_dates[0])[:10] if len(orig_dates) > 0 else None
        ),
        "first_signal_date_lagged": (
            str(lag_dates[0])[:10] if len(lag_dates) > 0 else None
        ),
        "is_strictly_lagged": False,
        "rows_dropped": rows_dropped,
    }

    # 校验: 延迟后第一个信号日期应 > 原始第一个信号日期
    if len(orig_dates) > 0 and len(lag_dates) > 0:
        if orig_dates[0] < lag_dates[0]:
            result["is_strictly_lagged"] = True

    status = "PASS" if result["is_strictly_lagged"] else "WARN"
    logger.info(
        f"[审计] {status}: 原始{result['original_signals_count']}信号 → "
        f"延迟后{result['lagged_signals_count']}信号, "
        f"延迟{'生效' if result['is_strictly_lagged'] else '未生效或数据不足'}"
    )

    return result


# ═══════════════════════════════════════════
# 对接回测引擎的便捷函数
# ═══════════════════════════════════════════

def prepare_signals_for_backtest(
    signal_df: pd.DataFrame,
    lag_periods: int = 1,
    validate: bool = True,
) -> pd.DataFrame:
    """
    准备信号用于回测: 延迟 + 校验。

    这是对接 BacktestEngine 的推荐入口。
    如果引擎已使用 _run_next_bar() 模式, lag_periods 应设为 0 (避免双重延迟)。

    Args:
        signal_df:   原始信号 DataFrame
        lag_periods: 延迟周期 (引擎用 next_open=0, same_close=1)
        validate:    是否执行审计校验

    Returns:
        处理后的信号 DataFrame
    """
    if lag_periods > 0:
        lagged = apply_signal_lag(signal_df, lag_periods=lag_periods)
    else:
        lagged = signal_df.copy()

    if validate:
        validate_signal_integrity(signal_df, lagged)

    return lagged


# ============ 测试 ============
if __name__ == "__main__":
    dates = pd.date_range("2024-01-01", periods=5, freq="D")
    mock = pd.DataFrame({
        "000001.SZ": [1.0, -1.0, 0.0, 0.5, 0.0],
        "600519.SH": [0.0, 0.0, 1.0, 0.0, -0.5],
    }, index=dates)

    print("===== 原始信号 =====")
    print(mock)

    lagged = apply_signal_lag(mock, lag_periods=1)
    print("\n===== 延迟后 (T+1 成交) =====")
    print(lagged)

    audit = validate_signal_integrity(mock, lagged)
    print("\n===== 审计结果 =====")
    for k, v in audit.items():
        print(f"  {k}: {v}")
