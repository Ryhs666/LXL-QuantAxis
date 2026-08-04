"""
量能耗尽反转因子 (Volume Exhaustion Reversal Factor)

A股日频量价因子。捕捉"放量 + 动量衰减 + 日内反转"三联信号，
预示趋势能量耗尽，后续将出现回调。

方向: 空头因子 (因子值越高 → 预期收益越低)
换手: 中频 (3-5天持仓周期)

构建逻辑:
  1. 成交量异常度 (volume_zscore): 当日量 / 20日均量 → z-score
  2. 动量衰减度 (momentum_decay): 5日动量 - 10日动量, 衰减信号
  3. 日内反转度 (intraday_fade): 收盘位置偏离趋势方向, 盘中反转确认

参考: 基于 A 股散户主导市场的微观结构特征设计
"""

import pandas as pd
import numpy as np
from typing import Tuple, Optional


def compute_volume_exhaustion_factor(
    df: pd.DataFrame,
    vol_lookback: int = 20,
    momentum_short: int = 5,
    momentum_long: int = 10,
    winsorize_pct: float = 0.01,
) -> pd.DataFrame:
    """
    计算量能耗尽反转因子。

    参数:
        df: 单只股票的 OHLCV DataFrame
            必须包含: open, high, low, close, volume
            按 date 升序排列
        vol_lookback:     成交量回顾窗口 (默认20日)
        momentum_short:   短期动量窗口 (默认5日)
        momentum_long:    长期动量窗口 (默认10日)
        winsorize_pct:    去极值比例 (默认1%)

    返回:
        DataFrame, 新增列:
          - volume_zscore:        成交量异常度 (子因子1)
          - momentum_decay:       动量衰减度 (子因子2)
          - intraday_fade:        日内反转度 (子因子3)
          - vol_exhaustion_raw:   原始合成因子
          - vol_exhaustion_zscore: 标准化后因子 (最终输出)
    """

    # ================================================================
    # 0. 数据校验
    # ================================================================
    required_cols = ["open", "high", "low", "close", "volume"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"缺少必需列: {missing}")

    df = df.copy().sort_values("date" if "date" in df.columns else df.index)
    min_bars = max(vol_lookback, momentum_long) + 5
    if len(df) < min_bars:
        raise ValueError(f"数据量不足: 需要至少 {min_bars} 条, 当前 {len(df)}")

    # 避免除零
    close = df["close"].astype(float)
    volume = df["volume"].astype(float)
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    open_ = df["open"].astype(float)

    # ================================================================
    # 1. 子因子一: 成交量异常度 (Volume Z-Score)
    #
    # 逻辑: 当日成交量 / 过去N日成交量中位数 → z-score 标准化
    # 为什么用中位数不用均值: 成交量分布右偏严重, 中位数更稳健
    # 为什么是空头信号: A股放量往往 = 散户追入高峰 → 后续买方枯竭
    # ================================================================
    vol_median = volume.rolling(window=vol_lookback, min_periods=10).median()
    vol_mad = (
        (volume - vol_median).abs()
        .rolling(window=vol_lookback, min_periods=10)
        .median()
    )

    # 成交量相对偏离 (用 MAD 标准化比 std 更抗异常值)
    vol_deviation = (volume - vol_median) / vol_mad.replace(0, np.nan)

    # ================================================================
    # 2. 子因子二: 动量衰减度 (Momentum Decay)
    #
    # 逻辑: 短期动量 - 长期动量, 负值 = 动量在衰减
    # 计算方法: (close_t / close_{t-short}) - (close_t / close_{t-long})
    # 解读: 如果短期涨幅开始小于长期涨幅, 说明边际买盘在减弱
    #       如果短期跌幅开始小于长期跌幅, 说明边际卖盘在减弱 (但空头因子只关注前者)
    # ================================================================
    ret_short = close / close.shift(momentum_short) - 1
    ret_long = close / close.shift(momentum_long) - 1

    # 动量衰减: 正值 → 短期动量强于长期 (趋势加速)
    #          负值 → 短期动量弱于长期 (趋势衰竭) → 空头信号
    momentum_decay_raw = ret_short - ret_long

    # 只对上涨趋势中的衰减感兴趣 (下跌趋势中的衰减是另一个故事)
    # 加入方向性调节: 如果长期趋势是上涨的, 衰减信号更重要
    trend_direction = np.sign(ret_long)  # +1 上涨, -1 下跌

    # 上涨趋势中的衰减 (动量减速) → 强烈空头信号
    # 下跌趋势中的衰减 → 空头信号较弱 (已经是下跌了, 再做空意义不大)
    momentum_decay = np.where(
        trend_direction > 0,
        -momentum_decay_raw,   # 上涨趋势: 衰减越严重, 信号越强 (取反使正值=空头)
        momentum_decay_raw * 0.3,  # 下跌趋势: 衰减信号打折
    )

    # ================================================================
    # 3. 子因子三: 日内反转度 (Intraday Fade)
    #
    # 逻辑: (收盘 - 开盘) / (最高 - 最低) 衡量收盘在日内区间的位置
    # 如果当日整体上涨 (close > open) 但收盘远低于最高点:
    #   → 盘中冲高回落 → 聪明钱在高位出货 → 空头信号
    # 如果当日整体下跌 (close < open) 但收盘远高于最低点:
    #   → 盘中探底回升 → 有资金在低位接盘 → 对空头因子贡献为负(不做空)
    # ================================================================
    daily_range = high - low
    close_position = np.where(
        daily_range > 0,
        (close - open_) / daily_range,
        0.0  # 一字板无日内区间
    )

    # 日内反转信号:
    # 上涨日 (close > open): close_position 越低 → 冲高回落越严重 → 空头信号
    #                         取值范围 [-1, +1], 越低越空
    # 下跌日 (close < open): close_position 越高 → 探底回升 → 不做空
    # 用符号函数区分涨跌日
    is_up_day = (close > open_).astype(float)

    # 上涨日的反转度: 1 - close_position (0~2, 越接近2越空)
    # 下跌日的反转度: 设为 ~0 (下跌日不贡献空头信号)
    intraday_fade = np.where(
        is_up_day > 0,
        1.0 - close_position,   # 上涨日: 收盘位置越低 → 反转越强
        np.maximum(0, close_position) * 0.2,  # 下跌日: 弱信号
    )

    # ================================================================
    # 4. 子因子去极值 (Winsorize)
    #
    # 对每个子因子做截面或时序 winsorize, 避免极端值主导合成结果
    # 这里做时序 winsorize (基于自身历史分布)
    # ================================================================
    def winsorize_series(s: pd.Series, pct: float) -> pd.Series:
        """时序 winsorize: 基于自身历史的上下分位数截尾"""
        if len(s.dropna()) < 20:
            return s
        lower = s.rolling(window=60, min_periods=20).quantile(pct)
        upper = s.rolling(window=60, min_periods=20).quantile(1 - pct)
        result = s.clip(lower=lower, upper=upper, axis=0)
        return result

    vol_deviation_w = winsorize_series(vol_deviation, winsorize_pct)
    momentum_decay_w = winsorize_series(
        pd.Series(momentum_decay, index=df.index), winsorize_pct
    )
    intraday_fade_w = winsorize_series(
        pd.Series(intraday_fade, index=df.index), winsorize_pct
    )

    # ================================================================
    # 5. 子因子标准化 (Z-Score)
    #
    # 每个子因子做滚动 z-score, 消除量纲差异
    # ================================================================
    def rolling_zscore(s: pd.Series, window: int = 60) -> pd.Series:
        """滚动 z-score 标准化"""
        rolling_mean = s.rolling(window=window, min_periods=20).mean()
        rolling_std = s.rolling(window=window, min_periods=20).std()
        rolling_std = rolling_std.replace(0, np.nan)
        return (s - rolling_mean) / rolling_std

    vol_z = rolling_zscore(vol_deviation_w, window=60)
    mom_z = rolling_zscore(momentum_decay_w, window=60)
    intra_z = rolling_zscore(intraday_fade_w, window=60)

    # ================================================================
    # 6. 合成原始因子
    #
    # 权重逻辑 (基于A股实证经验):
    #   成交量异常: 40% — 放量是最强的反转前兆
    #   动量衰减:   35% — 趋势衰竭是核心逻辑
    #   日内反转:   25% — 盘中确认增加精度
    #
    # 所有三个子因子方向一致: 正值 → 空头信号
    # ================================================================
    raw_factor = (
        0.40 * vol_z.fillna(0) +
        0.35 * mom_z.fillna(0) +
        0.25 * intra_z.fillna(0)
    )

    # ================================================================
    # 7. 最终标准化
    #
    # 合成后做一次截面或时序 z-score, 得到最终因子值
    # 正值: 量能耗尽, 预期下跌 (空头)
    # 负值: 量能健康, 无反转信号
    # ================================================================
    final_zscore = rolling_zscore(raw_factor, window=60)

    # ================================================================
    # 8. 组装输出
    # ================================================================
    result = df.copy()
    result["volume_zscore"] = vol_z
    result["momentum_decay"] = pd.Series(momentum_decay_w, index=df.index)
    result["intraday_fade"] = pd.Series(intraday_fade_w, index=df.index)
    result["vol_exhaustion_raw"] = raw_factor
    result["vol_exhaustion_zscore"] = final_zscore

    return result


