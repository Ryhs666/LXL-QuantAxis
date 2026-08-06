# LXL·QuantAxis V3 — 架构裁剪审查

> **个人金融科技作品项目 — 可落地性审查**  
> 原则：专业、可展示、但一个人能在合理时间内完成

**审查日期**: 2026-08-06  
**审查基准**: ARCHITECTURE_V3.md (26周/7阶段/150 commits 方案)  
**审查结论**: **严重过度设计。需裁剪 60%+ 范围才能落地。**

---

## 审查摘要

ARCHITECTURE_V3.md 设计的是一套**机构级多用户投研操作系统**——需要 3-5 人团队、12-18 个月工期。作为个人作品项目，核心问题：

| 问题 | 影响 |
|------|------|
| **Redis 事件总线** | 个人桌面应用不需要独立消息中间件 |
| **4 个标准 Agent + 编排器** | 每个 Agent 本身就是一个小项目 |
| **Point-in-Time 数据门户** | 需要历史成分股、财报发布日期、公司行为数据库——机构花几百万做的事 |
| **Barra 多因子风险模型** | 学术级别，个人投资者不需要 |
| **16 个独立数据库** | 维护噩梦——迁移、备份、一致性检查 |
| **RBAC 四角色** | 唯一用户就是你自己 |
| **Prometheus + Docker + CI/CD** | 作品集项目不需要生产级基础设施 |
| **7 种报告类型 × 4 种输出格式** | 每种组合都是独立工作量 |

**核心原则校准**：

> V3 的正确目标不是"机构级操作系统"，而是**"能记住你研究过什么、告诉你判断对不对、帮你把研究组织得更好的个人量化投研工作台"**。

---

## 1. 保留功能（V3 MVP 必须实现）

### 1.1 Fundamental Intelligence（核心版）

**保留**，但大幅裁剪：

```
保留:
├── 财务报表获取（akshare）
│   ├── 利润表：营收、净利润、EPS
│   ├── 资产负债表：总资产、总负债、股东权益
│   └── 现金流量表：经营活动CF、自由现金流
│
├── 核心估值指标（历史序列）
│   ├── PE(TTM)、PB —— 含 5 年分位数
│   ├── ROE —— 含趋势
│   ├── 营收增速（YoY）
│   └── 净利润增速（YoY）
│
├── 行业分类（申万一级行业）
│   └── 行业内百分位排名（PE、ROE、增速）
│
└── 基本面因子桥接
    ├── pe_percentile_5y
    ├── pb_percentile_5y
    ├── roe_level
    ├── roe_trend_4q
    ├── revenue_growth_yy
    ├── earnings_growth_yy
    └── industry_relative_pe
    （共 7 个，非 16 个）

删除/延后:
✂  DuPont 分解 —— 延后 V4
✂  Altman Z-score —— 延后 V4
✂  宏观数据（CPI/PMI/M2/LPR）—— 延后 V4
✂  美股基本面 —— V3 只做 A 股
✂  另类数据（供应链/卫星/信用卡）—— 删除，不在范围
✂  分红/拆股/内部交易 —— 延后 V4
✂  分析师一致预期 —— 延后 V4
```

**文件清单**（4-6 个文件）：
```
src/lxl_quantaxis/fundamental/
├── __init__.py
├── contracts.py          # FundamentalSnapshot, FundamentalSeries
├── fetcher.py            # akshare 财报 + 指标获取
├── storage.py            # fundamental.db CRUD
├── factor_bridge.py      # 注册 7 个基本面因子
└── peer.py               # 行业对比
```

### 1.2 Investment Journal + Research Memory（合并版）

**保留核心功能**，但大幅简化数据模型：

```python
# 一张表替代原来的三张表（ResearchMemory + JournalEntry + MarketContext）

@dataclass(frozen=True, slots=True)
class MemoryEntry:
    """统一记忆条目 —— 论文、决策、观察、教训都是同一种东西"""
    entry_id: int
    entry_type: str          # "thesis" | "decision" | "observation" | "lesson"
    date: str
    title: str
    content: str             # Markdown

    # 可选关联
    symbols: list[str]       # 涉及标的
    tags: list[str]          # 标签
    related_id: int | None   # 关联另一条记忆

    # 论文专属（entry_type=thesis 时有效）
    conviction: float | None          # 0.0–1.0
    pipeline_snapshot: dict | None    # factor_model + strategy_spec + backtest_result 的 JSON
    report_path: str | None

    # 结果追踪
    outcome_status: str | None   # "pending" | "correct" | "wrong" | "expired"
    outcome_notes: str | None
    reviewed_at: str | None

    created_at: str
```

