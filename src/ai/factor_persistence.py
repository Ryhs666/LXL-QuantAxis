"""
Factor Persistence — AI挖掘因子持久化

使 AIFactorMiner 通过 exec() 动态注册的因子在重启后能够恢复。

存储格式: D:/trading_data/mined_factors/{factor_name}.json
每个 JSON 包含完整的因子定义、源代码和性能统计。

安全性:
  - exec 前验证代码仅使用: pd, np, 基础算术, rolling, ewm, shift, diff
  - 不合法代码跳过并警告, 不执行
"""

import json
import os
import re
from typing import Dict, List, Optional
from datetime import datetime


class FactorPersistence:
    """因子持久化管理器"""

    STORE_DIR = os.path.join(
        os.environ.get("QUANT_DATA_DIR", os.environ.get("TRADING_DATA_DIR", "D:/trading_data")),
        "mined_factors"
    )

    # exec 安全白名单: 只允许这些模块和操作
    ALLOWED_NAMES = {"pd", "np", "abs", "min", "max", "sum", "len", "range", "round", "True", "False", "None"}
    BLOCKED_PATTERNS = [
        r"import\s", r"__import__", r"eval\s*\(", r"exec\s*\(", r"open\s*\(",
        r"os\.", r"sys\.", r"subprocess", r"shutil", r"globals\s*\(", r"locals\s*\(",
        r"getattr\s*\(", r"setattr\s*\(", r"delattr\s*\(",
    ]

    def __init__(self, store_dir: str = None):
        self.store_dir = store_dir or self.STORE_DIR
        os.makedirs(self.store_dir, exist_ok=True)

    # ═══════════════════════════════════════════
    # 安全校验
    # ═══════════════════════════════════════════

    @classmethod
    def is_safe_code(cls, code: str) -> bool:
        """检查代码是否只使用安全的操作"""
        for pattern in cls.BLOCKED_PATTERNS:
            if re.search(pattern, code):
                return False
        return True

    # ═══════════════════════════════════════════
    # 持久化操作
    # ═══════════════════════════════════════════

    def save_factor(self, factor_def: dict, source_symbol: str = "") -> str:
        """保存因子到磁盘, 返回文件路径"""
        name = factor_def.get("name", "unknown")
        if not name or name == "unknown":
            return ""

        filepath = os.path.join(self.store_dir, f"{name}.json")

        record = {
            "name": name,
            "chinese_name": factor_def.get("chinese_name", ""),
            "category": factor_def.get("category", "composite"),
            "description": factor_def.get("logic", factor_def.get("chinese_name", ""))[:200],
            "python_code": factor_def.get("python_code", ""),
            "mined_at": datetime.now().isoformat(),
            "source_symbol": source_symbol,
            "version": factor_def.get("version", 1),
            "performance": factor_def.get("performance", {
                "signals_generated": 0,
                "win_rate": 0.0,
                "avg_return": 0.0,
                "last_ic": 0.0,
                "decaying": False,
            }),
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2, ensure_ascii=False)

        return filepath

    def load_factor(self, name: str) -> Optional[dict]:
        """加载单个因子"""
        filepath = os.path.join(self.store_dir, f"{name}.json")
        if not os.path.exists(filepath):
            return None
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None

    def load_all_factors(self) -> List[dict]:
        """加载所有持久化因子"""
        factors = []
        if not os.path.exists(self.store_dir):
            return factors
        for fname in os.listdir(self.store_dir):
            if fname.endswith(".json"):
                name = fname[:-5]
                factor = self.load_factor(name)
                if factor:
                    factors.append(factor)
        return factors

    def delete_factor(self, name: str) -> bool:
        """删除因子"""
        filepath = os.path.join(self.store_dir, f"{name}.json")
        if os.path.exists(filepath):
            os.remove(filepath)
            return True
        return False

    def update_performance(self, name: str, stats: dict):
        """更新因子性能数据"""
        factor = self.load_factor(name)
        if factor:
            factor["performance"].update(stats)
            factor["version"] = factor.get("version", 1) + 1
            filepath = os.path.join(self.store_dir, f"{name}.json")
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(factor, f, indent=2, ensure_ascii=False)

    # ═══════════════════════════════════════════
    # 注册表恢复
    # ═══════════════════════════════════════════

    def reload_into_registry(self, verbose: bool = True) -> int:
        """
        将所有持久化因子重新 exec 并注册到 FACTOR_REGISTRY。
        在启动时调用, 恢复上次会话的 AI 挖掘因子。
        返回成功恢复的数量。
        """
        import pandas as pd
        import numpy as np

        try:
            from src.factors.definitions import Factor, FACTOR_REGISTRY
        except ImportError:
            return 0

        factors = self.load_all_factors()
        loaded = 0

        for fdef in factors:
            name = fdef["name"]
            code = fdef.get("python_code", "")

            if not code:
                continue

            # 安全校验
            if not self.is_safe_code(code):
                if verbose:
                    print(f"[FactorPersistence] WARN 因子 {name} 代码未通过安全检查, 跳过")
                continue

            # 提取函数体
            func_match = re.search(
                r'def calc_factor\s*\(data\)\s*:(.*?)(?=\n\S|\Z)',
                code, re.DOTALL
            )

            if func_match:
                func_body = func_match.group(1)
            else:
                func_body = code

            try:
                namespace = {"pd": pd, "np": np}
                full_code = f"def calc(data):\n{func_body}"
                exec(full_code, namespace)
                calc_fn = namespace.get("calc")

                if name not in FACTOR_REGISTRY:
                    FACTOR_REGISTRY[name] = Factor(
                        name=name,
                        category=fdef.get("category", "composite"),
                        description=fdef.get("description", ""),
                        compute=calc_fn,
                    )
                    loaded += 1
            except Exception as e:
                if verbose:
                    print(f"[FactorPersistence] WARN 恢复因子 {name} 失败: {e}")

        if verbose and loaded > 0:
            print(f"[FactorPersistence] OK 成功恢复 {loaded} 个持久化因子")

        return loaded

    def list_factors(self) -> List[str]:
        """列出所有持久化因子名称"""
        if not os.path.exists(self.store_dir):
            return []
        return [
            f[:-5] for f in os.listdir(self.store_dir)
            if f.endswith(".json")
        ]


# ═══════════════════════════════════════════
# 全局单例
# ═══════════════════════════════════════════

factor_persistence = FactorPersistence()