# ================================================================
# 便捷函数: 跨股票截面标准化版本
# (用于多股票横截面选股, 每日做截面 z-score)
# ================================================================

def compute_cross_sectional(
    panel: pd.DataFrame,
    date_col: str = "date",
    symbol_col: str = "stock_code",
) -> pd.DataFrame:
    """
    多股票横截面版本: 对每只股票计算原始因子, 然后按日做截面标准化。

    参数:
        panel: 多股票面板数据, 必须包含 date, stock_code, OHLCV
        date_col:   日期列名
        symbol_col: 股票代码列名

    返回:
        添加了 'vol_exhaustion_factor' 列的面板数据
    """
    results = []
    for symbol, group in panel.groupby(symbol_col):
        try:
            stock_result = compute_volume_exhaustion_factor(group)
            stock_result[symbol_col] = symbol
            results.append(stock_result)
        except ValueError:
            continue

    if not results:
        return panel

    combined = pd.concat(results, ignore_index=True)

    # 截面标准化: 每日对所有股票的 raw factor 做 z-score
    combined["vol_exhaustion_factor"] = combined.groupby(
        date_col
    )["vol_exhaustion_raw"].transform(
        lambda x: (x - x.mean()) / x.std() if x.std() > 0 else 0.0
    )

    # 截面去极值: ±3 倍标准差截尾
    combined["vol_exhaustion_factor"] = combined["vol_exhaustion_factor"].clip(
        lower=-3.0, upper=3.0
    )

    return combined