**为什么合并？**
- 个人用户不需要把"论文记忆""决策日志""市场快照"拆成三张表
- 一张表 + `entry_type` 枚举 = 同样的查询能力，1/3 的代码量
- SQLite FTS5 全文搜索一张表即可

**数据库**: `lxl_v3.db`（1 个数据库，非 3 个），包含 `memory_entries` 表。

### 1.3 Web Workspace（统一 Shell）

**保留**，但简化页面数量：

```
V3 MVP 页面（5 页，非 12 页）:

├── /                     Landing → 重定向到 /workspace
├── /workspace            ★ 核心页面：项目总览 + 快捷操作
│                          ├── 项目列表（create/archive）
│                          ├── 最近论文时间线
│                          ├── 记忆分析卡片（hit rate, 最近教训）
│                          └── 快捷入口：写论文、跑管线、写日志
│
├── /pipeline             V2 AI 研究管线（已有，增加基本面上下文展示）
│
├── /journal              ★ 核心页面：记忆日记
│                          ├── 日历视图
│                          ├── 条目列表（筛选：类型、标的、标签）
│                          ├── 新建/编辑条目
│                          └── 全文搜索
│
├── /fundamental          ★ 核心页面：基本面浏览器
│                          ├── 股票搜索
│                          ├── 指标卡片（PE/PB/ROE/增速）
│                          ├── 历史趋势图
│                          └── 行业对比表
│
└── /portfolio            投资组合仪表盘（V2 已有，保持）
```

**删除/合并的页面**：
- `/agents` → 删除（V3 MVP 无 Agent）
- `/backtest` → 合并到 `/workspace` 的快捷回测面板
- `/reports` → 合并到项目详情页
- `/memory` → 合并到 `/journal`（同一概念）
- `/admin` → 删除（单用户）

**技术选型**：HTMX + Alpine.js。不引入 React。

### 1.4 Report Generation（精简版）

**保留**，但缩减为 3 种类型 × 2 种格式：

| 报告类型 | 格式 | 目标 |
|----------|------|------|
| **Investment Brief** (2-3 页) | HTML + Markdown | 快速决策支持 |
| **Research Report** (10-15 页) | HTML + Markdown | 完整研究输出 |
| **Daily Brief** (1 页，自动生成) | HTML | 每日收盘总结 |

```
删除:
✂  Institutional Report 25+ 页 —— 过于学术，个人不需要
✂  PDF 渲染（WeasyPrint/Puppeteer）—— HTML 在浏览器打印即可
✂  Excel 导出 —— Markdown 表格可复制到 Excel
✂  Email 分发 —— 个人项目不需要
✂  8 种模板组件 —— V3 MVP 用 4 种：metric_tile, comparison_table, price_chart, callout
```

### 1.5 V2 Quant Kernel（零改动）

完全保持现有 V2 引擎不变：
- 28 因子 + 16 策略 + 回测引擎 + 投资组合分析
- DSL 编译器 + 安全验证
- AI 研究管线（7 阶段）
- 所有现有 API

---

## 2. 延后功能（V4/V5）

| 功能 | 延后原因 | 建议版本 |
|------|----------|----------|
| **Research Agent Framework** | 需等 Journal Memory 积累足够数据后才能评估 Agent 质量 | V4 |
| **Alpha Agent（自动选股）** | 可简化为定时因子扫描（无 AI），Agent 版本延后 | V4 |
| **Sentiment Agent** | 新闻 NLP 是独立领域，需要稳定的数据源 | V5 |
| **Point-in-Time 数据门户** | 正确实现 PIT 需要历史成分股 + 报告日期数据库，远超个人项目范围 | V4 (简化版) |
| **多资产回测（组合回测）** | V2 单资产回测 + 手动组合分析已满足个人需求 | V4 |
| **Barra 风险模型** | 个人投资者不需要多因子风险分解 | V5 |
| **贝叶斯/遗传算法优化** | V2 网格搜索 + Walk-Forward 已足够 | V4 |
| **宏观数据（CPI/PMI/M2）** | 数据源稳定但分析框架复杂 | V4 |
| **美股/港股基本面** | A 股优先（akshare 数据最全），多市场延后 | V4 |
| **FastAPI 迁移** | Flask 工作正常，无强驱动力迁移 | V4 |
| **PDF 渲染** | HTML 浏览器打印 = 零开发成本 | V4 |
| **Redis** | 单用户不需要独立消息中间件 | V4 (仅在需要实时推送时) |
| **多用户 / RBAC** | 个人工具 = 单用户 | V5+（或不实现） |

