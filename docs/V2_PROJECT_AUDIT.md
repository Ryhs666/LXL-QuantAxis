# LXL·QuantAxis V2.0 — 项目审计报告

**日期**: 2026-08-04  
**分支**: `fix/portfolio-metrics-v2`  
**代码量**: 287 文件, 37,597 行  
**测试**: 394 passed, 119 subtests  

---

## 一、项目结构

```
LXL-QuantAxis/
├── main.py                    # CLI 交互菜单 (20+ 功能)
├── web_modern.py              # Flask-SocketIO Web (3242行, 60+路由)
├── web_app.py                 # Flask Web (旧版)
├── daily_runner.py            # 每日自动扫描
├── src/                       # 旧架构 (仍在运行)
│   ├── backtest/              # 回测引擎·数据源·优化器·宏观
│   ├── strategies/            # 16策略
│   ├── factors/               # 28因子·信号组合器
│   ├── ai/                    # AI助手·引擎·工厂·情绪
│   ├── analysis/              # 图表·报表·市场状态
│   ├── realtime/              # 行情采集·策略引擎·K线
│   ├── execution/             # 执行引擎·模拟交易
│   ├── data/                  # 数据仓库·股票DB·财务
│   ├── dashboard/             # HTML仪表盘
│   ├── risk/                  # 风控管理器
│   ├── portfolio/             # 组合持仓管理
│   ├── journal/               # 交易日志
│   ├── auth/                  # JWT认证
│   └── database/              # ORM
├── src/lxl_quantaxis/         # V2架构 (建设中)
│   ├── core/                  # 合约·配置·安全·事件·时钟·可观测
│   ├── backtest/              # 数据门户·事件循环·成交模型·成本·信号延迟
│   ├── portfolio/             # 会计·分析·分配
│   ├── strategy/              # 基础·编译器·注册表·spec
│   ├── factor/                # 基础·流水线·注册·验证
│   ├── data/                  # 合约·目录·提供者·存储·质量
│   ├── api/                   # 路由·中间件·schema·服务
│   ├── ai/                    # 分析师·护栏·编排·提示词
│   ├── memory/                # 记忆·提取
│   ├── execution/             # 券商接口·订单·模拟
│   ├── risk/                  # 策略·交易前
│   ├── research/              # 公司·财务·行业·估值·报告
│   ├── dashboard/             # 工作区·功能开关
│   └── ops/                   # 运维
└── tests/                     # 394测试 (单元+集成+安全+合同+回测)
```

### 核心文件作用

| 文件 | 作用 | 行数 |
|------|------|------|
| `web_modern.py` | Flask-SocketIO 主应用, 60+路由, 5页面 | 3242 |
| `main.py` | CLI 交互菜单, --tune/--allocate等命令行 | 1700+ |
| `src/app.py` | Tkinter 桌面应用 | 1500+ |
| `src/backtest/engine.py` | 回测引擎: Portfolio + BacktestEngine | 600+ |
| `src/backtest/batch_runner.py` | 批量回测 + ResultDB | 600+ |
| `src/factors/definitions.py` | 28因子注册表 + FactorCalculator | 500+ |
| `src/strategies/library.py` | 12策略注册表 + 7经典策略实现 | 800+ |
| `src/ai/factory.py` | 策略工厂: AI分析→进化→银行 | 600+ |
| `src/lxl_quantaxis/core/security/settings.py` | 安全配置, JWT, 环境检测 | 116 |
| `src/lxl_quantaxis/portfolio/analytics.py` | 显式语义组合指标 | 318 |
| `src/lxl_quantaxis/portfolio/allocation.py` | 4种分配模型+walk-forward | 300+ |
| `src/lxl_quantaxis/backtest/cost_model.py` | 集中化交易成本 | 100+ |

---

## 二、系统架构分层分析

### Data Layer

**实现**: `src/backtest/data_feed.py` (akshare+yfinance), `src/data/market_db.py` (SQLite), `src/lxl_quantaxis/data/` (V2 contracts+providers)

**优点**: 多市场支持(A股/港股/美股), 双源fallback, CSV缓存, V2已有合约抽象

**缺陷**: 旧代码双源路径不一致, 无PIT数据语义, V2数据层未完全接入

**方向**: 统一到V2 catalog+providers, 实现PIT, 添加数据质量监督

### Model Layer

**实现**: `src/models/trade.py` (Trade/TradeRepository), `src/models/strategy.py` (Signal/StrategyConfig), `src/lxl_quantaxis/core/contracts/`

**优点**: 清晰的dataclass, SQLite CRUD完整, V2有不可变合约类型

**缺陷**: 两套模型, 旧TradeRepository使用裸sqlite3, V2 contracts未全面替换

### Strategy Layer

