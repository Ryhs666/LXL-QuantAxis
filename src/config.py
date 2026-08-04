"""
量化系统全局配置

使用方式:
    from src.config import config
    print(config.initial_capital)
    print(config.data_dir)
"""

import os
import json
from pathlib import Path
from typing import Any

try:
    import yaml
    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False


# 默认配置
DEFAULTS = {
    # ---- 系统 ----
    "project_name": "LXL·QuantAxis",
    "version": "2.0.0-alpha.1",
    "log_level": "INFO",
    "log_dir": "D:/trading_data/logs",

    # ---- 数据 ----
    "data_dir": "D:/trading_data",
    "cache_dir": "D:/trading_data/cache",
    "cache_expire_days": 1,
    "default_start_date": "2020-01-01",

    # ---- 回测 ----
    "initial_capital": 100_000,
    "commission_rate": 0.0003,
    "slippage": 0.001,
    "position_size_pct": 0.3,

    # ---- 风控 ----
    "max_positions": 10,
    "stop_loss_pct": 0.05,
    "take_profit_pct": 0.15,
    "max_drawdown_limit": 0.25,

    # 移动止损
    "risk_trailing_stop_pct": 0.05,       # 从最高点回撤5%止损
    # 熔断
    "risk_max_drawdown_pct": 0.10,        # 总回撤10%熔断
    "risk_enable_circuit_breaker": True,   # 启用熔断
    # 凯利仓位
    "risk_kelly_fraction": 0.5,            # 半凯利=0.5, 全凯利=1.0
    "risk_max_single_position_pct": 0.15,  # 单只股票仓位上限15%

    # ---- A股特殊规则 ----
    "a_stock_lot_size": 100,
    "a_stock_stamp_tax": 0.001,

    # ---- 显示 ----
    "verbose": True,
    "use_progress_bar": True,
    "chart_theme": "plotly_white",

    # ---- 数据源 ----
    "primary_market": "A股",
    "fallback_to_akshare": True,

    # ---- 实时行情 ----
    "realtime_data_source": "tencent",     # tencent / eastmoney / akshare / simulator
    "realtime_symbols": [                  # 实时推送股票池
        "000001", "000002", "600000", "600036", "601318",
        "000858", "002415", "300750", "600519", "000333",
    ],
    "realtime_poll_interval": 3,           # 拉取间隔(秒)
    "realtime_retry_interval": 10,         # 断线重连间隔(秒)
}

# ============================================================
# 参数白名单 — 防止参数注入攻击 (陷阱1)
# 每个策略只允许这些参数名，类型和范围在此定义
# ============================================================
PARAM_WHITELIST = {
    "ma_cross": {
        "fast_period":  {"type": int,   "range": (1, 100)},
        "slow_period":  {"type": int,   "range": (2, 200)},
        "vol_confirm":  {"type": bool,  "range": None},
        "vol_ratio":    {"type": float, "range": (0.5, 10.0)},
    },
    "rsi": {
        "rsi_period":   {"type": int,   "range": (2, 100)},
        "oversold":     {"type": float, "range": (5.0, 50.0)},
        "overbought":   {"type": float, "range": (50.0, 95.0)},
        "require_recovery": {"type": bool, "range": None},
    },
    "macd": {
        "fast":         {"type": int,   "range": (2, 50)},
        "slow":         {"type": int,   "range": (5, 100)},
        "signal":       {"type": int,   "range": (2, 50)},
        "filter_zero":  {"type": bool,  "range": None},
    },
    "bollinger": {
        "period":       {"type": int,   "range": (2, 100)},
        "std_dev":      {"type": float, "range": (0.5, 5.0)},
        "buy_on_lower": {"type": bool,  "range": None},
        "sell_on_middle": {"type": bool, "range": None},
    },
    "turtle": {
        "entry_period": {"type": int,   "range": (5, 100)},
        "exit_period":  {"type": int,   "range": (2, 50)},
        "atr_period":   {"type": int,   "range": (5, 50)},
        "atr_stop":     {"type": float, "range": (0.5, 5.0)},
    },
    "mean_reversion": {
        "ma_period":    {"type": int,   "range": (5, 100)},
        "deviation_pct": {"type": float, "range": (0.5, 20.0)},
        "rsi_period":   {"type": int,   "range": (2, 50)},
        "rsi_extreme":  {"type": float, "range": (10.0, 45.0)},
    },
    "momentum": {
        "breakout_period": {"type": int, "range": (5, 100)},
        "exit_period":    {"type": int,  "range": (2, 50)},
        "volume_confirm": {"type": bool, "range": None},
        "trend_filter":   {"type": bool, "range": None},
    },
}

_config = None


class Config:
    """全局配置管理"""

    def __init__(self, config_path: str = None):
        self._data = DEFAULTS.copy()
        self._loaded_from = []

        # 1. 加载默认配置
        self._loaded_from.append("defaults")

        # 2. 尝试加载 YAML 配置
        if config_path is None:
            config_path = os.environ.get(
                "QUANT_CONFIG",
                str(Path(__file__).parent.parent.parent / "config.yaml")
            )
        self._load_yaml(config_path)

        # 3. 环境变量覆盖（QUANT_ 前缀）
        self._load_env()

        # 确保目录存在
        for d in ["data_dir", "cache_dir", "log_dir"]:
            os.makedirs(self._data[d], exist_ok=True)

    def _load_yaml(self, path: str):
        if not os.path.exists(path):
            return
        try:
            if _HAS_YAML:
                with open(path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
            else:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            if data:
                self._data.update(data)
                self._loaded_from.append(path)
        except Exception as e:
            print(f"[Config] 警告: 无法加载 {path}: {e}")

    def _load_env(self):
        """从环境变量覆盖配置，格式: QUANT_INITIAL_CAPITAL=200000"""
        for key in self._data:
            env_key = f"QUANT_{key.upper()}"
            if env_key in os.environ:
                val = os.environ[env_key]
                # 类型转换
                orig = self._data[key]
                if isinstance(orig, bool):
                    val = val.lower() in ("1", "true", "yes")
                elif isinstance(orig, int):
                    val = int(val)
                elif isinstance(orig, float):
                    val = float(val)
                self._data[key] = val
                self._loaded_from.append(f"env:{env_key}")

    def __getattr__(self, key: str) -> Any:
        if key.startswith("_"):
            return object.__getattribute__(self, key)
        if key in self._data:
            return self._data[key]
        raise AttributeError(f"未知配置项: {key}")

    def __getitem__(self, key: str) -> Any:
        return self._data.get(key)

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def __contains__(self, key: str) -> bool:
        return key in self._data

    def keys(self):
        return self._data.keys()

    def to_dict(self) -> dict:
        return dict(self._data)

    def save(self, path: str = None):
        """保存当前配置为 JSON"""
        if path is None:
            path = str(Path(__file__).parent.parent.parent / "config.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)
        print(f"[Config] 配置已保存到: {path}")

    def info(self):
        """打印当前配置信息"""
        print(f"\n  配置来源: {self._loaded_from}")
        print(f"  数据目录: {self.data_dir}")
        print(f"  缓存目录: {self.cache_dir}")
        print(f"  初始资金: ¥{self.initial_capital:,}")
        print(f"  手续费率: {self.commission_rate:.4f}")
        print(f"  默认仓位: {self.position_size_pct * 100:.0f}%")


# 全局单例
config = Config()