---

## 3. 删除功能

以下功能**确定删除**，不进入任何版本规划：

| 功能 | 删除理由 |
|------|----------|
| **Custom Agent DSL (AgentSpec YAML)** | 为一个人设计"自定义 Agent 配置语言"是无意义的抽象 |
| **Agent 冲突检测与投票解决** | 没有多 Agent 就没有冲突 |
| **Almgren-Chriss 市场冲击模型** | 个人投资者交易量不会产生市场冲击 |
| **Greeks 计算器（期权）** | 项目不做期权 |
| **Protocol Buffers 序列化** | JSON 对个人数据量足够 |
| **Brinson 归因分析** | 机构级绩效归因，个人不需要 |
| **7 年审计日志留存** | 个人工具，不需要合规留存 |
| **SQLCipher 静态加密** | 个人本地数据，操作系统全盘加密已足够 |
| **OAuth2 / SSO** | 单用户不需要联合登录 |
| **Prometheus metrics 端点** | 个人工具不需要可观测性基础设施 |
| **Docker 部署** | `python web_modern.py` 即可 |
| **Email 报告分发** | 浏览器查看即可 |

---

## 4. MVP 开发路线（8 周，4 阶段）

```
┌─────────────────────────────────────────────────────────┐
│               V3 MVP: 8 周 · 4 阶段 · ~50 commits        │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Phase 1: 基本面智能（Week 1-2）                          │
│  ├── fundamental/fetcher.py    akshare 财报数据拉取       │
│  ├── fundamental/storage.py    fundamental.db            │
│  ├── fundamental/peer.py       申万行业分类 + 同行对比     │
│  ├── fundamental/factor_bridge.py   7 个基本面因子        │
│  └── web: /fundamental 页面                              │
│                                                          │
│  Phase 2: 投资记忆系统（Week 3-4）                        │
│  ├── journal/models.py         MemoryEntry 数据模型       │
│  ├── journal/repository.py     lxl_v3.db CRUD + FTS5     │
│  ├── journal/analytics.py      命中率/信心校准            │
│  ├── pipeline integration      管线结果自动写入记忆        │
│  └── web: /journal 页面（日历+搜索+编辑）                  │
│                                                          │
│  Phase 3: 报告 + 工作台（Week 5-6）                       │
│  ├── report/generator.py       报告生成器                  │
│  ├── report/types/             Brief + Research + Daily   │
│  ├── templates/reports/        HTML + MD 模板             │
│  ├── web: /workspace 页面（统一 Shell）                   │
│  └── 现有页面 CSS 统一（terminal.css 设计系统）            │
│                                                          │
│  Phase 4: 打磨 + 集成测试（Week 7-8）                     │
│  ├── 端到端测试                                          │
│  ├── 文档更新（README/USER_GUIDE/ARCHITECTURE）           │
│  ├── 展示录屏 + 截图                                      │
│  └── v3.0.0 release                                      │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**每个 Phase 可独立展示**：
- Phase 1 完成 → 展示"量化+基本面融合"
- Phase 2 完成 → 展示"能记住研究的AI系统"
- Phase 3 完成 → 展示"专业投研工作台"
- Phase 4 完成 → 完整作品集

---

## 5. 数据库最小设计

### 5.1 数据库合并策略

```
ARCHITECTURE_V3.md 设计: 18 个数据库
V3 MVP 设计:           5 个数据库（新增 1 个 + 复用 V2 4 个）
```

| 数据库 | 用途 | 来源 |
|--------|------|------|
| `lxl_v3.db` | **唯一的 V3 新数据库**：记忆条目 + 基本面缓存 | **新建** |
| `trades.db` | 交易记录 | V2 已有 |
| `backtest_results.db` | 回测结果 | V2 已有 |
| `research_notes.db` | 研究笔记 | V2 已有 |
| `market_cache/` | 行情 CSV 缓存 | V2 已有 |

其他 14 个 V2 数据库保持不动——既不改也不删。

### 5.2 `lxl_v3.db` Schema（唯一新数据库）

```sql
-- ============================================================
-- lxl_v3.db: V3 唯一新数据库
-- 合并了 ARCHITECTURE_V3.md 中的:
--   investment_memory.db + fundamental.db +
--   macro_series.db + agent_state.db + audit_trail.db
-- ============================================================

