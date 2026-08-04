# Architecture Migration Plan — V1 → V2

**日期**: 2026-08-04  
**阶段**: Phase 1 — 纯分析, 不修改代码  

---

## 1. 两个架构的区别

### V1 (`src/` 顶层模块)

| 特征 | 描述 |
|------|------|
| 风格 | 实用主义, 快速迭代, 函数优于类 |
| 配置 | 模块级全局单例 `Config()`, 硬编码路径 `D:/trading_data/` |
| 数据 | 裸 `pd.read_csv` + `sqlite3.connect()`, CSV 缓存 |
| 回测 | 单一 `BacktestEngine` 类, `_run_legacy` + `_run_next_bar` 双路径 |
| 因子 | `FACTOR_REGISTRY` dict, `FactorCalculator` 直接计算 |
| 策略 | `BaseStrategy` ABC, `STRATEGIES` dict 注册 |
| Web | 单文件 `web_modern.py` (3242行), 60+路由直接在模块级定义 |
| 日志 | `print()` 和 `logging` 混用 |
| 错误 | 大量 `except Exception: pass` |
| 类型 | 少量 dataclass, 多数用普通 dict 传结果 |

### V2 (`src/lxl_quantaxis/` 包)

| 特征 | 描述 |
|------|------|
| 风格 | 领域驱动设计, 合约类型, 不可变数据 |
| 配置 | `SecuritySettings.from_env()`, `DataConfig`, 显式 fail-closed |
| 数据 | `DataPortal` PIT检查, `DataCatalog`, provider registry |
| 回测 | `BacktestEventLoop`, `DataPortal`, `NextBarOpenFillModel` |
| 因子 | `FactorSpec`, `FactorPipeline`, `FactorRegistry` |
| 策略 | `StrategySpec` (Pydantic), `StrategyCompiler`, `StrategyRegistry` |
| Web | API routes 拆分为 blueprint, middleware 独立 |
| 日志 | `logging.getLogger(__name__)` (标准库) |
| 错误 | 自定义异常类型, 显式 `raise` |
| 类型 | frozen dataclass, Pydantic models, 显式 contracts |

### 关键差异

```
V1:  dict结果 → 调用方自己解析 → 容易出错
V2:  dataclass/frozen → 类型安全 → 编译器检查

V1:  pd.read_csv(path) → 路径硬编码
V2:  DataPortal(data) → 显式注入

V1:  except Exception: pass → 错误静默消失
V2:  raise DomainError(...) → 明确失败
```

---

## 2. 模块迁移计划

### 已迁移 (V2 已完整, 旧版可废弃)

| V1 模块 | V2 模块 | 状态 |
|---------|---------|------|
| `src/portfolio/metrics.py` (部分) | `src/lxl_quantaxis/portfolio/analytics.py` | ✅ V2可用, 旧版保留兼容适配层 |
| 无 (新版) | `src/lxl_quantaxis/portfolio/allocation.py` | ✅ 纯新增 |
| 无 (新版) | `src/lxl_quantaxis/portfolio/accounting/` | ✅ 不可变账本 |
| 无 (新版) | `src/lxl_quantaxis/backtest/cost_model.py` | ✅ 集中化成本 |
| 无 (新版) | `src/lxl_quantaxis/backtest/signal_lag.py` | ✅ 信号延迟队列 |
| `src/risk/manager.py` (部分) | `src/lxl_quantaxis/risk/pre_trade/chain.py` | ⚠️ V2策略链, 旧版仍在使用 |
| 无 (新版) | `src/lxl_quantaxis/core/security/settings.py` | ✅ 安全配置 |
| 无 (新版) | `src/lxl_quantaxis/core/contracts/` | ✅ 领域类型 |

### 正在迁移 (双轨并存, 需要统一)

