"""
MarketRegimeDetector — 市场状态检测器 (v6.4)

方法:
  主: 滚动波动率 + 趋势强度 → 4状态分类
  可选: HMM (hmmlearn) 隐马尔可夫模型

4种状态:
  REGIME_0: 高波动单边上涨 → 加仓
  REGIME_1: 高波动单边下跌 → 减仓/空仓
  REGIME_2: 低波动震荡     → 正常仓位
  REGIME_3: 高波动剧烈反转  → 轻仓观望

自动联动: 更新 config.position_size_pct
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Tuple, Optional
import os, json


class MarketRegimeDetector:
    """市场状态检测器"""

    REGIME_LABELS = {
        0: "高波动单边上涨",
        1: "高波动单边下跌",
        2: "低波动震荡",
        3: "高波动剧烈反转",
    }

    POSITION_ADJUST = {
        0: 1.3,   # 单边上涨 → 加仓30%
        1: 0.3,   # 单边下跌 → 减到30%
        2: 1.0,   # 震荡 → 正常
        3: 0.5,   # 剧烈反转 → 半仓
    }

    def __init__(self, lookback: int = 60, vol_window: int = 20):
        self.lookback = lookback
        self.vol_window = vol_window
        self._current_regime = 2  # 默认震荡
        self._history: list = []
        self._switch_log: list = []
        self._last_regime = None

    # ═══════════════════════════════════════════
    # 核心: 滚动波动率 + 趋势分类
    # ═══════════════════════════════════════════

    def detect(self, data: pd.DataFrame) -> Tuple[int, str, dict]:
        """
        检测当前市场状态

        返回: (regime_id, label, detail_dict)
        """
        if data is None or len(data) < self.lookback:
            return 2, self.REGIME_LABELS[2], {"info": "数据不足,默认震荡"}

        close = data["close"]
        ret = close.pct_change().dropna()
        recent = ret.tail(self.lookback)
        vol = recent.rolling(self.vol_window).std().iloc[-1] * np.sqrt(252)

        # 趋势判断
        ma20 = close.rolling(20).mean().iloc[-1]
        ma60 = close.rolling(60).mean().iloc[-1]
        trend = (close.iloc[-1] / ma20 - 1)  # 短期趋势
        trend_medium = (ma20 / ma60 - 1)  # 中期趋势

        # 反转检测: 涨跌幅方向切换频率
        direction = np.sign(recent)
        flips = (direction.diff().abs() > 0).sum()
        flip_rate = flips / len(recent)  # 方向切换率

        # 波动分位 (相对于历史)
        hist_vol = ret.rolling(self.vol_window).std() * np.sqrt(252)
        vol_percentile = (hist_vol.dropna().iloc[-1] < hist_vol.dropna()).mean()

        # 分类逻辑
        high_vol = vol > 0.30 or vol_percentile > 0.7
        strong_trend = abs(trend) > 0.03 or abs(trend_medium) > 0.05

        if high_vol and trend > 0.02 and flip_rate < 0.35:
            regime = 0  # 高波动单边上涨
        elif high_vol and trend < -0.02 and flip_rate < 0.35:
            regime = 1  # 高波动单边下跌
        elif high_vol and flip_rate > 0.45:
            regime = 3  # 高波动剧烈反转
        else:
            regime = 2  # 低波动震荡

        detail = {
            "volatility": round(vol * 100, 1),
            "vol_percentile": round(vol_percentile * 100),
            "trend_short": round(trend * 100, 2),
            "trend_medium": round(trend_medium * 100, 2),
            "flip_rate": round(flip_rate * 100),
            "price": round(close.iloc[-1], 2),
            "ma20": round(ma20, 2),
            "ma60": round(ma60, 2),
        }

        # 记录状态切换
        if self._last_regime is not None and self._last_regime != regime:
            self._log_switch(self._last_regime, regime, detail)

        self._last_regime = regime
        self._current_regime = regime
        self._history.append({"date": str(data["date"].iloc[-1])[:10], "regime": regime,
                              **detail})

        return regime, self.REGIME_LABELS[regime], detail

    def _log_switch(self, old: int, new: int, detail: dict):
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        msg = (f"[RegimeSwitch] {now} | {self.REGIME_LABELS[old]} → {self.REGIME_LABELS[new]} | "
               f"vol={detail['volatility']}% trend={detail['trend_short']}%")
        self._switch_log.append(msg)
        # 写入日志文件
        try:
            log_path = os.environ.get("QUANT_DATA_DIR", os.environ.get("TRADING_DATA_DIR", os.path.expanduser("~/lxl_quantaxis_data"))) + "/logs/regime_switch.log"
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(msg + "\n")
        except:
            pass

    # ═══════════════════════════════════════════
    # 仓位联动
    # ═══════════════════════════════════════════

    def get_position_ratio(self, base_pct: float = 0.3) -> float:
        """根据市场状态调整仓位比例"""
        adj = self.POSITION_ADJUST.get(self._current_regime, 1.0)
        return round(base_pct * adj, 3)

    def apply_to_config(self, base_pct: float = 0.3):
        """自动更新config中的仓位设置"""
        new_pct = self.get_position_ratio(base_pct)
        try:
            from src.config import config
            config._data["position_size_pct"] = new_pct
            return new_pct
        except:
            return new_pct

    # ═══════════════════════════════════════════
    # HMM (可选)
    # ═══════════════════════════════════════════

    def detect_hmm(self, data: pd.DataFrame) -> Tuple[int, str, dict]:
        """HMM检测 (需要 hmmlearn)"""
        try:
            from hmmlearn import hmm
        except ImportError:
            return self.detect(data)  # 降级

        close = data["close"]
        ret = close.pct_change().dropna().tail(500)
        if len(ret) < 200:
            return self.detect(data)

        vol = ret.rolling(20).std().dropna() * np.sqrt(252)
        # 特征: [收益率, 波动率, 涨跌比]
        up_ratio = (ret > 0).rolling(20).mean().dropna()
        common_idx = ret.dropna().index.intersection(vol.index).intersection(up_ratio.index)
        features = np.column_stack([
            ret.loc[common_idx].values,
            vol.loc[common_idx].values,
            up_ratio.loc[common_idx].values,
        ])
        features = np.nan_to_num(features)

        try:
            model = hmm.GaussianHMM(n_components=4, covariance_type="full",
                                    n_iter=100, random_state=42)
            model.fit(features)
            current_state = model.predict(features[-1:])[0]
        except Exception:
            return self.detect(data)

        detail = {"method": "HMM", "features": ["ret", "vol", "up_ratio"]}

        # 根据状态特征分类
        state_means = model.means_[current_state]
        mean_ret = state_means[0]
        mean_vol = state_means[1]
        if mean_vol > 0.02 and mean_ret > 0:
            regime = 0
        elif mean_vol > 0.02 and mean_ret < 0:
            regime = 1
        elif mean_vol < 0.01:
            regime = 2
        else:
            regime = 3

        return regime, self.REGIME_LABELS[regime], detail

    # ═══════════════════════════════════════════
    # 报告
    # ═══════════════════════════════════════════

    @property
    def current_regime(self) -> int:
        return self._current_regime

    @property
    def current_label(self) -> str:
        return self.REGIME_LABELS.get(self._current_regime, "未知")

    def get_history(self) -> pd.DataFrame:
        return pd.DataFrame(self._history)

    def get_switch_log(self) -> list:
        return self._switch_log[-20:]

    def report(self) -> str:
        lines = ["═══ Market Regime ═══"]
        lines.append(f"当前状态: {self.current_regime} - {self.current_label}")
        lines.append(f"建议仓位: {self.get_position_ratio()*100:.0f}%")
        lines.append("")
        lines.append("最近切换:")
        for s in self._switch_log[-5:]:
            lines.append(f"  {s}")
        return "\n".join(lines)


# 全局实例
detector = MarketRegimeDetector()


def quick_detect(symbol: str = "000300", market: str = "指数") -> dict:
    """快速检测当前市场状态"""
    from src.backtest.data_feed import get_data
    data = get_data(symbol, market, start_date="2023-01-01")
    if data is None or len(data) == 0:
        return {"regime": 2, "label": "数据不足", "position": 0.3}
    regime, label, detail = detector.detect(data)
    pos = detector.get_position_ratio()
    return {"regime": regime, "label": label, "position_pct": pos, "detail": detail}