-- 1. 统一记忆表（替代 research_memory + journal_entries + market_contexts）
CREATE TABLE memory_entries (
    entry_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_type   TEXT NOT NULL CHECK(entry_type IN (
                    'thesis','decision','observation','lesson','daily_note'
                 )),
    date         TEXT NOT NULL,
    title        TEXT NOT NULL,
    content      TEXT NOT NULL,          -- Markdown body

    -- 关联（都是可选的）
    symbols      TEXT DEFAULT '[]',      -- JSON array, e.g. '["000858","600519"]'
    tags         TEXT DEFAULT '[]',      -- JSON array, e.g. '["消费","白酒"]'
    project_id   TEXT,                   -- 项目分组（可选，V4 扩展项目系统用）
    related_id   INTEGER,                -- 关联另一条记忆

    -- 论文专属字段（entry_type='thesis' 时填充）
    conviction        REAL,              -- 0.0–1.0
    pipeline_snapshot TEXT,              -- JSON: {parsed_thesis, factor_model, ...}
    report_path       TEXT,              -- 生成报告的文件路径

    -- 结果追踪
    outcome_status    TEXT DEFAULT 'pending',  -- pending|correct|wrong|expired
    outcome_notes     TEXT,
    reviewed_at       TEXT,

    created_at   TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at   TEXT
);

-- 索引
CREATE INDEX idx_memory_type   ON memory_entries(entry_type);
CREATE INDEX idx_memory_date   ON memory_entries(date);
CREATE INDEX idx_memory_outcome ON memory_entries(outcome_status);
CREATE INDEX idx_memory_project ON memory_entries(project_id);

-- 全文搜索（FTS5）
CREATE VIRTUAL TABLE memory_fts USING fts5(
    title, content, tags, symbols,
    content='memory_entries', content_rowid='rowid'
);


-- 2. 基本面快照表
CREATE TABLE fundamental_snapshots (
    symbol       TEXT NOT NULL,
    report_date  TEXT NOT NULL,          -- 报告期，如 "2024-12-31"

    -- 核心指标
    pe_ttm             REAL,
    pb                 REAL,
    roe_ttm            REAL,
    revenue_yoy        REAL,             -- 营收同比增速
    earnings_yoy       REAL,             -- 净利润同比增速
    gross_margin       REAL,
    net_margin         REAL,
    debt_to_equity     REAL,

    -- 行情快照（报告期的股价和市值）
    close_price        REAL,
    market_cap         REAL,             -- 亿元

    -- 行业
    industry_sw        TEXT,             -- 申万一级行业

    created_at   TEXT NOT NULL DEFAULT (datetime('now','localtime')),

    PRIMARY KEY (symbol, report_date)
);

CREATE INDEX idx_fundamental_industry ON fundamental_snapshots(industry_sw);