| V1 模块 | V2 模块 | 调用方 | 迁移策略 |
|---------|---------|--------|----------|
| `src/backtest/engine.py` (全部) | `lxl_quantaxis/backtest/engine/event_loop.py` | `web_modern.py`, `main.py` | V2 event_loop 已存在, V1 `_run_next_bar` 内部调用 V2 |
| `src/backtest/metrics.py` | `lxl_quantaxis/backtest/performance/metrics.py` | `engine.py` | V2 `PerformanceMetrics` 已存在, V1 `calc_all_metrics` 仍在使用 |
| `src/factors/definitions.py` | `lxl_quantaxis/factor/base/spec.py` | `composer.py`, `factor_miner.py` | V2 有 `FactorSpec`, V1 `FACTOR_REGISTRY` dict 仍在使用 |
| `src/strategies/library.py` | `lxl_quantaxis/strategy/base/spec.py` | `batch_runner.py`, `web_modern.py` | V2 有 `StrategySpec`+compiler, V1 `BaseStrategy` ABC 仍在使用 |
| `src/data/stock_db.py` | `lxl_quantaxis/data/catalog/models.py` | `web_modern.py`, `app.py` | V2 有 catalog, V1 裸 sqlite3 仍在使用 |
| `src/data/market_db.py` | `lxl_quantaxis/data/storage/local.py` | `data_feed.py` | V2 有 storage, V1 CSV 缓存仍在使用 |
| `src/execution/engine.py` | `lxl_quantaxis/execution/paper_trading/broker.py` | `app.py` | V2 有 paper_trading, V1 执行引擎仍在使用 |
| `src/ai/factory.py` | `lxl_quantaxis/ai/orchestration/daily.py` | `app.py` | V2 有编排层, V1 工厂仍在运行 |
| `src/realtime/` | 无 V2 对应 | `web_modern.py` | 未迁移, 需新建 `lxl_quantaxis/realtime/` |

### 暂不迁移 (纯展示/工具, 无V2对应)

| 模块 | 原因 |
|------|------|
| `src/app.py` (Tkinter) | 桌面GUI, V2不覆盖 |
| `src/dialogs.py` | Tkinter对话框 |
| `src/console.py` | 终端美化, 独立工具 |
| `src/audit/TradeAudit.py` | 独立审计模块 |
| `src/journal/cli.py` | CLI日志, 独立功能 |
| `src/report/generator.py` | 独立报告生成 |
| `src/dashboard/visual.py` | HTML仪表盘生成器 |
| `src/index/` (估值/轮动) | 独立研究工具 |
| `src/auth/auth.py` | 已有V2 security, 旧版仅用于Flask装饰器 |
| `src/database/` (ORM) | V2暂无ORM替代, 保留 |
| `main.py` | CLI入口, 保留但重定向到V2 |

---

## 3. 未来唯一核心入口设计

```
web_modern.py (Flask app)
    │
    ├── src/lxl_quantaxis/api/routes/     ← 所有 API 路由 (blueprint)
    │   ├── market.py          # 行情, K线, 搜索
    │   ├── strategy.py        # 策略CRUD, 回测
    │   ├── portfolio.py       # 组合, 持仓, 分配
    │   ├── research.py        # 诊断, 推荐, 估值
    │   ├── ai.py              # AI对话, 策略创建
    │   └── auth.py            # 登录, 注册, 用户管理
    │
    ├── src/lxl_quantaxis/api/middleware/  ← 安全, 限流, 日志
    │
    └── src/lxl_quantaxis/core/           ← 共享内核
        ├── config/            # 统一配置
        ├── security/          # 认证 (已有)
        ├── contracts/         # 领域类型 (已有)
        └── logging/           # 统一日志 (新建)

CLI (main.py)
    │
    └── 委托到 src/lxl_quantaxis/* 服务层

Desktop (src/app.py)
    │
    └── 委托到 src/lxl_quantaxis/* 服务层 (逐步)
```

### 入口统一原则

1. **所有业务逻辑** → `src/lxl_quantaxis/`
2. **旧 `src/` 模块** → 仅作为兼容适配层，内部委托给 V2
3. **新功能** → 直接在 V2 开发，不允许向旧模块添加新代码
4. **旧模块删除时机** → V2 对应模块稳定运行 30 天后删除旧版

---

## 4. 兼容性保证

- 所有现有 API 路由保持不变 (URL, method, response format)
- 所有现有 CLI 命令保持不变
- 所有现有策略、因子名称保持不变
- 数据库 schema 不变
- 环境变量名不变 (但增加 `QUANT_DATA_DIR` 优先于 `TRADING_DATA_DIR`)

---

## 5. 迁移风险矩阵

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| 旧引擎→V2引擎结果不一致 | 中 | 高 | 双轨并行, 对比测试 |
| Web路由重构引入bug | 中 | 中 | 逐条路由迁移, 保留旧路由做代理 |
| 因子计算结果变化 | 低 | 中 | 保留旧FACTOR_REGISTRY, V2新增命名空间 |
| 性能下降 | 低 | 低 | V2使用不可变类型, Python开销可控 |

---

## 6. 迁移顺序

```
Phase 1 (当前): 分析, 不改代码 ✅
Phase 2: 统一配置 + 统一日志 + 异常规范
Phase 3: 逐模块迁移 (顺序: core → portfolio → backtest → factor → strategy → data → api)
Phase 4: Web路由拆分 + CLI统一入口
Phase 5: 旧模块标记 deprecated → 30天后删除
```
