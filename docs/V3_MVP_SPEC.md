# LXL·QuantAxis V3.0 MVP — 冻结规格文档

> **AI Investment Research Operating System — Personal Edition**  
> 8 周 · 单人开发 · 零新基础设施 · 纯增量叠加

**Status**: FROZEN — 实施基准  
**Base**: v2.0.0-showcase  
**Target**: v3.0.0-mvp  
**Spec Version**: 1.0  
**Date**: 2026-08-06

---

## 目录

1. [产品目标与范围](#1-产品目标与范围)
2. [明确不做功能](#2-明确不做功能)
3. [Fundamental Intelligence](#3-fundamental-intelligence)
4. [Memory System](#4-memory-system)
5. [Workspace 设计](#5-workspace-设计)
6. [Report Generator](#6-report-generator)
7. [数据库 Schema](#7-数据库-schema)
8. [文件目录结构](#8-文件目录结构)
9. [Commit Roadmap](#9-commit-roadmap)
10. [验收标准](#10-验收标准)

---

## 1. 产品目标与范围

### 1.1 V3 一句话定位

> 能记住你研究过什么、告诉你判断对不对、把研究组织得更好的 **个人量化投研工作台**。

### 1.2 V2 → V3 核心变化

```
V2:  "把投资想法转化为回测报告。"（单次、无状态）
V3:  "持续积累研究记忆、追踪判断准确率、用基本面增强因子体系。"（持久、可回顾）
```

### 1.3 V3 三个新能力

| # | 能力 | 一句话 | 用户感知 |
|---|------|--------|----------|
| 1 | **Fundamental Intelligence** | 财报数据 + 行业对比 | "PE 在历史什么位置？ROE 比同行高还是低？" |
| 2 | **Memory System** | 论文→记忆→结果追踪 | "我三个月前看好的那个标的，现在回头看对不对？" |
| 3 | **Workspace + Reports** | 统一工作台 + 专业报告 | "不用在 9 个页面之间跳来跳去。" |

### 1.4 用户场景

```
场景 A: 收盘后复盘
  打开 /workspace → 看到今天的 Daily Brief → 在 /journal 写一条 observation
  → 看到上周的 thesis 需要 review → 标记 outcome → 系统更新 hit rate

场景 B: 研究新标的
  打开 /workspace → 创建新 Project → 写 investment thesis 自然语言
  → 跑 7-stage pipeline → 在 /fundamental 看 PE/ROE 历史
  → pipeline 结果自动写入 Memory → 生成 Research Report

场景 C: 回顾历史判断
  打开 /journal → 搜索 "消费" → 看到 3 条 thesis + 2 条 decision
  → 筛选 outcome_status=pending → 逐条 review → 标记 correct/wrong
  → /workspace 的 Memory Analytics 卡片更新
```

### 1.5 架构原则

| # | 原则 | 含义 |
|---|------|------|
| P1 | **V2 零改动** | 不改 V2 任何一行代码；只做增量导入 |
| P2 | **无新基础设施** | 不加 Redis、FastAPI、Docker、消息队列 |
| P3 | **单数据库增量** | 只新建 1 个 `lxl_v3.db`，3 张表 |
| P4 | **Flask only** | 路由直接加在 `web_modern.py` 上 |
| P5 | **单用户** | 无 RBAC、无多租户、无权限系统 |
| P6 | **每 Phase 可独立部署** | Phase 1 做完就能用，不等 Phase 4 |
| P7 | **先有记忆，后有智能** | V3 做 Memory；Agent 是 V4 的事 |

---

## 2. 明确不做功能

以下功能**明确排除**在 V3 MVP 之外。不实现、不预留、不设计接口。

### 2.1 基础设施类

| 不做 | 理由 |
|------|------|
| FastAPI 迁移 | Flask 工作正常，零价值迁移 |
| Redis 事件总线 | 单用户不需要消息中间件 |
| Docker 容器化 | `python web_modern.py` 即可 |
| Prometheus metrics | 个人工具不需要可观测性平台 |
| CI/CD Pipeline 变更 | 现有 GitHub Actions 足够 |

### 2.2 Agent 类

| 不做 | 理由 |
|------|------|
| Alpha Agent（自动选股） | 没有记忆的 Agent = 随机数生成器 |
| Risk Agent（组合监控） | V2 已有 risk 模块，够用 |
| Fundamental Agent（深度分析） | 基本面数据先入库，Agent 是 V4 |
| Sentiment Agent（情绪分析） | 需要稳定新闻数据源，V5 |
| Custom Agent DSL | 单人不需要自定义 Agent 框架 |
| Agent Orchestrator | 没有多 Agent 就没有编排 |
| Agent 冲突检测 | 同上 |

### 2.3 回测类

| 不做 | 理由 |
|------|------|
| Point-in-Time 数据门户 | 需要历史成分股数据库，远超个人范围 |
| 多资产组合回测 | V2 单资产 + 手动组合分析够用 |
| Barra 多因子风险模型 | 学术级，个人不需要 |
| 贝叶斯/遗传算法优化 | V2 网格搜索 + Walk-Forward 够用 |
| Almgren-Chriss 市场冲击 | 个人交易量不产生市场冲击 |
| 期权 Greeks | 项目不做期权 |
| 公司行为处理 | V4 |

### 2.4 数据类

| 不做 | 理由 |
|------|------|
| 美股/港股基本面 | V3 只做 A 股 |
| 宏观数据（CPI/PMI/M2/LPR） | V4 |
| 另类数据（供应链/卫星/信用卡） | 永远不做 |
| 分析师一致预期 | V4 |
| 分红/拆股/内部交易 | V4 |

### 2.5 报告类

| 不做 | 理由 |
|------|------|
| PDF 渲染 | 浏览器打印 = 零开发成本 |
| Excel 导出 | Markdown 表格可复制 |
| Email 分发 | 个人项目不需要 |
| 25+ 页机构报告 | V4 — V3 做 10-15 页版本 |
| Protocol Buffers 序列化 | JSON 够用 |

### 2.6 用户系统类

| 不做 | 理由 |
|------|------|
| RBAC 多角色 | 单用户 |
| OAuth2/SSO | 单用户 |
| 7 年审计日志 | 个人工具 |
| SQLCipher 加密 | OS 全盘加密已足够 |

---

## 3. Fundamental Intelligence

### 3.1 模块定位

让量化策略能看到**公司基本面**——不只是价格和成交量，还有 PE、ROE、营收增速。

### 3.2 数据获取

**数据源**: akshare（免费、覆盖 A 股全部财报数据）

**获取内容**:

| 接口 | akshare 函数 | 获取字段 | 频率 |
|------|-------------|----------|------|
| 利润表 | `stock_financial_abstract_ths` | 营收、净利润、EPS | 季度 |
| 资产负债表 | `stock_financial_abstract_ths` | 总资产、总负债、股东权益 | 季度 |
| 现金流量表 | `stock_financial_abstract_ths` | 经营活动CF、FCF | 季度 |
| 估值指标 | `stock_a_lg_indicator` | PE-TTM、PB | 每日 |
| 行业分类 | `stock_board_concept_cons_ths` | 申万一级行业 | 静态 |
| 行业估值 | `stock_board_industry_pe_ths` | 行业平均 PE | 每日 |

**缓存策略**:
- 财报数据：季度更新，本地缓存到 `fundamental_snapshots` 表
- 估值指标：每日更新，本地缓存到 `fundamental_series` 表
- 行业分类：首次获取后永久缓存

### 3.3 数据模型

```python
# src/lxl_quantaxis/fundamental/contracts.py

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FundamentalSnapshot:
    """单季度/单日的基本面快照"""
    symbol: str              # 股票代码，如 "000858"
    report_date: str         # 报告期，如 "2024-12-31" 或交易日 "2026-08-06"

    # 估值
    pe_ttm: float | None
    pb: float | None

    # 盈利能力
    roe_ttm: float | None
    gross_margin: float | None
    net_margin: float | None

    # 增长
    revenue_yoy: float | None      # 营收同比增速，如 0.15 = +15%
    earnings_yoy: float | None     # 净利润同比增速

    # 财务健康
    debt_to_equity: float | None   # 资产负债率

    # 行情
    close_price: float | None
    market_cap: float | None       # 亿元

    # 行业
    industry_sw: str | None        # 申万一级行业，如 "食品饮料"


@dataclass(frozen=True, slots=True)
class FundamentalSeries:
    """某个指标的历史时序"""
    symbol: str              # 股票代码
    indicator: str           # "pe_ttm" | "pb" | "roe_ttm" | "revenue_yoy" | "earnings_yoy" | "gross_margin" | "net_margin"
    dates: list[str]         # 日期序列
    values: list[float]      # 值序列


@dataclass(frozen=True, slots=True)
class PeerContext:
    """行业同行对比上下文"""
    symbol: str
    industry_sw: str
    peer_count: int          # 同行业股票数量

    # 该股票在行业内的百分位（0-100，越高越好）
    pe_percentile: float     # PE 分位数（0=最便宜，100=最贵）
    roe_percentile: float    # ROE 分位数（0=最低，100=最高）
    growth_percentile: float # 营收增速分位数
```

### 3.4 Python API

```python
# 使用示例

from lxl_quantaxis.fundamental.fetcher import FundamentalFetcher
from lxl_quantaxis.fundamental.storage import FundamentalStorage
from lxl_quantaxis.fundamental.peer import PeerAnalyzer

# 1. 拉取并缓存基本面数据
fetcher = FundamentalFetcher()
snapshots = fetcher.fetch_financials("000858", years=5)  # 最近 5 年
for s in snapshots:
    FundamentalStorage.upsert_snapshot(s)

# 2. 获取历史序列（用于画图）
series = FundamentalStorage.get_series("000858", "pe_ttm")
# → FundamentalSeries(dates=[...], values=[...])

# 3. 同行对比
analyzer = PeerAnalyzer()
context = analyzer.analyze("000858")
# → PeerContext(pe_percentile=65.2, roe_percentile=88.1, ...)
```

### 3.5 基本面因子桥接

注册 7 个新因子到现有 `FACTOR_REGISTRY`：

```python
# src/lxl_quantaxis/fundamental/factor_bridge.py

FUNDAMENTAL_FACTORS = {
    "pe_percentile_5y": {
        "name": "PE 历史分位数",
        "category": "valuation",
        "description": "当前 PE-TTM 在最近 5 年的百分位位置。0=历史最便宜，1=历史最贵",
        "output_range": (0, 1),
        "update_freq": "daily",
    },
    "pb_percentile_5y": {
        "name": "PB 历史分位数",
        "category": "valuation",
        "description": "当前 PB 在最近 5 年的百分位位置",
        "output_range": (0, 1),
        "update_freq": "daily",
    },
    "roe_level": {
        "name": "ROE 水平",
        "category": "profitability",
        "description": "ROE-TTM，标准化到 0-1（0=亏损，0.5=10%，1=30%+）",
        "output_range": (0, 1),
        "update_freq": "quarterly",
    },
    "roe_trend_4q": {
        "name": "ROE 趋势",
        "category": "profitability",
        "description": "过去 4 个季度 ROE 的方向。0.5=持平，>0.5=上升，<0.5=下降",
        "output_range": (0, 1),
        "update_freq": "quarterly",
    },
    "revenue_growth_yy": {
        "name": "营收增速",
        "category": "growth",
        "description": "营收同比增长率，标准化到 0-1（0=负增长，0.5=持平，1=高增长）",
        "output_range": (0, 1),
        "update_freq": "quarterly",
    },
    "earnings_growth_yy": {
        "name": "盈利增速",
        "category": "growth",
        "description": "净利润同比增长率，标准化到 0-1",
        "output_range": (0, 1),
        "update_freq": "quarterly",
    },
    "industry_relative_pe": {
        "name": "行业相对 PE",
        "category": "relative",
        "description": "PE 在同行中的位置。0=行业最便宜，1=行业最贵",
        "output_range": (0, 1),
        "update_freq": "daily",
    },
}
```

### 3.6 Web 页面: `/fundamental`

```
┌─────────────────────────────────────────────────────────┐
│  [LXL·QuantAxis]  Workspace  Pipeline  Journal  Fundamental │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  股票代码: [000858________] [查询]                        │
│                                                          │
│  ┌──────────┬──────────┬──────────┬──────────┐          │
│  │ PE-TTM   │ PB       │ ROE      │ 营收增速  │          │
│  │  25.3    │  5.2     │ 24.8%   │ +15.3%   │          │
│  │ 分位:65% │ 分位:58% │ 行业:88%│ 行业:72% │          │
│  └──────────┴──────────┴──────────┴──────────┘          │
│                                                          │
│  ┌─────────────────────────────────────────┐            │
│  │         PE-TTM 历史趋势 (5年)             │            │
│  │  [Plotly 折线图: 当前值 vs 历史区间]       │            │
│  └─────────────────────────────────────────┘            │
│                                                          │
│  ┌─────────────────────────────────────────┐            │
│  │         同行对比                           │            │
│  │  行业: 食品饮料  |  同行: 47 家            │            │
│  │  指标         五粮液    行业中位数   排名   │            │
│  │  PE-TTM       25.3      32.1      18/47  │            │
│  │  ROE          24.8%     15.2%      5/47  │            │
│  │  营收增速      +15.3%    +8.7%     12/47 │            │
│  └─────────────────────────────────────────┘            │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### 3.7 文件清单

```
src/lxl_quantaxis/fundamental/
├── __init__.py           # 公开 API 导出
├── contracts.py          # FundamentalSnapshot, FundamentalSeries, PeerContext
├── fetcher.py            # FundamentalFetcher: akshare 数据拉取
├── storage.py            # FundamentalStorage: fundamental_snapshots/series CRUD
├── peer.py               # PeerAnalyzer: 申万行业分类 + 同行百分位
└── factor_bridge.py      # register_fundamental_factors(): 7 因子注册
```

---

## 4. Memory System

### 4.1 模块定位

V3 的**核心创新**。让系统能记住每一次研究、每一个决策、每一条教训——并追踪判断准确率。

### 4.2 统一记忆模型

一整张表替代传统三表设计（研究记忆 + 日记条目 + 市场快照）：

```python
# src/lxl_quantaxis/journal/models.py

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class MemoryEntry:
    """统一记忆条目。

    所有类型的记忆——论文、决策、观察、教训——都通过 entry_type 区分，
    共享同一套 CRUD 和搜索基础设施。
    """
    entry_id: int                    # 自增主键
    entry_type: str                  # "thesis" | "decision" | "observation" | "lesson" | "daily_note"
    date: str                        # ISO date "2026-08-06"
    title: str                       # 标题
    content: str                     # Markdown 正文

    # 可选关联
    symbols: list[str] = field(default_factory=list)   # ["000858", "600519"]
    tags: list[str] = field(default_factory=list)      # ["消费", "白酒", "价值"]
    project_id: str | None = None    # 项目分组
    related_id: int | None = None    # 关联另一条记忆

    # Thesis 专属字段（entry_type="thesis" 时填充）
    conviction: float | None = None           # 0.0–1.0
    pipeline_snapshot: dict | None = None     # {parsed_thesis, factor_model, strategy_spec, backtest_result, ai_assessment}
    report_path: str | None = None

    # 结果追踪
    outcome_status: str | None = None  # "pending" | "correct" | "wrong" | "expired"
    outcome_notes: str | None = None
    reviewed_at: str | None = None

    created_at: str = ""
    updated_at: str = ""


# entry_type 枚举及语义
ENTRY_TYPES = {
    "thesis":       "投资论文 — AI 管线输出，含 conviction + pipeline_snapshot + outcome 追踪",
    "decision":     "交易决策 — 买入/卖出/持有，含决策理由和事后结果",
    "observation":  "市场观察 — 宏观变化、行业轮动、公司公告等",
    "lesson":       "经验教训 — 犯过的错误、成功的模式、规则演进",
    "daily_note":   "每日笔记 — 自由格式的日记",
}
```

### 4.3 Python API

```python
# 使用示例

from lxl_quantaxis.journal.repository import MemoryRepository
from lxl_quantaxis.journal.analytics import MemoryAnalytics

repo = MemoryRepository("D:/trading_data/lxl_v3.db")

# === 写入 ===
# 1. 管线完成后自动写入论文记忆
entry = MemoryEntry(
    entry_type="thesis",
    date="2026-08-06",
    title="五粮液：消费复苏 + 估值修复",
    content="## 投资逻辑\n...",
    symbols=["000858"],
    tags=["消费", "白酒"],
    conviction=0.7,
    pipeline_snapshot={
        "parsed_thesis": {...},
        "factor_model": {...},
        "strategy_spec": {...},
        "backtest_result": {...},
        "ai_assessment": {...},
    },
    report_path="reports/000858_20260806.md",
)
repo.save(entry)

# 2. 手动写日志
repo.save(MemoryEntry(
    entry_type="observation",
    date="2026-08-06",
    title="白酒板块集体回调，成交量放大",
    content="## 观察\n...",
    symbols=["000858", "600519"],
    tags=["白酒", "回调"],
))

# === 查询 ===
# 全文搜索
results = repo.search("消费 白酒")  # FTS5

# 按类型筛选
theses = repo.find_by_type("thesis")

# 按标的筛选
all_000858 = repo.find_by_symbol("000858")

# 待 review 的论文
pending = repo.find_pending_reviews()  # outcome_status="pending"

# === 更新 ===
# Review 一条旧论文
repo.review(
    entry_id=5,
    outcome_status="correct",
    outcome_notes="目标价 180 元已到达，涨了 22%",
)

# === 分析 ===
analytics = MemoryAnalytics(repo)
stats = analytics.get_stats()
# → {
#     "total_entries": 47,
#     "thesis_count": 12,
#     "thesis_hit_rate": 0.58,        # 58% 正确
#     "high_conviction_hit_rate": 0.75,  # 高信心论文正确率
#     "decision_win_rate": 0.62,
#     "pending_reviews": 3,
#     "lessons_learned": 8,
#     "top_tags": ["消费", "科技", "白酒"],
#     "streak_days": 5,                 # 连续记录天数
# }
```

### 4.4 管线集成钩子

在 V2 的 7-stage pipeline 末尾增加一个**非侵入钩子**：

```python
# 在 research/application.py 的 EquityResearchService 中

def run_pipeline(self, thesis_text: str) -> ResearchReport:
    # ... V2 原有 7 个 stage 不变 ...

    # ★ V3 钩子：管线结果写入 Memory（静默，不影响管线）
    try:
        from lxl_quantaxis.journal.repository import MemoryRepository
        from lxl_quantaxis.journal.models import MemoryEntry

        entry = MemoryEntry(
            entry_type="thesis",
            date=datetime.now().strftime("%Y-%m-%d"),
            title=self._extract_title(parsed_thesis),
            content=thesis_text,
            symbols=[parsed_thesis.symbol],
            tags=self._extract_tags(parsed_thesis),
            conviction=parsed_thesis.confidence or 0.5,
            pipeline_snapshot={
                "parsed_thesis": dataclasses.asdict(parsed_thesis),
                "factor_model": dataclasses.asdict(factor_model),
                "strategy_spec": dataclasses.asdict(strategy_spec),
                "backtest_result": backtest_metrics,
                "ai_assessment": ai_assessment,
            },
            report_path=report_path,
        )
        MemoryRepository().save(entry)
    except Exception:
        pass  # 静默失败，不阻断管线

    return report
```

### 4.5 Web 页面: `/journal`

```
┌─────────────────────────────────────────────────────────┐
│  [LXL·QuantAxis]  Workspace  Pipeline  Journal  Fundamental │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  [+ New Entry]  [搜索: ____________]  [筛选: 全部▼]       │
│                                                          │
│  ┌─────────────────────────────────────────────────────┐ │
│  │  📅 August 2026                           ◀ ▶      │ │
│  │  Mo  Tu  We  Th  Fr  Sa  Su                         │ │
│  │  ...  ...  ●   ●   ●   ...  ...                      │ │
│  │        thesis daily                                 │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌─── Entries ───────────────────────────────────────┐  │
│  │                                                    │  │
│  │  💡 Thesis · 2026-08-06                            │  │
│  │  五粮液：消费复苏 + 估值修复                          │  │
│  │  000858 · conviction: 0.7 · pending review          │  │
│  │  tags: 消费 白酒                                     │  │
│  │                                                    │  │
│  │  📊 Observation · 2026-08-05                        │  │
│  │  白酒板块放量回调                                     │  │
│  │  000858 600519 · tags: 白酒 回调                     │  │
│  │                                                    │  │
│  │  ✅ Decision · 2026-08-01                           │  │
│  │  减仓五粮液 — 到达目标价                              │  │
│  │  outcome: good · P&L: +22%                          │  │
│  │                                                    │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### 4.6 文件清单

```
src/lxl_quantaxis/journal/
├── __init__.py           # 公开 API 导出
├── models.py             # MemoryEntry dataclass + ENTRY_TYPES
├── repository.py         # MemoryRepository: lxl_v3.db CRUD + FTS5
└── analytics.py          # MemoryAnalytics: hit_rate, calibration, tags
```

---

## 5. Workspace 设计

### 5.1 模块定位

统一工作台——替代 V2 的 9 个独立页面。不是新建一个复杂系统，而是在现有页面之上加一个**导航 Shell**。

### 5.2 设计原则

1. **Shell 模式**: 所有页面共享顶部导航栏
2. **渐进增强**: 现有页面（pipeline/portfolio/cases）嵌入 Shell 即可
3. **Dashboard 首页**: 一眼看到系统状态

### 5.3 页面结构

```
templates/workspace.html      ← 统一 Shell（导航 + 内容区）

导航栏:
  [LXL·QuantAxis V3]   Workspace · Pipeline · Journal · Fundamental · Portfolio

内容区（当前激活页面）:
  /workspace   → Dashboard 首页
  /pipeline    → AI 研究管线（V2 已有页面）
  /journal     → 记忆日记
  /fundamental → 基本面浏览器
  /portfolio   → 投资组合仪表盘（V2 已有页面）
```

### 5.4 Dashboard 首页设计 (`/workspace`)

```
┌─────────────────────────────────────────────────────────┐
│  [LXL·QuantAxis V3]  Workspace  Pipeline  Journal  ...    │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌─────────────┬─────────────┬─────────────┬──────────┐ │
│  │ 📝 论文总数  │ 🎯 命中率    │ ⏳ 待Review  │ 🔥 连续天数│ │
│  │    12       │   58%       │     3       │    5     │ │
│  └─────────────┴─────────────┴─────────────┴──────────┘ │
│                                                          │
│  ┌────────────────────┐  ┌────────────────────────────┐ │
│  │  快捷操作            │  │  最近论文                   │ │
│  │                    │  │                            │ │
│  │ [✏️ 写论文]         │  │  2026-08-06  五粮液 消费复苏 │ │
│  │ [🔬 跑管线]         │  │  2026-08-03  中芯国际 芯片周期│ │
│  │ [📝 写日志]         │  │  2026-07-28  茅台 防御配置   │ │
│  │ [📊 看报告]         │  │                            │ │
│  └────────────────────┘  └────────────────────────────┘ │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │  最近教训                                           │   │
│  │  💡 "追高买入导致最大回撤超过容忍度 — 等回调再进"      │   │
│  │  💡 "基本面恶化的票不要因为便宜就抄底"                  │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### 5.5 导航一致性

所有现有 V2 页面（pipeline、portfolio、cases、terminal、landing）增加统一顶部导航栏：

```html
<!-- 每个页面顶部插入 -->
<nav class="v3-nav">
    <a href="/workspace" class="nav-brand">LXL·QuantAxis V3</a>
    <div class="nav-links">
        <a href="/workspace">Workspace</a>
        <a href="/pipeline">Pipeline</a>
        <a href="/journal">Journal</a>
        <a href="/fundamental">Fundamental</a>
        <a href="/portfolio">Portfolio</a>
    </div>
</nav>
```

### 5.6 实现策略

**不改 V2 模板文件**。通过 Flask 的 `@app.context_processor` 注入导航栏 HTML：

```python
# web_modern.py

@app.context_processor
def inject_v3_nav():
    """V3: 向所有模板注入统一导航栏"""
    return {"v3_nav_html": render_nav_html()}

def render_nav_html():
    """生成 V3 导航栏 HTML"""
    return """
    <nav class="v3-nav">...</nav>
    """
```

### 5.7 文件清单

```
templates/
├── workspace.html          # ★ NEW: Dashboard 首页
├── journal.html            # ★ NEW: 记忆日记页面
├── fundamental.html        # ★ NEW: 基本面浏览器页面
├── landing.html            # (V2 已有，增加导航栏)
├── pipeline.html           # (V2 已有，增加导航栏)
├── portfolio.html          # (V2 已有，增加导航栏)
├── cases.html              # (V2 已有，增加导航栏)
├── terminal.html           # (V2 已有，增加导航栏)
├── ...                     # (其他 V2 模板不动)
│
static/css/
└── v3-nav.css              # ★ NEW: V3 导航栏样式（暗色主题，约 80 行 CSS）
```

---

## 6. Report Generator

### 6.1 模块定位

从 V2 的"一份 Markdown 报告"升级为**三种场景化报告**——但仍保持 Jinja2 + HTML/Markdown，不引入 PDF 引擎。

### 6.2 报告类型

#### 6.2.1 Investment Brief（投资速览，2-3 页）

**使用场景**: 快速决策参考。管线跑完后自动生成。

**内容结构**:
```yaml
sections:
  - header:
      stock: "五粮液 (000858.SZ)"
      recommendation: "买入"
      target_price: "¥180"
      conviction: 0.7
  - thesis_summary:    # 3 句话投资逻辑
  - catalysts:         # 近期催化剂（财报、政策、产品）
  - key_metrics:       # PE/PB/ROE/增速 当前 vs 历史分位
  - risk_matrix:       # Top 3 风险及应对
  - technical_snapshot: # 趋势/动量/支撑阻力
  - action_plan:       # 入场区间、仓位%、止损价
```

**输出格式**: HTML（浏览器查看）+ Markdown（文件保存）

#### 6.2.2 Research Report（研究报告，10-15 页）

**使用场景**: 完整研究存档。整合管线全部输出 + 基本面数据。

**内容结构**:
```yaml
sections:
  - cover:             # 封面页（标的、日期、评级）
  - executive_summary: # 一页摘要
  - investment_case:
      - thesis:        # 投资逻辑（来自 ai_parser）
      - catalysts:     # 催化剂时间线
  - factor_profile:    # 28 因子雷达图（来自 V2 factor_mapper）
  - strategy_detail:   # DSL 策略规则 + 回测绩效（来自 V2 backtest）
  - fundamental_view:  # 基本面数据（PE/ROE 趋势图、行业对比表）
  - valuation:         # 估值分析（PE 分位、行业分位）
  - risk_assessment:   # 风险评估（来自 V2 ai_assessment）
  - recommendation:    # 评级 + 仓位 + 操作计划
  - appendix:          # 数据来源 + 免责声明
```

**输出格式**: HTML（浏览器查看）+ Markdown（文件保存）

#### 6.2.3 Daily Brief（每日简报，1 页）

**使用场景**: 每日收盘自动生成。市场概览 + 组合快照。

**内容结构**:
```yaml
sections:
  - market_summary:    # 上证/沪深300/科创50 涨跌幅 + 成交量
  - sector_performance: # 今日行业涨跌榜
  - portfolio_snapshot: # 持仓 P&L
  - signal_today:      # 今日触发信号（如果有）
  - memory_reminder:   # 今天该 review 的论文列表
  - journal_prompt:    # 空白的日记模板（引导写复盘）
```

**生成方式**: 手动触发（点击 "Generate Daily Brief"），或 APScheduler 定时任务（可选）。

**输出格式**: HTML

### 6.3 技术实现

```python
# src/lxl_quantaxis/report/generator.py

class ReportGenerator:
    """V3 报告生成器"""

    def __init__(self, template_dir: str = "templates/reports"):
        self.env = Environment(loader=FileSystemLoader(template_dir))

    def generate_brief(
        self,
        thesis_data: dict,
        fundamental_data: dict,
        backtest_data: dict,
    ) -> str:
        """生成 Investment Brief (HTML)"""
        template = self.env.get_template("brief.html.jinja2")
        return template.render(
            thesis=thesis_data,
            fundamental=fundamental_data,
            backtest=backtest_data,
        )

    def generate_research_report(
        self,
        pipeline_data: dict,      # 管线全部输出
        fundamental_data: dict,   # 基本面数据
    ) -> str:
        """生成 Research Report (HTML)"""
        template = self.env.get_template("research.html.jinja2")
        return template.render(**pipeline_data, fundamental=fundamental_data)

    def generate_daily_brief(
        self,
        market_data: dict,
        portfolio_data: dict,
        pending_reviews: list,
    ) -> str:
        """生成 Daily Brief (HTML)"""
        template = self.env.get_template("daily.html.jinja2")
        return template.render(
            market=market_data,
            portfolio=portfolio_data,
            pending_reviews=pending_reviews,
        )
```

### 6.4 模板文件

```
templates/reports/
├── brief.html.jinja2         # Investment Brief 模板
├── research.html.jinja2      # Research Report 模板
└── daily.html.jinja2         # Daily Brief 模板
```

**复用 V2 样式**: 所有报告模板使用 `terminal.css` 暗色主题。

### 6.5 文件清单

```
src/lxl_quantaxis/report/
├── __init__.py           # 公开 API 导出
├── generator.py          # ReportGenerator: 统一入口
├── types/
│   ├── __init__.py
│   ├── brief.py          # generate_brief() 的数据组装逻辑
│   ├── research.py       # generate_research_report() 的数据组装逻辑
│   └── daily.py          # generate_daily_brief() 的数据组装逻辑
```

---

## 7. 数据库 Schema

### 7.1 数据库总览

| 数据库 | 用途 | 来源 | V3操作 |
|--------|------|------|--------|
| `lxl_v3.db` | **V3 唯一新数据库** | **新建** | 创建 |
| `trades.db` | 交易记录 | V2 已有 | 不动 |
| `backtest_results.db` | 回测结果 | V2 已有 | 不动 |
| `research_notes.db` | 研究笔记 | V2 已有 | 不动 |
| 其他 V2 数据库 | ... | V2 已有 | 不动 |

### 7.2 `lxl_v3.db` 完整 Schema

```sql
-- ============================================================
-- lxl_v3.db: V3 MVP 唯一新数据库
-- 位置: D:/trading_data/lxl_v3.db
-- 引擎: SQLite 3
-- ============================================================

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- -----------------------------------------------------------
-- 1. memory_entries: 统一记忆表
--   合并了论文记忆、决策日志、市场观察、经验教训、每日笔记
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS memory_entries (
    entry_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_type   TEXT    NOT NULL CHECK (entry_type IN (
                    'thesis', 'decision', 'observation', 'lesson', 'daily_note'
                 )),
    date         TEXT    NOT NULL,          -- ISO date "2026-08-06"
    title        TEXT    NOT NULL,
    content      TEXT    NOT NULL,          -- Markdown body

    -- 关联字段（全部可选）
    symbols      TEXT    NOT NULL DEFAULT '[]',   -- JSON array
    tags         TEXT    NOT NULL DEFAULT '[]',   -- JSON array
    project_id   TEXT,                           -- 项目分组标识
    related_id   INTEGER,                        -- FK → memory_entries.entry_id

    -- Thesis 专属字段（仅 entry_type='thesis' 时填充）
    conviction         REAL,                     -- 0.0–1.0
    pipeline_snapshot  TEXT,                     -- JSON blob
    report_path        TEXT,                     -- 生成报告的本地路径

    -- 结果追踪
    outcome_status     TEXT    DEFAULT 'pending',  -- pending | correct | wrong | expired
    outcome_notes      TEXT,
    reviewed_at        TEXT,

    -- 时间戳
    created_at   TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at   TEXT
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_memory_type    ON memory_entries(entry_type);
CREATE INDEX IF NOT EXISTS idx_memory_date    ON memory_entries(date);
CREATE INDEX IF NOT EXISTS idx_memory_outcome ON memory_entries(outcome_status);
CREATE INDEX IF NOT EXISTS idx_memory_related ON memory_entries(related_id);
CREATE INDEX IF NOT EXISTS idx_memory_project ON memory_entries(project_id);

-- 全文搜索
CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
    title,
    content,
    tags,
    symbols,
    content='memory_entries',
    content_rowid='rowid'
);

-- FTS 同步触发器
CREATE TRIGGER IF NOT EXISTS memory_ai AFTER INSERT ON memory_entries BEGIN
    INSERT INTO memory_fts(rowid, title, content, tags, symbols)
    VALUES (new.rowid, new.title, new.content, new.tags, new.symbols);
END;

CREATE TRIGGER IF NOT EXISTS memory_ad AFTER DELETE ON memory_entries BEGIN
    INSERT INTO memory_fts(memory_fts, rowid, title, content, tags, symbols)
    VALUES ('delete', old.rowid, old.title, old.content, old.tags, old.symbols);
END;

CREATE TRIGGER IF NOT EXISTS memory_au AFTER UPDATE ON memory_entries BEGIN
    INSERT INTO memory_fts(memory_fts, rowid, title, content, tags, symbols)
    VALUES ('delete', old.rowid, old.title, old.content, old.tags, old.symbols);
    INSERT INTO memory_fts(rowid, title, content, tags, symbols)
    VALUES (new.rowid, new.title, new.content, new.tags, new.symbols);
END;


-- -----------------------------------------------------------
-- 2. fundamental_snapshots: 基本面快照表
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS fundamental_snapshots (
    symbol          TEXT NOT NULL,
    report_date     TEXT NOT NULL,          -- 报告期 "2024-12-31"

    -- 估值
    pe_ttm          REAL,
    pb              REAL,

    -- 盈利
    roe_ttm         REAL,
    gross_margin    REAL,
    net_margin      REAL,

    -- 增长
    revenue_yoy     REAL,                   -- 如 0.153 表示 +15.3%
    earnings_yoy    REAL,

    -- 健康
    debt_to_equity  REAL,

    -- 行情
    close_price     REAL,
    market_cap      REAL,                   -- 亿元

    -- 行业
    industry_sw     TEXT,                   -- 申万一级行业

    created_at      TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),

    PRIMARY KEY (symbol, report_date)
);

CREATE INDEX IF NOT EXISTS idx_fs_industry ON fundamental_snapshots(industry_sw);
CREATE INDEX IF NOT EXISTS idx_fs_date     ON fundamental_snapshots(report_date);


-- -----------------------------------------------------------
-- 3. fundamental_series: 基本面时序表
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS fundamental_series (
    symbol     TEXT    NOT NULL,
    indicator  TEXT    NOT NULL,            -- pe_ttm | pb | roe_ttm | revenue_yoy | earnings_yoy | gross_margin | net_margin
    date       TEXT    NOT NULL,
    value      REAL    NOT NULL,

    PRIMARY KEY (symbol, indicator, date)
);

CREATE INDEX IF NOT EXISTS idx_fser_indicator ON fundamental_series(indicator);
```

### 7.3 数据库创建

```python
# src/lxl_quantaxis/journal/repository.py

import sqlite3
from pathlib import Path

class MemoryRepository:
    def __init__(self, db_path: str | None = None):
        if db_path is None:
            from lxl_quantaxis.core.config.settings import get_settings
            db_path = str(Path(get_settings().data_root) / "lxl_v3.db")
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """首次运行时创建所有表"""
        schema_path = Path(__file__).parent / "schema.sql"
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(schema_path.read_text())
            conn.commit()
```

---

## 8. 文件目录结构

### 8.1 新增文件（完整清单）

```
项目根目录/
│
├── lxl_v3.db                           # ★ NEW: V3 数据库（自动创建于 D:/trading_data/）
│
├── src/lxl_quantaxis/
│   │
│   ├── fundamental/                    # ★ NEW: Phase 1
│   │   ├── __init__.py
│   │   ├── contracts.py               # FundamentalSnapshot, FundamentalSeries, PeerContext
│   │   ├── fetcher.py                  # FundamentalFetcher
│   │   ├── storage.py                  # FundamentalStorage
│   │   ├── peer.py                     # PeerAnalyzer
│   │   └── factor_bridge.py            # 7 个基本面因子注册
│   │
│   ├── journal/                        # ★ NEW: Phase 2
│   │   ├── __init__.py
│   │   ├── models.py                   # MemoryEntry
│   │   ├── repository.py              # MemoryRepository + schema.sql 初始化
│   │   ├── analytics.py               # MemoryAnalytics
│   │   └── schema.sql                 # 数据库建表 DDL
│   │
│   ├── report/                         # ★ NEW: Phase 3
│   │   ├── __init__.py
│   │   ├── generator.py               # ReportGenerator
│   │   └── types/
│   │       ├── __init__.py
│   │       ├── brief.py               # Investment Brief 数据组装
│   │       ├── research.py            # Research Report 数据组装
│   │       └── daily.py               # Daily Brief 数据组装
│   │
│   └── (以下 V2 模块全部不动)
│       ├── core/
│       ├── factor/        # 仅修改 registry 以注册基本面因子
│       ├── strategy/
│       ├── backtest/
│       ├── research/      # 仅修改 application.py 以增加 Memory 钩子
│       ├── portfolio/
│       ├── ai/
│       ├── data/
│       ├── api/
│       ├── memory/
│       ├── execution/
│       ├── risk/
│       ├── ops/
│       └── dashboard/
│
├── templates/                          # Web 模板
│   ├── workspace.html                  # ★ NEW: Dashboard 首页
│   ├── journal.html                    # ★ NEW: 记忆日记
│   ├── fundamental.html               # ★ NEW: 基本面浏览器
│   ├── reports/                        # ★ NEW: 报告模板
│   │   ├── brief.html.jinja2
│   │   ├── research.html.jinja2
│   │   └── daily.html.jinja2
│   │
│   └── (以下 V2 模板不动，仅增加导航栏)
│       ├── landing.html
│       ├── pipeline.html
│       ├── portfolio.html
│       ├── cases.html
│       ├── terminal.html
│       ├── studio.html
│       ├── game.html
│       ├── login.html
│       ├── admin.html
│       └── professional.html
│
├── static/
│   └── css/
│       └── v3-nav.css                  # ★ NEW: V3 导航栏样式
│
├── tests/
│   ├── test_fundamental.py             # ★ NEW
│   ├── test_journal.py                 # ★ NEW
│   └── test_report.py                  # ★ NEW
│
├── docs/
│   ├── ARCHITECTURE_V3.md              # V3 完整架构设计（参考文档）
│   ├── ARCHITECTURE_V3_SCOPING.md      # 架构裁剪审查
│   └── V3_MVP_SPEC.md                  # ★ 本文档：MVP 冻结规格
│
├── web_modern.py                       # MODIFIED: +~200 行 V3 路由
├── pyproject.toml                      # MODIFIED: 无依赖变更（不需要新包）
└── requirements.txt                    # MODIFIED: 无变更（akshare 已有）
```

### 8.2 修改文件（非新增）

| 文件 | 修改内容 | 增量行数 |
|------|----------|----------|
| `web_modern.py` | 增加 V3 路由 + 导航栏 context_processor | ~200 行 |
| `src/lxl_quantaxis/research/application.py` | 管线末尾增加 Memory 钩子 | ~20 行 |
| `src/lxl_quantaxis/factor/registry/registry.py` | 注册 7 个基本面因子 | ~30 行 |
| `templates/*.html`（10 个） | 增加 V3 导航栏（可选，不影响功能） | ~5 行/个 |

### 8.3 代码量估算

| 模块 | Python 文件 | 估计行数 |
|------|------------|----------|
| `fundamental/` | 6 个文件 | ~800 行 |
| `journal/` | 4 个文件 + 1 SQL | ~500 行 |
| `report/` | 5 个文件 | ~400 行 |
| Web 路由（web_modern.py 增量） | - | ~200 行 |
| Web 模板（HTML） | 6 个文件 | ~600 行 |
| CSS | 1 个文件 | ~80 行 |
| 测试 | 3 个文件 | ~400 行 |
| **总计** | **~25 个文件** | **~3000 行** |

---

## 9. Commit Roadmap

### 9.1 Phase 概览

```
Phase 1: Fundamental Intelligence   Week 1-2   12 commits   基本面数据 + Web 页面
Phase 2: Memory System              Week 3-4   12 commits   记忆 CRUD + 管线集成 + Web 页面
Phase 3: Reports + Workspace        Week 5-6   14 commits   报告生成 + 工作台 Shell
Phase 4: Polish + Release           Week 7-8   12 commits   测试 + 文档 + 发布
                                          ──
                               Total: ~50 commits
```

### 9.2 Phase 1: Fundamental Intelligence（12 commits）

```
Week 1: 数据层
  feat(fundamental): add FundamentalSnapshot and FundamentalSeries contracts
  feat(fundamental): add FundamentalFetcher — akshare financial data download
  feat(fundamental): add FundamentalStorage — SQLite CRUD for snapshots and series
  feat(fundamental): add PeerAnalyzer — Shenwan industry classification and peer comparison
  feat(fundamental): add fundamental factor bridge — register 7 factors

Week 2: Web 层
  feat(web): add /fundamental page — stock lookup, metric cards, trend chart
  feat(web): add /api/fundamental/<symbol> — snapshot API
  feat(web): add /api/fundamental/<symbol>/series — historical series API
  feat(web): add /api/fundamental/<symbol>/peers — peer comparison API
  style(web): add fundamental page styles (terminal.css compatible)
  test(fundamental): add fundamental module tests
  docs: update CHANGELOG with Phase 1 completion
```

### 9.3 Phase 2: Memory System（12 commits）

```
Week 3: 数据层 + 管线集成
  feat(journal): add MemoryEntry model and ENTRY_TYPES
  feat(journal): add schema.sql — lxl_v3.db DDL
  feat(journal): add MemoryRepository — CRUD with FTS5 search
  feat(journal): add MemoryAnalytics — hit rate, calibration, tag stats
  feat(research): add Memory hook to pipeline — auto-save thesis to memory
  feat(web): add /api/journal/* routes — list, create, detail, update, delete, search

Week 4: Web 层
  feat(web): add /journal page — calendar view, entry list, search, filter
  feat(web): add journal entry editor — create/edit form with Markdown
  feat(web): add /workspace page — dashboard with memory stats cards
  style(web): add journal and workspace page styles
  test(journal): add journal module tests
  docs: update CHANGELOG with Phase 2 completion
```

### 9.4 Phase 3: Reports + Workspace（14 commits）

```
Week 5: 报告系统
  feat(report): add ReportGenerator — Jinja2 template engine
  feat(report): add InvestmentBrief template + data assembler
  feat(report): add ResearchReport template + data assembler
  feat(report): add DailyBrief template + data assembler
  feat(web): add /api/report/generate — report generation API
  feat(web): add report viewer page — HTML display + download

Week 6: 工作台统一
  feat(web): add V3 navigation bar — unified shell across all pages
  feat(web): add V3 nav context_processor — inject nav into all templates
  style(web): add v3-nav.css — dark theme navigation bar
  feat(web): add workspace dashboard — KPI tiles, quick actions, recent theses
  feat(web): add report download links from workspace
  refactor(web): redirect / to /workspace (instead of /login)
  test(report): add report generation tests
  docs: update CHANGELOG with Phase 3 completion
```

### 9.5 Phase 4: Polish + Release（12 commits）

```
Week 7: 测试 + 打磨
  test: add end-to-end test — thesis → pipeline → memory → report
  test: add integration test — fundamental data fetch → storage → web display
  fix: edge cases and error handling across V3 modules
  perf: add fundamental data caching with staleness check
  chore: ensure all V2 tests still pass (CI gate)
  docs: update README with V3 features and screenshots

Week 8: 发布
  docs: update ARCHITECTURE.md with V3 section
  docs: update USER_GUIDE.md with V3 features usage
  docs: add V3_MVP_SPEC.md as frozen reference
  docs: write RELEASE_NOTES_v3.0.0.md
  chore: bump version to 3.0.0-mvp
  chore: create v3.0.0-mvp git tag
```

### 9.6 分支策略

```
main
  │
  ├── v3-fundamental     (Phase 1, 12 commits, merge via PR)
  ├── v3-memory          (Phase 2, 12 commits, merge via PR)
  ├── v3-reports         (Phase 3, 14 commits, merge via PR)
  ├── v3-polish          (Phase 4, 12 commits, merge via PR)
  │
  └── v3.0.0-mvp tag     (冻结发布)
```

---

## 10. 验收标准

### 10.1 功能验收

| # | 验收项 | 验收方式 |
|---|--------|----------|
| F1 | 输入 A 股代码，能看到 PE/PB/ROE/增速历史趋势图 | 手动测试 `/fundamental?symbol=000858` |
| F2 | 输入 A 股代码，能看到同行对比（申万行业分类正确） | 手动测试 `/api/fundamental/000858/peers` |
| F3 | 7 个基本面因子已在因子注册表中可用 | `FACTOR_REGISTRY["pe_percentile_5y"]` 存在 |
| F4 | 管线跑完后，Memory 中自动出现一条 thesis 记录 | 跑 `demo_ai_research.py` → 检查 `memory_entries` 表 |
| F5 | Memory 支持全文搜索（中文） | 搜索"白酒"能返回相关条目 |
| F6 | 能手动创建/编辑/删除 Memory 条目 | 手动测试 `/journal` |
| F7 | Memory Analytics 统计数据正确（总数、命中率、待 review） | 创建几条 correct/wrong 的 thesis → 检查 `/workspace` 卡片 |
| F8 | 能生成 Investment Brief（HTML 格式） | 手动触发 → 浏览器打开 |
| F9 | 能生成 Research Report（HTML 格式） | 手动触发 → 浏览器打开 |
| F10 | 所有页面有统一导航栏（Workspace/Pipeline/Journal/Fundamental/Portfolio） | 浏览所有页面 |
| F11 | `/` 重定向到 `/workspace` 而非 `/login` | 访问 `http://127.0.0.1:5000/` |
| F12 | V2 全部功能正常（管线、回测、策略、因子的 V2 测试全过） | `pytest tests/` |

### 10.2 非功能验收

| # | 验收项 | 标准 |
|---|--------|------|
| NF1 | 零新依赖 | `pip freeze` diff 无新增包（akshare 已有） |
| NF2 | V2 测试全部通过 | `pytest tests/` 400+ tests pass |
| NF3 | 新代码测试覆盖率 | > 80%（`test_fundamental.py`, `test_journal.py`, `test_report.py`） |
| NF4 | 基本面数据拉取性能 | 单只股票 5 年财报 < 10s（含 akshare 网络请求） |
| NF5 | Memory 搜索性能 | FTS5 全文搜索 < 100ms（1000 条数据量级） |
| NF6 | 报告生成性能 | < 3s（含 Plotly 图表渲染） |
| NF7 | 数据库自动创建 | 首次启动自动创建 `lxl_v3.db` + 建表 |
| NF8 | 错误隔离 | Memory 写入失败不影响管线结果返回 |

### 10.3 代码质量

| # | 验收项 | 标准 |
|---|--------|------|
| Q1 | 类型注解 | 所有新函数有完整 type hints |
| Q2 | Dataclass | 所有数据模型用 frozen dataclass |
| Q3 | Ruff | 零新增 lint 错误 |
| Q4 | MyPy | 新代码通过 strict 模式 |
| Q5 | 文档字符串 | 每个公开函数有 docstring |
| Q6 | 无循环导入 | V3 模块不导入 V2 内部模块 |

---

## 附录 A: 不引入的新依赖

V3 MVP **零新依赖**。所有功能用已有包实现：

| 功能 | 已有依赖 | 用法 |
|------|---------|------|
| 基本面数据 | `akshare` (已有) | 财报 + 估值指标 + 行业分类 |
| 数据库 | `sqlite3` (标准库) | lxl_v3.db |
| Web 框架 | `flask` (已有) | 新增路由 |
| 报告渲染 | `jinja2` (flask 内置) | 报告模板 |
| 图表 | `plotly` (已有) | 基本面趋势图 |
| 定时任务 | `apscheduler` (可选依赖) | Daily Brief 自动生成 |

---

> **本规格文档已冻结。实施时以本文档为唯一权威来源。**  
> **ARCHITECTURE_V3.md 作为长期愿景参考保留，与本规格冲突时以本规格为准。**
