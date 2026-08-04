"""
Strategy Bank Bridge — 统一两个策略银行

当前系统有两个独立的策略存储:
  1. data/strategy_store.py → StrategyBank, SQLite (strategy_bank.db), 用户手动创建
  2. ai/factory.py → StrategyBank, JSON (bank.json), AI进化自动生成

UnifiedStrategyBank 提供统一接口, 支持跨库搜索和迁移。
"""

import json
import os
from typing import List, Dict, Optional
from datetime import datetime


class UnifiedStrategyBank:
    """统一策略银行 — 包裹 SQLite + JSON 两个子银行"""

    def __init__(self, data_dir: str = None):
        if data_dir is None:
            data_dir = os.environ.get(
                "QUANT_DATA_DIR",
                os.environ.get("TRADING_DATA_DIR", "D:/trading_data")
            )
        self.data_dir = data_dir
        self._sqlite_bank = None   # 延迟加载
        self._json_path = os.path.join(data_dir, "strategy_bank", "bank.json")

    # ── SQLite bank (lazy) ────────────────────────────

    def _get_sqlite_bank(self):
        if self._sqlite_bank is None:
            try:
                from src.data.strategy_store import StrategyBank
                self._sqlite_bank = StrategyBank()
            except ImportError:
                self._sqlite_bank = None
        return self._sqlite_bank

    # ── JSON bank ──────────────────────────────────────

    def _load_json_bank(self) -> List[dict]:
        if not os.path.exists(self._json_path):
            return []
        try:
            with open(self._json_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []

    def _save_json_bank(self, entries: List[dict]):
        os.makedirs(os.path.dirname(self._json_path), exist_ok=True)
        with open(self._json_path, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2, ensure_ascii=False)

    # ── Unified API ────────────────────────────────────

    def list_all(self, source: str = "all", limit: int = 100) -> List[dict]:
        """列出所有策略, 统一格式"""
        results = []

        # JSON bank (evolution)
        if source in ("all", "evolution"):
            for entry in self._load_json_bank():
                results.append(self._normalize_evolution(entry))

        # SQLite bank (user)
        if source in ("all", "user"):
            sqlite = self._get_sqlite_bank()
            if sqlite:
                for entry in sqlite.list_strategies():
                    results.append(self._normalize_user(entry))

        # 按 fitness 降序
        results.sort(key=lambda x: x.get("fitness", 0), reverse=True)
        return results[:limit]

    def get_best(self, n: int = 5, source: str = "all",
                  min_fitness: float = 0.0) -> List[dict]:
        """获取最佳 N 个策略"""
        all_s = self.list_all(source=source)
        filtered = [s for s in all_s if s.get("fitness", 0) >= min_fitness]
        return filtered[:n]

    def get_best_for_regime(self, regime_id: int, n: int = 3) -> List[dict]:
        """获取指定市场状态下表现最佳的策略

        依赖 AlphaSignalStore 中的 regime_performance_matrix 来判断。
        如果 alpha_store 不可用, 退化为 get_best()。
        """
        try:
            from src.ai.alpha_store import alpha_store
            matrix = alpha_store.get_regime_performance_matrix()
            if regime_id in matrix:
                best_factors = matrix[regime_id].get("best_factors", [])
                if best_factors:
                    # 找使用这些因子的策略
                    candidates = []
                    for s in self.list_all():
                        conditions = s.get("conditions", [])
                        s_factors = [c.get("factor", "") for c in conditions]
                        overlap = set(best_factors) & set(s_factors)
                        if overlap:
                            s["regime_match_score"] = len(overlap)
                            candidates.append(s)
                    candidates.sort(key=lambda x: x.get("regime_match_score", 0), reverse=True)
                    if candidates:
                        return candidates[:n]
        except ImportError:
            pass

        return self.get_best(n)

    def search(self, keyword: str) -> List[dict]:
        """搜索策略 (名称 + 描述 + 因子名)"""
        keyword_lower = keyword.lower()
        results = []
        for s in self.list_all():
            text = (s.get("name", "") + " " +
                    s.get("description", "") + " " +
                    " ".join(c.get("factor", "") for c in s.get("conditions", [])))
            if keyword_lower in text.lower():
                results.append(s)
        return results

    def find_by_factor(self, factor_name: str, source: str = "all") -> List[dict]:
        """按因子查找使用该因子的策略"""
        results = []
        for s in self.list_all(source=source):
            for c in s.get("conditions", []):
                if c.get("factor") == factor_name:
                    results.append(s)
                    break
        return results

    def deposit(self, strategy: dict, source: str = "evolution") -> bool:
        """存入策略到指定银行"""
        if source == "evolution":
            entries = self._load_json_bank()
            entries.append(self._serialize_for_json(strategy))
            # 排序并限制 50 条
            entries.sort(key=lambda x: x.get("fitness", 0), reverse=True)
            self._save_json_bank(entries[:50])
            return True
        elif source == "user":
            sqlite = self._get_sqlite_bank()
            if sqlite:
                sqlite.save_strategy(
                    name=strategy.get("name", "unnamed"),
                    description=strategy.get("description", ""),
                    conditions=strategy.get("conditions", []),
                    logic=strategy.get("logic", "and"),
                    threshold=strategy.get("threshold", 0.5),
                )
                return True
        return False

    def migrate_evolution_to_user(self, top_n: int = 10) -> int:
        """将 JSON bank 中 top N 策略迁移到 SQLite user bank"""
        evolved = self.get_best(n=top_n, source="evolution")
        if not evolved:
            return 0

        sqlite = self._get_sqlite_bank()
        if not sqlite:
            return 0

        migrated = 0
        for s in evolved:
            self.deposit(s, source="user")
            migrated += 1

        return migrated

    def auto_adjust_decaying_factors(self) -> dict:
        """检查所有策略中的衰减因子并自动调整权重

        依赖: FactorCalculator 的 _decay_status (实时计算)
              或 AlphaSignalStore 的 get_factor_health() (历史回顾)

        返回: {strategy_name: {factor: new_decay}}
        """
        try:
            from src.ai.alpha_store import alpha_store
            health = alpha_store.get_factor_health()
        except ImportError:
            health = {}

        changes = {}
        for s in self.list_all(source="evolution"):
            conditions = s.get("conditions", [])
            for c in conditions:
                factor_name = c.get("factor", "")
                if factor_name in health:
                    h = health[factor_name]
                    if h.get("health") in ("weak", "ineffective", "stale"):
                        c["decay_factor"] = 0.3 if h["health"] == "weak" else 0.0
                        changes.setdefault(s.get("name", ""), {})[factor_name] = c["decay_factor"]

        return changes

    def stats(self) -> dict:
        """统计概览"""
        json_entries = self._load_json_bank()
        sqlite_count = 0
        sqlite = self._get_sqlite_bank()
        if sqlite:
            try:
                sqlite_count = len(sqlite.list_strategies())
            except Exception:
                pass

        return {
            "evolution_bank": len(json_entries),
            "user_bank": sqlite_count,
            "total": len(json_entries) + sqlite_count,
            "json_path": self._json_path,
        }

    # ── 内部格式转换 ──────────────────────────────────

    def _normalize_evolution(self, entry: dict) -> dict:
        """JSON bank entry → 统一格式"""
        conditions = []
        for bf in entry.get("buy_factors", []):
            conditions.append({
                "factor": bf.get("factor", ""),
                "operator": bf.get("operator", "lt"),
                "threshold": bf.get("threshold", 0.5),
                "weight": bf.get("weight", 1.0),
                "decay_factor": bf.get("decay_factor", 1.0),
                "action": "BUY",
            })
        for sf in entry.get("sell_factors", []):
            conditions.append({
                "factor": sf.get("factor", ""),
                "operator": sf.get("operator", "gt"),
                "threshold": sf.get("threshold", 0.5),
                "weight": sf.get("weight", 1.0),
                "decay_factor": sf.get("decay_factor", 1.0),
                "action": "SELL",
            })
        return {
            "id": f"ev:{entry.get('name', '')}",
            "name": entry.get("name", ""),
            "source": "evolution",
            "type": "strategy_gene",
            "description": f"进化策略 (买入{len(entry.get('buy_factors',[]))}因子/卖出{len(entry.get('sell_factors',[]))}因子)",
            "conditions": conditions,
            "logic": entry.get("buy_logic", "weighted"),
            "threshold": entry.get("buy_threshold", 2.0),
            "fitness": entry.get("fitness", 0),
            "deposited_at": entry.get("deposited_at", ""),
            "tags": [],
        }

    def _normalize_user(self, entry) -> dict:
        """SQLite user bank entry → 统一格式"""
        # entry 来自 strategy_store.list_strategies()
        # 可能是 dict 或 namedtuple
        if isinstance(entry, dict):
            d = entry
        elif hasattr(entry, "_asdict"):
            d = entry._asdict()
        else:
            d = {"name": str(entry)}

        conditions = []
        try:
            raw = d.get("conditions_json", "[]")
            if isinstance(raw, str):
                raw_conditions = json.loads(raw)
            else:
                raw_conditions = raw if isinstance(raw, list) else []
            for c in raw_conditions:
                conditions.append({
                    "factor": c.get("factor", ""),
                    "operator": c.get("operator", "lt"),
                    "threshold": c.get("threshold", 0.5),
                    "weight": c.get("weight", 1.0),
                    "decay_factor": c.get("decay_factor", 1.0),
                })
        except (json.JSONDecodeError, TypeError):
            pass

        return {
            "id": f"usr:{d.get('id', '')}",
            "name": d.get("name", ""),
            "source": "user",
            "type": "signal_composer",
            "description": d.get("description", ""),
            "conditions": conditions,
            "logic": d.get("logic", "weighted"),
            "threshold": d.get("threshold", 2.0),
            "fitness": d.get("star", 0),
            "deposited_at": d.get("created_at", ""),
            "tags": d.get("tags", "").split(",") if d.get("tags") else [],
        }

    def _serialize_for_json(self, strategy: dict) -> dict:
        """统一格式 → JSON bank 格式"""
        buy_factors = [
            {"factor": c.get("factor"), "operator": c.get("operator"),
             "threshold": c.get("threshold"), "weight": c.get("weight")}
            for c in strategy.get("conditions", [])
            if c.get("action", "BUY") == "BUY"
        ]
        sell_factors = [
            {"factor": c.get("factor"), "operator": c.get("operator"),
             "threshold": c.get("threshold"), "weight": c.get("weight")}
            for c in strategy.get("conditions", [])
            if c.get("action") == "SELL"
        ]
        return {
            "name": strategy.get("name", ""),
            "source": "migrated",
            "fitness": strategy.get("fitness", 0),
            "buy_factors": buy_factors,
            "sell_factors": sell_factors,
            "buy_logic": strategy.get("logic", "weighted"),
            "buy_threshold": strategy.get("threshold", 2.0),
            "generation": 0,
            "deposited_at": datetime.now().isoformat(),
        }


# ═══════════════════════════════════════════
# 全局单例
# ═══════════════════════════════════════════

unified_bank = UnifiedStrategyBank()