-- 3. 基本面时序表（画趋势图用）
CREATE TABLE fundamental_series (
    symbol     TEXT NOT NULL,
    indicator  TEXT NOT NULL,            -- "pe_ttm"|"pb"|"roe_ttm"|"revenue_yoy"|...
    date       TEXT NOT NULL,
    value      REAL NOT NULL,

    PRIMARY KEY (symbol, indicator, date)
);
```

**对比原设计的缩减**：

| 原设计 | V3 MVP |
|--------|--------|
| `research_memory` 表（17 列 + 6 索引） | |
| `journal_entries` 表（17 列 + 6 索引） | → `memory_entries` 1 张表 |
| `market_contexts` 表（17 列 + 1 索引） | |
| `fundamental_snapshots` 表 | → 保留，但列数从 15 减到 11 |
| `fundamental_series` 表 | → 保留，不变 |
| `macro_series` 表 | ✂ 删除（V4） |
| `agent_state` 表 | ✂ 删除 |
| `audit_trail` 表 | ✂ 删除（用 Python logging 替代） |
| `scheduled_jobs` 表 | ✂ 删除（用 APScheduler 内存调度） |
| `report_archive` 表 | ✂ 删除（报告存文件系统） |
| `pit_data` 表 | ✂ 删除（V4） |
| **10 张新表** | **3 张新表** |

---

## 6. 第一阶段代码目录结构

```
src/lxl_quantaxis/
│
├── fundamental/                    # ★ NEW: Phase 1
│   ├── __init__.py
│   ├── contracts.py                # FundamentalSnapshot, FundamentalSeries
│   ├── fetcher.py                  # akshare 财报拉取
│   ├── storage.py                  # fundamental_snapshots/series CRUD
│   ├── peer.py                     # 申万行业分类 + 同行百分位
│   └── factor_bridge.py            # 7 个基本面因子注册
│
├── journal/                        # ★ NEW: Phase 2
│   ├── __init__.py
│   ├── models.py                   # MemoryEntry (frozen dataclass)
│   ├── repository.py               # lxl_v3.db CRUD + FTS5 搜索
│   └── analytics.py                # 命中率 / 信心校准 / 标签统计
│
├── report/                         # ★ NEW: Phase 3 (精简)
│   ├── __init__.py
│   ├── generator.py                # ReportGenerator: 统一入口
│   ├── types/
│   │   ├── __init__.py
│   │   ├── brief.py                # InvestmentBrief (2-3p)
│   │   ├── research.py             # ResearchReport (10-15p)
│   │   └── daily.py                # DailyBrief (1p)
│   └── templates/                  # Jinja2 模板（可放 templates/ 目录）
│
├── (以下 V2 模块保持不动)
│   ├── core/            # 不变
│   ├── factor/          # 不变（factor_bridge 追加注册新因子）
│   ├── strategy/        # 不变
│   ├── backtest/        # 不变
│   ├── research/        # 不变（管线末尾增加 memory 写入钩子）
│   ├── portfolio/       # 不变
│   ├── ai/              # 不变
│   ├── data/            # 不变
│   ├── api/             # 不变（追加少量 V3 路由）
│   ├── memory/          # 不变（V2 memory 模块继续工作）
│   ├── execution/       # 不变
│   ├── risk/            # 不变
│   ├── ops/             # 不变
│   └── dashboard/       # 不变
│
templates/                          # Web 模板
│   ├── landing.html                # (V2 已有，保持)
│   ├── terminal.html               # (V2 已有，保持)
│   ├── pipeline.html               # (V2 已有，保持)
│   ├── portfolio.html              # (V2 已有，保持)
│   ├── cases.html                  # (V2 已有，保持)
│   ├── workspace.html              # ★ NEW: 统一工作台
│   ├── journal.html                # ★ NEW: 记忆日记
│   ├── fundamental.html            # ★ NEW: 基本面浏览器
│   └── reports/                    # ★ NEW: 报告模板
│       ├── brief.html.jinja2
│       ├── research.html.jinja2
│       └── daily.html.jinja2
│
static/
│   ├── echarts.min.js              # (V2 已有)
│   ├── professional.css            # (V2 已有)
│   └── css/
│       └── terminal.css            # (V2 已有，V3 页面全部复用)
│
tests/
│   ├── test_fundamental.py         # ★ NEW
│   ├── test_journal.py             # ★ NEW
│   └── test_report.py              # ★ NEW
│   └── (所有已有测试保持)
│
docs/
│   ├── ARCHITECTURE_V3.md          # V3 完整架构设计（参考文档）
│   ├── ARCHITECTURE_V3_SCOPING.md  # ★ 本文档：裁剪审查
│   └── (所有已有文档保持)
│
lxl_v3.db                           # ★ NEW: V3 唯一新数据库（自动创建）
```

**文件增量**：
- 新增 Python 文件：~15 个（fundamental 6 + journal 3 + report 6）
- 新增 HTML 模板：~6 个（workspace + journal + fundamental + 3 报告模板）
- 新增测试文件：~3 个
- 修改现有文件：~5 个（web_modern.py 增加路由、research 管线增加 memory 钩子、factor registry 增加基本面因子、requirements.txt 等）
- **总增量：~30 个文件，~3000 行代码**

**对比原设计的增量**：
- ARCHITECTURE_V3.md 设计：~80 个新 Python 文件 + ~30 个模板 + ~20 个测试文件
- 裁剪后：**减少 70% 文件量**

---

## 7. 与 V2 的集成策略

不创建 `/api/v3/`。直接在 V2 的 `web_modern.py` 上增加路由：

```python
# web_modern.py 新增路由（~200 行代码）

