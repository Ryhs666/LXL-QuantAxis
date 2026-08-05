# V2 Dependency Map — Phase 1.5

**日期**: 2026-08-04

## 核心发现: V2 完全独立

```
V2 (src/lxl_quantaxis/)     ←── 14个V1模块导入V2
   ↑                              ↑
   │                              │
   └── 0个V2模块导入V1 ─────────────┘
```

V2 对 V1 的依赖为 **零**。这是干净的架构边界。

## V1→V2 导入清单 (14 modules)

| V1 模块 | 导入的 V2 模块 |
|---------|---------------|
| `src/config.py` | `lxl_quantaxis.core.config.settings` |
| `src/auth/auth.py` | `lxl_quantaxis.core.security.settings, rate_limit` |
| `src/backtest/engine.py` | `lxl_quantaxis.backtest.{event_loop,data_portal,fill_models,performance}` |
| `src/backtest/metrics.py` | `lxl_quantaxis.backtest.performance.metrics` |
| `src/backtest/data_feed.py` | `lxl_quantaxis.data.providers.contracts` |
| `src/backtest/providers.py` | `lxl_quantaxis.data.providers.contracts` |
| `src/ai/engine.py` | `lxl_quantaxis.ai.ports` |
| `src/ai/research.py` | `lxl_quantaxis.research.{application,evidence}` |
| `src/app.py` | `lxl_quantaxis.research` |
| `src/factors/definitions.py` | `lxl_quantaxis.factor.registry` |
| `src/factors/fundamental.py` | `lxl_quantaxis.factor.base.spec` |
| `src/risk/manager.py` | `lxl_quantaxis.risk.policies.standard` |
| `src/core/plugin.py` | `lxl_quantaxis.core.events.domain` |
| `src/database/__init__.py` | `lxl_quantaxis.core.security.settings` |

## V2 独立模块 (ZERO V1 imports)

| V2 模块 | 行数 | 状态 |
|---------|------|------|
| `core/config/loader.py` | 140 | ✅ 新建, 无V1依赖 |
| `core/logging.py` | 40 | ✅ 新建 |
| `core/exceptions.py` | 25 | ✅ 新建 |
| `core/contracts/` | 3 files | ✅ 纯合约 |
| `core/security/` | 2 files | ✅ 独立 |
| `portfolio/analytics.py` | 318 | ✅ 独立 |
| `portfolio/allocation.py` | 300+ | ✅ 独立 |
| `portfolio/accounting/` | 2 files | ✅ 独立 |
| `backtest/cost_model.py` | 100+ | ✅ 独立 |
| `backtest/signal_lag.py` | 55 | ✅ 独立 |
| `backtest/event_loop.py` | 50+ | ✅ 独立 |
| `backtest/fill_models.py` | 60+ | ✅ 独立 |
| `factor/` | 5 files | ✅ 独立 |
| `strategy/` | 6 files | ✅ 独立 |
| `data/` | 12 files | ✅ 独立 |
| `api/` | 8 files | ✅ 独立 |
| `memory/` | 4 files | ✅ 独立 |
| `research/` | 7 files | ✅ 独立 |
| `risk/` | 3 files | ✅ 独立 |

## 结论

V2 是一个**干净的、向后兼容的扩展层**。它不修改 V1, 只通过 14 个明确的导入点被 V1 引用。迁移可以安全推进。