**实现**: 16策略 (7经典+5高级+4因子), `src/lxl_quantaxis/strategy/` (V2 base+compiler+registry)

**优点**: 策略丰富, 信号组合器灵活, V2有编译器和spec

**缺陷**: 循环导入需懒加载, 策略与回测耦合, V2编译器未完成

### Backtest Layer

**实现**: 事件驱动引擎, T+1成交, Portfolio模拟账户, V2 event_loop+fill_models

**优点**: 无前视偏差(默认), 涨跌停检查, A股成本模型, Symbol解析

**缺陷**: `_run_legacy`与`_run_next_bar`两套路径共存, V2 event_loop未完全替代旧引擎

### Analysis Layer

**实现**: 绩效指标, Plotly图表, 因子IC分析, 分层回测, 归因分析, 市场状态检测

**优点**: 指标丰富, 显式simple/log语义, 图表交互式

**缺陷**: 部分指标仍用可变dict, 报告生成缺乏模板化

### AI Layer

**实现**: LLMClient(HTTP直接调用), 策略工厂(分析→生成→进化), 情绪分析, AI复盘/简报

**优点**: 支持多LLM, 工厂闭环(AI→进化→复测→银行), 安全白名单算子(无exec)

**缺陷**: Prompt管理分散, 无token成本追踪, AI生成策略需人工确认流程(V2护栏已部分实现)

### UI Layer

**实现**: Tkinter桌面, Flask Web(5页面), Plotly图表, SocketIO实时推送

**优点**: 三端覆盖, 实时行情+信号推送, v2仪表盘K线图

**缺陷**: Tkinter GUI过时, Web `eventlet`在Windows上有兼容问题

---

## 三、量化系统审计

| 能力 | 评分 | 说明 |
|------|------|------|
| 因子研究 | ★★★★☆ | 28因子+FactorCalculator+IC分析+分层回测+因子验证+相关性热力图。缺多因子组合研究 |
| 策略开发 | ★★★★☆ | 16策略+SignalComposer+参数优化+AI策略战法。V2编译器未完成 |
| 组合管理 | ★★★☆☆ | 4种分配模型+walk-forward+显式再平衡语义。缺真实持仓管理和再平衡交易 |
| 风险管理 | ★★★★☆ | 移动止损+熔断+凯利+闸门(6道规则)+风控策略。缺实时风险监控面板 |
| 回测验证 | ★★★★☆ | T+1成交+A股成本+基准指标+归因分析+复现清单。V2引擎只部分接入 |
| 研究报告 | ★★★☆☆ | 每日简报+绩效报告+估值快照+归因摘要。缺专业PDF/LaTeX输出 |
| 投资记录 | ★★★☆☆ | 交易日志+复盘笔记+信号记忆(alpha_memory)。缺策略决策记录链 |

---

## 四、软件工程审计

### 代码组织: ★★★☆☆
- **优点**: 模块分离清晰, V2有领域驱动设计
- **问题**: 两套架构共存(`src/`+`src/lxl_quantaxis/`), 功能重复, 调用路径不一致

### 模块耦合: ★★★☆☆
- **问题**: 策略库循环导入(已用懒加载修复), web_modern直接import所有src模块, 全局单例过多

### 异常处理: ★★☆☆☆
- **问题**: 大量`except Exception: pass`, 部分catch太宽, 错误日志不一致(print/logging混用)

### 日志: ★★☆☆☆
- **问题**: `print()`与`logging`混用, 无结构化日志, 无trace ID

### 配置: ★★★☆☆
- **优点**: 环境变量+YAML, SecuritySettings fail-closed
- **问题**: 硬编码路径`D:/trading_data/`, 配置分散在多处

### 测试覆盖: ★★★☆☆
- **优点**: 394测试, 覆盖核心回测+安全+合同+因子
- **问题**: 策略测试不足, Web路由测试只有部分, 集成测试少

### 部署: ★★☆☆☆
- **问题**: 无Docker, 无CI/CD pipeline, `pyproject.toml`不完整

### 安全: ★★★★☆
- **优点**: JWT无硬编码密钥, 默认127.0.0.1, AI无exec, 路由鉴权到位
- **问题**: 未设置CORS白名单, 无CSRF保护

### Technical Debt (优先级排序)
1. **P0**: 双架构导致维护成本翻倍, 需要合并路径
2. **P0**: `D:/trading_data/`硬编码, 应全部走环境变量
3. **P1**: `except Exception: pass` 散落各处, 静默吞错
4. **P1**: `print()`和`logging`混用, 无结构化日志
5. **P1**: 全局单例(config, stock_db, market_db...)阻碍测试隔离
6. **P2**: web_modern.py 3242行太胖, 需拆分为blueprint
7. **P2**: 无Docker, 环境复现困难
8. **P2**: `pyproject.toml`不完整, 缺少ruff/mypy/bandit配置