# === V3 页面路由 ===
@app.route("/workspace")
@token_required
def workspace_page():
    """统一工作台 —— V3 核心页面"""
    ...

@app.route("/journal")
@token_required
def journal_page():
    """记忆日记 —— V3 核心页面"""
    ...

@app.route("/fundamental")
@token_required
def fundamental_page():
    """基本面浏览器"""
    ...

# === V3 API 路由（数据接口）===
@app.route("/api/journal/list")
@token_required
def api_journal_list():
    """记忆条目列表（支持筛选、搜索）"""
    ...

@app.route("/api/journal/create", methods=["POST"])
@token_required
def api_journal_create():
    """创建记忆条目"""
    ...

@app.route("/api/journal/<int:entry_id>")
@token_required
def api_journal_detail(entry_id):
    """记忆条目详情"""
    ...

@app.route("/api/fundamental/<symbol>")
@token_required
def api_fundamental_snapshot(symbol):
    """基本面快照"""
    ...

@app.route("/api/fundamental/<symbol>/series")
@token_required
def api_fundamental_series(symbol):
    """基本面历史序列"""
    ...

@app.route("/api/fundamental/<symbol>/peers")
@token_required
def api_fundamental_peers(symbol):
    """同行对比"""
    ...

@app.route("/api/report/generate", methods=["POST"])
@token_required
def api_report_generate():
    """生成报告"""
    ...
```

**不引入 FastAPI**。Flask 继续工作。FastAPI 迁移是 V4 的事。

---

## 8. 架构对比：设计 vs 落地

| 维度 | ARCHITECTURE_V3.md 设计 | V3 MVP 裁剪后 |
|------|------------------------|---------------|
| **工期** | 26 周 | **8 周** |
| **提交数** | ~150 commits | **~50 commits** |
| **新 Python 文件** | ~80 个 | **~15 个** |
| **新 HTML 模板** | ~25 个 | **~6 个** |
| **新数据库** | 8 个 | **1 个** |
| **新数据库表** | ~15 张 | **3 张** |
| **Agent 数量** | 4 标准 + 自定义系统 | **0**（V4 再说） |
| **报告类型** | 7 种 | **3 种** |
| **输出格式** | 5 种（MD/HTML/PDF/JSON/Excel） | **2 种**（HTML + MD） |
| **Web 页面** | 12 页 | **5 页**（3 新 + 2 已有改版） |
| **API 版本** | /api/v3/ 全新 | **V2 路由增量** |
| **中间件依赖** | Redis + FastAPI + Prometheus | **0 新增依赖** |
| **基本面因子** | 16 个 | **7 个** |
| **支持市场** | A 股 + 港股 + 美股 | **A 股** |
| **用户模型** | 4 角色 RBAC | **单用户** |
| **基础设施** | Docker/Prometheus/CI | **无新增** |

---

## 9. 原则声明

1. **一个人能做完的才叫 MVP。** 26 周计划 = 做不完 = 没有作品集。
2. **V2 代码是资产，不是负债。** 不要重写，不要迁移，在上面叠加。
3. **少就是多。** 3 个功能做到极致 > 15 个功能做到 60%。
4. **每个 Phase 都能独立展示。** Phase 1 做完就能部署上线，不需要等 Phase 4。
5. **数据库越少越好。** 1 个新数据库 > 8 个。
6. **Flask 不坏不换。** FastAPI 迁移是零价值工作量。
7. **Agent 是 V4 的事。** 先有记忆，再谈智能。没有记忆的 Agent 只是个随机数生成器。

---

> **结论：ARCHITECTURE_V3.md 作为长期愿景保留。实际开发按本文档执行。**  
> **下一步：按 Phase 1 开始 Fundamental Intelligence 实现。**