# ================================================================
# 因子元数据 (注册到 FACTOR_REGISTRY 使用)
# ================================================================

FACTOR_META = {
    "name": "vol_exhaustion",
    "chinese_name": "量能耗尽反转因子",
    "category": "volume",
    "direction": "short",       # 空头因子
    "turnover_freq": "medium",  # 中频换手
    "description": (
        "捕捉'放量+动量衰减+日内反转'三联信号。"
        "成交量异常放大检测散户追入高峰, 动量衰减确认趋势衰竭, "
        "日内收盘位置验证盘中反转。正值 → 预期下跌 (空头)。"
    ),
    "params": {
        "vol_lookback": 20,
        "momentum_short": 5,
        "momentum_long": 10,
        "winsorize_pct": 0.01,
    },
}

# ================================================================
# 注册到项目因子库
# ================================================================

def register():
    """将因子注册到 FACTOR_REGISTRY"""
    try:
        from src.factors.definitions import Factor, FACTOR_REGISTRY

        def calc_factor(data: pd.DataFrame) -> pd.Series:
            """
            FactorCalculator 兼容接口。
            输入 OHLCV DataFrame → 输出因子 Series (0~1 标准化)
            """
            result = compute_volume_exhaustion_factor(data)
            # 将 z-score 映射到 0~1 (sigmoid)
            z = result["vol_exhaustion_zscore"].fillna(0)
            sigmoid = 1.0 / (1.0 + np.exp(-z.clip(-5, 5)))
            return sigmoid

        if "vol_exhaustion" not in FACTOR_REGISTRY:
            FACTOR_REGISTRY["vol_exhaustion"] = Factor(
                name="vol_exhaustion",
                category=FACTOR_META["category"],
                description=FACTOR_META["description"],
                compute=calc_factor,
            )
            print(f"[Factor] 已注册: {FACTOR_META['chinese_name']}")
    except ImportError:
        pass


if __name__ == "__main__":
    # 快速测试
    import sys
    sys.path.insert(0, ".")
    from src.backtest.data_feed import get_data

    data = get_data("600519", "A股", start_date="2024-01-01")
    if data is not None and len(data) > 60:
        result = compute_volume_exhaustion_factor(data)
        latest = result.iloc[-1]
        print(f"\n{FACTOR_META['chinese_name']}")
        print(f"  最新因子值 (z-score): {latest['vol_exhaustion_zscore']:.3f}")
        print(f"  成交量异常度:         {latest['volume_zscore']:.3f}")
        print(f"  动量衰减度:           {latest['momentum_decay']:.3f}")
        print(f"  日内反转度:           {latest['intraday_fade']:.3f}")
        print(f"  方向: {FACTOR_META['direction']} | 换手: {FACTOR_META['turnover_freq']}")

        # 覆盖度统计
        valid = result["vol_exhaustion_zscore"].notna().sum()
        print(f"  有效值: {valid}/{len(result)} ({valid/len(result)*100:.1f}%)")
