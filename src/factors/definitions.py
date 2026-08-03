"""
因子定义 — 你的独有因子库

每个因子是一个可复用的计算单元，输出 0~1 标准化的信号强度。

因子分类:
  - trend    趋势类: 均线、方向、斜率
  - momentum 动量类: RSI、MACD、ROC
  - volatility 波动类: ATR、布林宽度、HV
  - volume   成交量类: 放量、缩量、OBV
  - pattern  形态类: 锤子线、吞没、十字星
  - composite 复合类: 多因子加权组合
"""

from dataclasses import dataclass, field
from typing import Optional, Callable
import pandas as pd
import numpy as np


# ============================================================
# 因子元数据
# ============================================================

@dataclass
class Factor:
    """一个因子"""
    name: str                          # 因子名称
    category: str                      # 分类: trend/momentum/volatility/volume/pattern/composite
    description: str                   # 一句话描述
    params: dict = field(default_factory=dict)  # 默认参数
    compute: Optional[Callable] = None  # 计算函数

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "params": self.params,
        }


# ============================================================
# 因子计算器
# ============================================================

class FactorCalculator:
    """因子计算引擎 — 输入 OHLCV，输出因子值 DataFrame (v6.7: EWMA时间衰减)"""

    def __init__(self, data: pd.DataFrame, halflife: int = 20, use_ewma: bool = True):
        """
        data:      OHLCV DataFrame (date, open, high, low, close, volume)
        halflife:  EWMA 半衰期(交易日), 默认20天
        use_ewma:  是否使用时间衰减加权
        """
        self.data = data.copy()
        self.halflife = halflife
        self.use_ewma = use_ewma
        self._cache = {}
        self._decay_status = {}  # 因子衰退状态

    # ---- 基础计算 ----

    def sma(self, col: str = "close", period: int = 20) -> pd.Series:
        return self.data[col].rolling(period).mean()

    def ema(self, col: str = "close", period: int = 20) -> pd.Series:
        return self.data[col].ewm(span=period, adjust=False).mean()

    def std(self, col: str = "close", period: int = 20) -> pd.Series:
        return self.data[col].rolling(period).std()

    def highest(self, col: str = "high", period: int = 20) -> pd.Series:
        return self.data[col].rolling(period).max()

    def lowest(self, col: str = "low", period: int = 20) -> pd.Series:
        return self.data[col].rolling(period).min()

    # ---- EWMA 时间衰减 (v6.7) ----

    def ewma(self, col: str = "close", halflife: int = None) -> pd.Series:
        """指数加权移动平均"""
        hl = halflife or self.halflife
        span = hl * 2  # span ≈ 2 * halflife
        return self.data[col].ewm(span=span, adjust=False).mean()

    def ewma_std(self, col: str = "close", halflife: int = None) -> pd.Series:
        """指数加权标准差"""
        hl = halflife or self.halflife
        span = hl * 2
        ewm_mean = self.data[col].ewm(span=span, adjust=False).mean()
        ewm_var = ((self.data[col] - ewm_mean) ** 2).ewm(span=span, adjust=False).mean()
        return np.sqrt(ewm_var)

    def _normalize(self, series: pd.Series, method: str = "zscore",
                   period: int = 252) -> pd.Series:
        """标准化到 ~0-1 范围 (v6.7: 支持EWMA)"""
        if method == "zscore":
            mean = series.rolling(period).mean()
            std = series.rolling(period).std()
            z = (series - mean) / std.replace(0, np.nan)
            # 映射到 0-1 via sigmoid
            return 1 / (1 + np.exp(-z))
        elif method == "minmax":
            high = series.rolling(period).max()
            low = series.rolling(period).min()
            rng = (high - low).replace(0, np.nan)
            return (series - low) / rng
        elif method == "rank":
            return series.rolling(period).rank(pct=True)
        return series

    # ============================================================
    # 趋势类因子
    # ============================================================

    def f_ma_deviation(self, period: int = 20) -> pd.Series:
        """价格偏离均线程度。>0.5=多方, <0.5=空方"""
        ma = self.sma("close", period)
        pct = (self.data["close"] - ma) / ma * 100
        return 1 / (1 + np.exp(-pct))  # sigmoid

    def f_ma_alignment(self, short: int = 5, mid: int = 20, long: int = 60) -> pd.Series:
        """均线排列。1=多头排列(短>中>长), 0=空头排列"""
        ma_s = self.sma("close", short)
        ma_m = self.sma("close", mid)
        ma_l = self.sma("close", long)
        bullish = (ma_s > ma_m) & (ma_m > ma_l)
        bearish = (ma_s < ma_m) & (ma_m < ma_l)
        score = bullish.astype(float) * 1.0 + (~bullish & ~bearish).astype(float) * 0.5
        return score

    def f_ma_slope(self, period: int = 20, lookback: int = 5) -> pd.Series:
        """均线斜率。正斜率=上升趋势, 值高=陡峭"""
        ma = self.sma("close", period)
        slope = (ma - ma.shift(lookback)) / ma.shift(lookback) * 100
        return 1 / (1 + np.exp(-slope * 5))

    def f_adx_like(self, period: int = 14) -> pd.Series:
        """简易趋势强度（类似 ADX）。1=强趋势, 0=弱趋势"""
        high, low, close = self.data["high"], self.data["low"], self.data["close"]
        tr = pd.concat([
            high - low,
            abs(high - close.shift(1)),
            abs(low - close.shift(1))
        ], axis=1).max(axis=1)

        up = high - high.shift(1)
        down = low.shift(1) - low
        plus_dm = pd.Series(np.where((up > down) & (up > 0), up, 0), index=self.data.index)
        minus_dm = pd.Series(np.where((down > up) & (down > 0), down, 0), index=self.data.index)

        atr = tr.ewm(alpha=1 / period, adjust=False).mean()
        plus_di = 100 * plus_dm.ewm(alpha=1 / period, adjust=False).mean() / atr.replace(0, np.nan)
        minus_di = 100 * minus_dm.ewm(alpha=1 / period, adjust=False).mean() / atr.replace(0, np.nan)

        dx = abs(plus_di - minus_di) / (plus_di + minus_di).replace(0, np.nan) * 100
        return dx.ewm(alpha=1 / period, adjust=False).mean() / 100

    # ============================================================
    # 动量类因子
    # ============================================================

    def f_rsi(self, period: int = 14) -> pd.Series:
        """RSI 标准化到 0~1。0=超卖, 1=超买"""
        delta = self.data["close"].diff()
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta).where(delta < 0, 0.0)
        avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        return (100 - (100 / (1 + rs))) / 100

    def f_macd_hist(self, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.Series:
        """MACD 柱状图。正=动能向上, 负=动能向下 (标准化的)"""
        ema_f = self.ema("close", fast)
        ema_s = self.ema("close", slow)
        dif = ema_f - ema_s
        dea = dif.ewm(span=signal, adjust=False).mean()
        hist = 2 * (dif - dea)
        return 1 / (1 + np.exp(-hist * 10 / self.data["close"].rolling(100).mean()))

    def f_roc(self, period: int = 10) -> pd.Series:
        """价格变化率 (Rate of Change)。>0=上涨, <0=下跌"""
        roc = (self.data["close"] / self.data["close"].shift(period) - 1) * 100
        return 1 / (1 + np.exp(-roc))

    def f_price_position(self, period: int = 60) -> pd.Series:
        """当前价格在 N 日范围内的位置。1=顶部, 0=底部"""
        h = self.highest("high", period)
        l = self.lowest("low", period)
        rng = (h - l).replace(0, np.nan)
        pos = (self.data["close"] - l) / rng
        return pos.clip(0, 1)

    def f_momentum_score(self, periods: list = None) -> pd.Series:
        """多周期动量综合评分。看越多个周期都是正收益"""
        if periods is None:
            periods = [5, 10, 20, 60]
        scores = []
        for p in periods:
            ret = self.data["close"].pct_change(p)
            scores.append((ret > 0).astype(float))
        return pd.concat(scores, axis=1).mean(axis=1)

    # ============================================================
    # 波动类因子
    # ============================================================

    def f_volatility(self, period: int = 20) -> pd.Series:
        """历史波动率。高值=波动大, 低值=波动小"""
        returns = self.data["close"].pct_change()
        vol = returns.rolling(period).std() * np.sqrt(252)  # 年化
        # 反转: 低波动 → 高值 (低波动往往健康)
        vol_norm = vol.rolling(252).rank(pct=True)
        return 1 - vol_norm  # 低波动=高分

    def f_bollinger_position(self, period: int = 20, std_dev: float = 2.0) -> pd.Series:
        """价格在布林带中的位置。1=上轨, 0=下轨, 0.5=中轨"""
        ma = self.sma("close", period)
        std = self.std("close", period)
        upper = ma + std_dev * std
        lower = ma - std_dev * std
        rng = (upper - lower).replace(0, np.nan)
        return ((self.data["close"] - lower) / rng).clip(0, 1)

    def f_bollinger_width(self, period: int = 20, std_dev: float = 2.0) -> pd.Series:
        """布林带宽度。窄=盘整, 宽=突破可能"""
        ma = self.sma("close", period)
        std = self.std("close", period)
        width = (2 * std_dev * std) / ma
        return width

    def f_atr_ratio(self, period: int = 14) -> pd.Series:
        """ATR/收盘价比。高值=相对波动大"""
        high, low, close = self.data["high"], self.data["low"], self.data["close"]
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.ewm(alpha=1 / period, adjust=False).mean()
        return atr / close

    # ============================================================
    # 成交量类因子
    # ============================================================

    def f_volume_ratio(self, short: int = 5, long: int = 20) -> pd.Series:
        """量比。>1=放量, <1=缩量"""
        vol_short = self.data["volume"].rolling(short).mean()
        vol_long = self.data["volume"].rolling(long).mean()
        ratio = (vol_short / vol_long.replace(0, np.nan)).fillna(1)
        return 1 / (1 + np.exp(-(ratio - 1) * 3))

    def f_volume_trend(self, period: int = 10) -> pd.Series:
        """量价配合。放量上涨=1, 缩量下跌=0。健康的量价关系"""
        price_up = (self.data["close"].diff() > 0).astype(float)
        vol_up = (self.data["volume"].diff() > 0).astype(float)
        # 价涨量增 or 价跌量缩 = 健康
        healthy = (price_up & vol_up) | ((1 - price_up) & (1 - vol_up))
        return healthy.rolling(period).mean()

    def f_obv_divergence(self, period: int = 20) -> pd.Series:
        """OBV 与价格背离。1=OBV领先价格(看涨), 0=背离"""
        obv = (self.data["volume"] * np.sign(self.data["close"].diff())).cumsum()
        price_ret = self.data["close"].pct_change(period)
        obv_ret = obv.pct_change(period)
        # 同向 = 健康
        same_dir = ((price_ret > 0) & (obv_ret > 0)) | ((price_ret < 0) & (obv_ret < 0))
        return same_dir.rolling(period).mean()

    # ============================================================
    # 形态类因子
    # ============================================================

    def f_hammer(self, lookback: int = 2) -> pd.Series:
        """锤子线检测。1=锤子线(看涨反转信号)"""
        o, h, l, c = self.data["open"], self.data["high"], self.data["low"], self.data["close"]
        body = abs(c - o)
        total_range = h - l
        lower_wick = np.where(c > o, o - l, c - l)

        # 下影线 > 2倍实体, 实体范围较小
        body_ratio = (body / total_range.replace(0, np.nan)).fillna(1)
        wick_ratio = (lower_wick / body.replace(0, np.nan)).fillna(0)

        hammer = (wick_ratio > 2) & (body_ratio < 0.3)
        return hammer.rolling(lookback).max().astype(float)

    def f_engulfing(self) -> pd.Series:
        """吞没形态。1=看涨吞没"""
        o, c = self.data["open"], self.data["close"]
        prev_o, prev_c = o.shift(1), c.shift(1)

        # 前一日阴线 (close < open)
        prev_red = prev_c < prev_o
        # 当日阳线 (close > open)
        today_green = c > o
        # 当日实体 > 前一日实体
        body_bigger = abs(c - o) > abs(prev_c - prev_o)
        # 当日收盘 > 前一日开盘, 当日开盘 < 前一日收盘 (吞没)
        engulf = (c > prev_o) & (o < prev_c)

        return (prev_red & today_green & body_bigger & engulf).rolling(3).max().astype(float)

    # ============================================================
    # 批量计算所有因子
    # ============================================================

    def compute_all(self) -> pd.DataFrame:
        """计算所有因子，返回 DataFrame"""
        factors_df = pd.DataFrame(index=self.data.index)
        factors_df["date"] = self.data["date"] if "date" in self.data.columns else self.data.index

        factor_methods = [
            # (列名, 方法, 分类)
            ("ma_deviation", self.f_ma_deviation, "trend"),
            ("ma_alignment", self.f_ma_alignment, "trend"),
            ("ma_slope", self.f_ma_slope, "trend"),
            ("trend_strength", self.f_adx_like, "trend"),
            ("rsi_norm", self.f_rsi, "momentum"),
            ("macd_hist", self.f_macd_hist, "momentum"),
            ("roc_10", self.f_roc, "momentum"),
            ("price_position", self.f_price_position, "momentum"),
            ("momentum_score", self.f_momentum_score, "momentum"),
            ("volatility", self.f_volatility, "volatility"),
            ("bollinger_pos", self.f_bollinger_position, "volatility"),
            ("bollinger_width", self.f_bollinger_width, "volatility"),
            ("atr_ratio", self.f_atr_ratio, "volatility"),
            ("volume_ratio", self.f_volume_ratio, "volume"),
            ("volume_trend", self.f_volume_trend, "volume"),
            ("obv_divergence", self.f_obv_divergence, "volume"),
            ("hammer", self.f_hammer, "pattern"),
            ("engulfing", self.f_engulfing, "pattern"),
        ]

        for col_name, method, category in factor_methods:
            try:
                factors_df[col_name] = method() if callable(method) else method
            except Exception:
                factors_df[col_name] = np.nan

        # 元数据
        factors_df.attrs["factor_columns"] = [c for _, c, _ in factor_methods]
        factors_df.attrs["factor_categories"] = {c: cat for _, c, cat in factor_methods}

        return factors_df

    # ---- IC 衰减曲线 (v6.7) ----

    def compute_decay_curve(self, price_data: pd.DataFrame,
                            factor_name: str,
                            lookback: int = 120) -> dict:
        """
        计算因子的半衰期IC衰减曲线

        返回: {
          current_ic, ic_series, decaying(bool), days_since_positive, recommendation
        }
        """
        factors = self.compute_all()
        if factor_name not in factors.columns:
            return {"current_ic": 0, "decaying": False, "recommendation": "因子不存在"}

        close = price_data["close"]
        ret = close.pct_change().shift(-1)  # 未来1日收益
        factor_vals = factors[factor_name]

        common_idx = factor_vals.dropna().index.intersection(ret.dropna().index)
        ic_list = []
        dates = []

        for i in range(lookback, 0, -1):
            idx = common_idx[-i] if i <= len(common_idx) else None
            if idx is None or idx not in common_idx:
                continue
            fv = factor_vals.loc[:idx].iloc[-1]
            rv = ret.loc[:idx].iloc[-1]
            # 横截面IC需要多只股票, 这里用滚动时序相关
            f_slice = factor_vals.loc[:idx].iloc[-60:]
            r_slice = ret.loc[:idx].iloc[-60:]
            valid = f_slice.notna() & r_slice.notna()
            if valid.sum() < 20:
                continue
            ic = f_slice[valid].corr(r_slice[valid])
            ic_list.append(ic)
            dates.append(str(price_data["date"].iloc[min(idx, len(price_data)-1)])[:10])

        if not ic_list:
            return {"current_ic": 0, "decaying": False, "recommendation": "数据不足"}

        current_ic = ic_list[-1]
        # 检测衰退: IC连续5天低于0
        recent = ic_list[-20:] if len(ic_list) >= 20 else ic_list
        below_zero_streak = 0
        for ic in reversed(recent):
            if ic < 0:
                below_zero_streak += 1
            else:
                break

        # 找半衰点: IC首次跌破0.01 或 首次变负
        decay_start = None
        for i, ic in enumerate(recent):
            if ic < 0.01:
                decay_start = dates[-len(recent) + i] if i < len(dates) else "未知"
                break

        decaying = below_zero_streak >= 5
        recommendation = "正常"
        if decaying:
            recommendation = "衰退! 建议权重降为0"
        elif below_zero_streak >= 3:
            recommendation = "预警: 连续3日IC<0, 密切关注"
        elif current_ic < 0.01:
            recommendation = "弱效: IC接近0, 建议降权"

        self._decay_status[factor_name] = {
            "current_ic": round(current_ic, 4),
            "decaying": decaying,
            "below_zero_streak": below_zero_streak,
            "recommendation": recommendation,
            "decay_start": decay_start,
            "ic_series": list(zip(dates[-60:], ic_list[-60:])),
        }

        return self._decay_status[factor_name]

    def get_decay_status(self) -> dict:
        """获取所有因子的衰退状态"""
        return self._decay_status

    def get_active_factors(self) -> list:
        """返回未衰退的因子列表"""
        active = []
        for name, status in self._decay_status.items():
            if not status.get("decaying", False):
                active.append(name)
        return active


# ============================================================
# 因子注册表
# ============================================================

FACTOR_REGISTRY = {
    "ma_deviation":      Factor("ma_deviation", "trend",       "价格偏离均线程度", {"period": 20}),
    "ma_alignment":      Factor("ma_alignment", "trend",       "均线多头排列程度", {"short": 5, "mid": 20, "long": 60}),
    "ma_slope":          Factor("ma_slope",     "trend",       "均线斜率-趋势方向", {"period": 20, "lookback": 5}),
    "trend_strength":    Factor("trend_strength", "trend",     "趋势强度(类ADX)", {"period": 14}),
    "rsi_norm":          Factor("rsi_norm",     "momentum",    "RSI标准化(0超卖-1超买)", {"period": 14}),
    "macd_hist":         Factor("macd_hist",    "momentum",    "MACD动能柱标准化", {"fast": 12, "slow": 26, "signal": 9}),
    "roc_10":            Factor("roc_10",       "momentum",    "10日价格变化率", {"period": 10}),
    "price_position":    Factor("price_position", "momentum",  "价格在N日高低区间的位置", {"period": 60}),
    "momentum_score":    Factor("momentum_score", "momentum",  "多周期动量综合评分", {}),
    "volatility":        Factor("volatility",   "volatility",  "历史波动率(低波=高分)", {"period": 20}),
    "bollinger_pos":     Factor("bollinger_pos", "volatility", "布林带位置", {"period": 20, "std_dev": 2.0}),
    "bollinger_width":   Factor("bollinger_width", "volatility", "布林带宽度-波动预期", {"period": 20}),
    "atr_ratio":         Factor("atr_ratio",    "volatility",  "ATR/价格比-相对波动", {"period": 14}),
    "volume_ratio":      Factor("volume_ratio", "volume",      "量比(短/长)", {"short": 5, "long": 20}),
    "volume_trend":      Factor("volume_trend", "volume",      "量价配合健康度", {"period": 10}),
    "obv_divergence":    Factor("obv_divergence", "volume",    "OBV与价格背离检测", {"period": 20}),
    "hammer":            Factor("hammer",       "pattern",     "锤子线检测", {}),
    "engulfing":         Factor("engulfing",    "pattern",     "吞没形态检测", {}),
}


def get_v2_factor_registry():
    """Expose legacy definitions through the versioned V2 adapter."""
    from src.lxl_quantaxis.factor import LegacyFactorAdapter

    return LegacyFactorAdapter().registry()