---

## 五、AI能力审计

### 当前AI可以做什么

| 能力 | 实现位置 | 状态 |
|------|----------|------|
| LLM对话 | `src/ai/engine.py` | ✅ 支持DeepSeek/OpenAI/Qwen |
| 策略工厂(进化) | `src/ai/factory.py` | ✅ AI分析→遗传进化→入银行 |
| 自然语言→策略 | `web_modern.py:/api/ai/create_strategy` | ✅ 描述思路→AI构建策略 |
| AI复盘 | `src/ai/assistants.py:AITradeReviewer` | ✅ 读交易日志→LLM复盘 |
| 市场简报 | `src/ai/assistants.py:AIMarketAnalyst` | ✅ 读数据→LLM简报 |
| 因子挖掘 | `src/ai/factor_miner.py` | ✅ 安全白名单(无exec) |
| 情绪分析 | `src/ai/sentiment.py` | ✅ 爬取+打分 |
| 护栏 | `src/lxl_quantaxis/ai/guardrails/` | ✅ schema校验 |
| V2编排 | `src/lxl_quantaxis/ai/orchestration/daily.py` | ✅ 每日流程 |

### 未来缺什么

1. **Prompt版本管理** — 硬编码在代码中, 修改需发版
2. **Token成本追踪** — 无用量和成本统计
3. **AI决策审计链** — 无user_id+model+prompt_version+timestamp记录
4. **多步Agent** — 当前只有单轮, 无多步推理+工具调用
5. **回测→AI→优化闭环** — V2有框架但未集成
6. **因子表达DSL** — 白名单只有9个算子, 表达能力有限

---

## 六、V2升级路线

### Phase 1: 清理与稳定 (1-2周)

| 目标 | 文件变化 | 风险 | 收益 |
|------|----------|------|------|
| 消除硬编码路径 | `config.py`, `web_modern.py`, 全部`D:/trading_data`引用 | 低 | 可移植性 |
| 统一日志 | 全部`print()`→`logging` | 低 | 可观测性 |
| 移除`except:pass` | 全局grep替换 | 低 | 可调试性 |
| 补CORS白名单 | `web_modern.py`, `security/settings.py` | 低 | 安全性 |
| 完善pyproject.toml | `pyproject.toml` | 低 | 标准化 |

### Phase 2: 架构合并 (2-3周)

| 目标 | 文件变化 | 风险 | 收益 |
|------|----------|------|------|
| 旧引擎→V2 event_loop | `backtest/engine.py`, `lxl_quantaxis/backtest/` | **高** | 单一引擎 |
| 旧因子→V2 factor pipeline | `factors/`, `lxl_quantaxis/factor/` | 中 | 统一因子流 |
| 旧策略→V2 strategy registry | `strategies/`, `lxl_quantaxis/strategy/` | 中 | 统一策略接口 |
| Web拆分为blueprint | `web_modern.py`→`api/routes/` | 中 | 可维护性 |
| 全局单例→依赖注入 | `config.py`, `data/`, `backtest/` | 中 | 可测试性 |

### Phase 3: 能力提升 (3-4周)

| 目标 | 文件变化 | 风险 | 收益 |
|------|----------|------|------|
| PIT数据语义 | `data/`, `lxl_quantaxis/data/` | 中 | 研究可信度 |
| AI多步Agent | `ai/`, `lxl_quantaxis/ai/orchestration/` | 中 | 自动化研究 |
| 专业报告生成 | `research/reports/`, `analysis/` | 低 | 专业输出 |
| Docker化 | `Dockerfile`, `docker-compose.yml` | 低 | 部署一致性 |
| CI/CD | `.github/workflows/` | 低 | 质量门禁 |
| 因子表达DSL扩展 | `factor_miner.py`, `guardrails/` | 中 | AI能力边界 |

---

## 七、当前优势总结

1. **回测引擎可靠** — T+1成交, 无前视偏差, A股真实成本
2. **安全设计良好** — JWT无硬编码密钥, 默认安全配置, AI无代码执行
3. **因子体系完整** — 28因子, IC分析, 分层回测, 相关性检测
4. **策略生态丰富** — 16策略, 信号组合器, 参数优化, AI策略战法
5. **测试覆盖坚实** — 394测试, 覆盖核心路径+安全+合同
6. **V2架构前瞻** — 领域驱动设计, 合约类型, 事件驱动回测, 安全护栏

## 八、关键风险

1. **双架构维护负担** — 每次改动可能需要在旧+V2两处实现
2. **单人项目** — 无团队协作基础设施(CI/CD/code review)
3. **数据依赖** — 强依赖akshare API稳定性, 无数据版本锁定
4. **Windows绑定** — 路径/编码/eventlet都假设Windows环境
