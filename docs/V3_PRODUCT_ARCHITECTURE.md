# LXL·QuantAxis V3.0 — Product Architecture

> **AI-Powered Personal Investment Research Operating System**  
> AI驱动的个人投资研究操作系统

**Document Type**: Product Architecture (产品架构设计)  
**Status**: DESIGN PHASE — 不写代码  
**Base**: V2.0.0 Showcase  
**Target**: V3.0.0  
**Role**: Product Architect × Quant Research Lead × AI Product Lead  
**Date**: 2026-08-06

---

## 目录

1. [Product Vision（产品愿景）](#1-product-vision)
2. [V2 → V3 Evolution（演进路线）](#2-v2--v3-evolution)
3. [User Journey（用户旅程）](#3-user-journey)
4. [Module 1: Investment Memory System](#4-module-1-investment-memory-system)
5. [Module 2: Company Intelligence Engine](#5-module-2-company-intelligence-engine)
6. [Module 3: Research Workspace](#6-module-3-research-workspace)
7. [Module 4: Quant Validation Engine](#7-module-4-quant-validation-engine)
8. [Module 5: Research Report Generator](#8-module-5-research-report-generator)
9. [Database Design（数据库设计）](#9-database-design)
10. [Page Architecture（页面架构）](#10-page-architecture)
11. [API Design（API设计）](#11-api-design)
12. [File Structure（文件结构）](#12-file-structure)
13. [Development Roadmap（开发路线）](#13-development-roadmap)
14. [Commit Plan（提交规划）](#14-commit-plan)
15. [Design Decisions（设计决策）](#15-design-decisions)

---

## 1. Product Vision

### 1.1 产品定位

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                  │
│   LXL·QuantAxis V3                                               │
│                                                                  │
│   AI-Powered Personal Investment Research Operating System       │
│                                                                  │
│   不是:                                                          │
│   ❌ 股票预测工具        ❌ 自动交易系统                           │
│   ❌ Bloomberg 替代品    ❌ AI 炒股机器人                          │
│                                                                  │
│   是:                                                            │
│   帮助投资者完成完整研究闭环的个人投研操作系统                          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 研究闭环

```
                    ┌──────────────────┐
                    │                  │
                    │   发现机会        │
                    │   Discover       │
                    │   Opportunity    │
                    │                  │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │                  │
        ┌───────────│   形成观点        │◀──────────┐
        │           │   Form Thesis    │           │
        │           │                  │           │
        │           └────────┬─────────┘           │
        │                    │                     │
        │                    ▼                     │
        │           ┌──────────────────┐           │
        │           │                  │           │
        │           │   验证逻辑        │           │
        │           │   Validate       │           │
        │           │   Logic          │           │
        │           │                  │           │
        │           └────────┬─────────┘           │
        │                    │                     │
        │                    ▼                     │
        │           ┌──────────────────┐           │
        │           │                  │           │
        │           │   记录决策        │           │
        │           │   Record         │           │
        │           │   Decision       │           │
        │           │                  │           │
        │           └────────┬─────────┘           │
        │                    │                     │
        │                    ▼                     │
        │           ┌──────────────────┐           │
        │           │                  │           │
        │           │   跟踪结果        │           │
        │           │   Track          │           │
        │           │   Outcome        │           │
        │           │                  │           │
        │           └────────┬─────────┘           │
        │                    │                     │
        │                    ▼                     │
        │           ┌──────────────────┐           │
        │           │                  │           │
        └───────────│   复盘优化        │───────────┘
                    │   Review &       │
                    │   Optimize       │
                    │                  │
                    └──────────────────┘
```

**六个环节，五个模块支撑**：

| 环节 | 支撑模块 | 用户行为 |
|------|----------|----------|
| 发现机会 | Company Intelligence + Workspace | 浏览市场、筛选标的、阅读基本面 |
| 形成观点 | Research Workspace | 撰写投资论文（Investment Thesis） |
| 验证逻辑 | Quant Validation Engine | 回测策略、验证因子、评估风险 |
| 记录决策 | Investment Memory System | 记录买入/卖出决策及理由 |
| 跟踪结果 | Investment Memory System | 标记论文结果、计算命中率 |
| 复盘优化 | Investment Memory System | 回顾教训、更新规则、校准信心 |

### 1.3 核心价值主张

```
┌──────────────────────────────────────────────────────────────┐
│                                                               │
│   "LXL·QuantAxis 不预测市场。                                   │
│    它增强你的研究能力。"                                         │
│                                                               │
│   "不是告诉你要买什么。                                          │
│    而是帮你记住你研究过什么、验证过什么、学到了什么。"                  │
│                                                               │
│   "不是替代你的判断。                                            │
│    而是让你的判断可追溯、可验证、可优化。"                             │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

### 1.4 目标用户画像

| 维度 | 描述 |
|------|------|
| **身份** | 认真对待投资的个人投资者 / 独立量化研究员 |
| **频次** | 每周 3-10 个投资想法，1-3 次实际交易 |
| **市场** | 主要 A 股，兼顾港股美股 |
| **风格** | 基本面 + 量化结合，中长期持有 |
| **痛点** | 研究过很多标的但忘了为什么；不知道自己的判断有多准；没有系统化的研究流程 |
| **设备** | 桌面端为主，偶尔平板查看 |

---

## 2. V2 → V3 Evolution

### 2.1 产品演进对比

| 维度 | V2.0 Showcase | V3.0 |
|------|---------------|------|
| **定位** | AI Research Showcase（AI 研究展示） | Personal Investment Research OS（个人投研操作系统） |
| **核心流程** | 输入论文 → 7 阶段管线 → 输出报告 | 发现 → 研究 → 验证 → 记录 → 跟踪 → 复盘（闭环） |
| **状态管理** | 无状态（每次管线独立运行） | 有状态（记忆持久化、结果可追踪） |
| **AI 角色** | 管线处理器（单次调用） | 研究助手（嵌入每个环节） |
| **数据范围** | 行情数据 + 28 技术因子 | + 财报数据 + 估值指标 + 行业对比 |
| **用户界面** | 9 个独立页面，无统一导航 | 统一 Shell（Workspace 为入口） |
| **核心指标** | 管线成功率 | 论文命中率 + 决策质量 |
| **规模** | 展示级（showcase） | 可用级（daily driver） |

### 2.2 兼容策略

```
V2.0.0 代码:
├── src/                             → 不动
├── src/lxl_quantaxis/               → 不动（155 文件保持原样）
│   ├── factor/                      → 追加基本面因子注册（1 行 import）
│   ├── research/application.py      → 管线末尾追加 Memory 钩子（~20 行）
│   └── ...                          → 其余零改动
│
V3.0.0 新增:
├── src/v3/                          → 所有 V3 新代码在这里
│   ├── memory/                      → Module 1: Investment Memory System
│   ├── intelligence/                → Module 2: Company Intelligence Engine
│   ├── workspace/                   → Module 3: Research Workspace (backend)
│   ├── validation/                  → Module 4: Quant Validation Engine
│   └── report/                      → Module 5: Research Report Generator
│
├── templates/v3/                    → V3 页面模板
├── static/css/v3/                   → V3 样式
└── tests/v3/                        → V3 测试

原则:
  ✓ V2 代码不改 — src/lxl_quantaxis/ 只读
  ✓ V3 代码独立 — src/v3/ 完全新增
  ✓ Web 路由增量 — web_modern.py 增加 import src/v3
  ✓ 数据库增量 — lxl_v3.db 新建, V2 数据库不动
```

---

## 3. User Journey

### 3.1 核心用户旅程

**场景: 从发现机会到复盘优化（完整闭环之旅）**

```
═══════════════════════════════════════════════════════════════════
STEP 1: DISCOVER — 发现机会
═══════════════════════════════════════════════════════════════════

  用户在 /workspace 看到 Dashboard
  → 点击 "五粮液 000858" 进入 Research Project

  在 Company Intelligence 页面看到:
  ├── 公司概览: 白酒龙头，高端定位，品牌护城河
  ├── 财务指标: PE 25.3 (5年分位 65%)、ROE 24.8%、营收增速 +15.3%
  ├── 行业对比: ROE 行业第 5/47，PE 低于行业中位数
  └── 估值分析: 当前估值合理，低于近 3 年均值

  用户觉得有意思 → 进入下一步

═══════════════════════════════════════════════════════════════════
STEP 2: FORM — 形成观点
═══════════════════════════════════════════════════════════════════

  用户在 Research Workspace 中写 Investment Thesis:

  "五粮液受益于消费复苏和高端白酒结构性升级。
   当前 PE 处于历史中位，ROE 行业领先。
   预计估值修复 + 盈利增长双驱动。
   目标价 180 元，12 个月，止损 130 元。"

  信心度: 70%

═══════════════════════════════════════════════════════════════════
STEP 3: VALIDATE — 验证逻辑
═══════════════════════════════════════════════════════════════════

  用户点击 "Validate Thesis"

  Quant Validation Engine 运行:
  ├── AI Parser: 提取结构化论文
  ├── Factor Mapper: 映射到因子模型 (momentum + quality + consumer)
  ├── Strategy Builder: 生成 DSL 策略规则
  ├── Backtest: 对 000858 历史数据回测
  ├── AI Assessment: Sharpe 1.35, Sortino 1.82, Max DD -18%
  └── Validation Score: 72/100 (Pass)

  验证通过 ✓ → 论文置信度从 70% 调整为 75%

═══════════════════════════════════════════════════════════════════
STEP 4: RECORD — 记录决策
═══════════════════════════════════════════════════════════════════

  几天后，股价回调到 145 元

  用户在 Journal 中记录 Decision:

  "2026-08-15: 买入 000858 五粮液 1,000 股 @ ¥145
   理由: 论文验证通过，估值合理，消费板块轮动启动
   止损: ¥130, 目标: ¥180
   仓位: 15% 总资产
   市场环境: 沪深300震荡上行，消费板块资金流入"

  此 Decision 自动关联到刚才的 Thesis

═══════════════════════════════════════════════════════════════════
STEP 5: TRACK — 跟踪结果
═══════════════════════════════════════════════════════════════════

  3 个月后...

  用户在 Memory System 中:
  → 看到 Thesis 状态是 "pending review"（论文发出 90 天了）
  → 系统提醒: "你有 3 条论文待复盘"

  用户点击 Review:
  → 当前价格: ¥172 (+18.6%)
  → 论文目标价 ¥180 接近达成
  → 标记 outcome_status = "correct"
  → 写 outcome_notes: "消费复苏逻辑验证，白酒龙头估值修复如期发生"

  系统自动更新:
  ├── 论文命中率: 58% → 62%
  ├── 高信心论文命中率: 75% → 80%
  └── 消费板块论文命中率: 66% → 71%

═══════════════════════════════════════════════════════════════════
STEP 6: REVIEW — 复盘优化
═══════════════════════════════════════════════════════════════════

  周末，用户打开 /workspace 看 Memory Analytics:

  "过去 6 个月:
    ├── 12 条论文，7 条正确 (58%)
    ├── 高信心论文 (>0.7): 5 条，4 条正确 (80%) ✓
    ├── 低信心论文 (<0.5): 4 条，1 条正确 (25%) — 你的低信心判断值得重视
    ├── 最佳板块: 消费 (3/4 正确)
    ├── 最差板块: 科技 (1/3 正确)
    └── 决策胜率: 5/8 盈利 (62%)"

  用户写下 Lesson:

  "高信心论文准确率 80% → 应该只交易 conviction > 0.7 的机会。
   科技板块判断差 → 需要增加科技行业的知识储备。
   消费板块判断好 → 这是能力圈，应该深耕。"

═══════════════════════════════════════════════════════════════════

  闭环完成。系统变聪明了。投资者也变聪明了。

  下一次研究 000858，打开 Research Project:
  → 自动显示之前的 2 条 Thesis、1 条 Decision、1 条 Lesson
  → Company Intelligence 更新到最新财报
  → 用户可以基于历史经验做更好的判断
```

---

## 4. Module 1: Investment Memory System

### 4.1 模块定位

> **投资认知数据库** — 记录投资者的整个研究过程，追踪判断准确率，驱动持续优化。

**不是**交易日志（V1 已有）。**而是**认知数据库——记录你的思考过程、判断质量、学习轨迹。

### 4.2 四种记忆类型

```
Investment Memory System
│
├── 📝 Research Notes（研究笔记）
│   "我对这个行业的理解是什么？"
│   自由格式，Markdown 写作
│   标签: 行业分析、公司研究、宏观观察
│
├── 💡 Investment Thesis（投资论文）
│   "我为什么看好/看空这个标的？"
│   结构化: 核心逻辑 + 催化剂 + 风险 + 信心度
│   可验证: 有明确的目标价、时间框架、判断标准
│   可追踪: 结果标记 (correct/wrong/expired)
│
├── 📊 Decision Record（决策记录）
│   "我做了什么交易？为什么？"
│   关联论文: 每笔交易对应一条 Thesis
│   记录: 买入价、仓位、理由、市场环境、情绪状态
│   事后: 盈亏、结果评估 (good/bad/neutral)
│
└── 🧠 Reflection（反思笔记）
    "我从这次经历中学到了什么？"
    类型: 教训、模式识别、规则更新
    关联: 可关联到具体 Thesis 或 Decision
    作用: 形成个人投资原则
```

### 4.3 统一数据模型

一张表承载四种记忆类型：

```python
# src/v3/memory/models.py

@dataclass(frozen=True, slots=True)
class MemoryEntry:
    """统一记忆条目 — 研究笔记、投资论文、决策记录、反思笔记"""

    # ── 基础字段 ──
    entry_id: int                       # 自增主键
    entry_type: str                     # "note" | "thesis" | "decision" | "reflection"
    date: str                           # ISO date
    title: str
    content: str                        # Markdown

    # ── 关联字段 ──
    symbols: list[str]                  # 涉及标的
    tags: list[str]                     # 标签（多级）
    project_id: str | None              # 所属 Research Project
    related_ids: list[int]              # 关联的其他记忆条目

    # ── Thesis 专属 ──
    thesis_conviction: float | None     # 信心度 0.0-1.0
    thesis_catalysts: list[str] | None  # 催化剂列表
    thesis_risks: list[str] | None      # 风险列表
    thesis_timeline: str | None         # 预期时间框架
    target_price: float | None          # 目标价
    pipeline_snapshot: dict | None      # 管线验证结果 JSON
    report_path: str | None             # 关联的研究报告

    # ── Decision 专属 ──
    decision_type: str | None           # "buy" | "sell" | "hold"
    decision_price: float | None
    decision_quantity: float | None
    decision_reason: str | None
    market_context: str | None          # 决策时的市场环境
    mood: str | None                    # 决策时的情绪状态

    # ── 结果追踪（Thesis 和 Decision 共用）──
    outcome_status: str | None          # "pending" | "correct" | "wrong" | "expired" | "partial"
    outcome_detail: str | None          # 详细复盘
    outcome_return: float | None        # 实际收益
    reviewed_at: str | None             # 复盘时间

    # ── 元数据 ──
    created_at: str
    updated_at: str
```

### 4.4 标签体系

```
标签分类:
├── 资产类别: 股票、债券、基金、商品、外汇
├── 市场: A股、港股、美股
├── 行业: 消费、科技、金融、医疗、能源、制造、地产...
├── 风格: 价值、成长、红利、周期、防御
├── 策略: 趋势跟踪、均值回归、动量、事件驱动、基本面
├── 主题: AI、新能源、消费升级、老龄化、国产替代...
├── 操作: 买入、卖出、加仓、减仓、观望
├── 结果: 盈利、亏损、持平
└── 反思: 教训、模式、原则、规则更新
```

### 4.5 搜索系统

```python
# src/v3/memory/search.py

class MemorySearch:
    """基于 SQLite FTS5 的全文搜索"""

    def search(
        self,
        query: str,                     # 关键词
        entry_type: str | None = None,  # 筛选类型
        symbols: list[str] | None = None,
        tags: list[str] | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        outcome_status: str | None = None,
    ) -> list[MemoryEntry]:
        ...

    # 典型搜索:
    # "白酒 消费" — 行业关键词搜索
    # entry_type="thesis" + outcome_status="pending" — 待复盘论文
    # symbols=["000858"] — 某只股票的所有记忆
    # tags=["教训"] — 所有教训
```

### 4.6 复盘机制

```
复盘流程:
  1. 系统识别 — outcome_status="pending" + created_at > 30 天
     → Dashboard 显示 "3 条论文待复盘"

  2. 用户打开 Review 面板
     → 显示论文原始内容 + 当时信心度
     → 自动拉取当前行情（现价 vs 目标价）
     → 提示用户评估结果

  3. 用户标记结果
     → correct: 论文方向正确，逻辑验证
     → wrong: 论文方向错误，需要总结原因
     → expired: 论文时效过期（如事件驱动失效）
     → partial: 部分正确（如方向对但幅度不够）

  4. 写入反思
     → 从结果中提炼教训
     → 更新投资原则

  5. 系统自动更新 Analytics
     → 命中率重算
     → 信心校准更新
     → 板块表现更新
```

### 4.7 Memory Analytics Dashboard

```
┌─────────────────────────────────────────────────────────┐
│  Memory Analytics                                       │
│                                                         │
│  ┌──────────┬──────────┬──────────┬──────────┐         │
│  │ 论文总数  │ 命中率    │ 待复盘    │ 决策胜率  │         │
│  │   15     │  62% ▲   │    3     │  58%     │         │
│  └──────────┴──────────┴──────────┴──────────┘         │
│                                                         │
│  ┌─────────────────────┐  ┌──────────────────────────┐ │
│  │ 信心校准             │  │ 板块表现                   │ │
│  │                     │  │                          │ │
│  │ 高信心(>0.7): 80% ✓ │  │ 消费:  ████████ 75%     │ │
│  │ 中信心(0.5-0.7): 50%│  │ 科技:  ███ 33%          │ │
│  │ 低信心(<0.5): 25%   │  │ 金融:  ██████ 60%       │ │
│  │                     │  │ 医疗:  ████████ 80%     │ │
│  └─────────────────────┘  └──────────────────────────┘ │
│                                                         │
│  ┌───────────────────────────────────────────────────┐ │
│  │ 最近教训                                            │ │
│  │ 💡 高信心论文准确率 80% → 坚持只交易 conviction>0.7 │ │
│  │ 💡 科技板块 1/3 正确 → 需要加强科技行业知识          │ │
│  │ 💡 止损执行率 90% → 纪律性良好，继续保持             │ │
│  └───────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### 4.8 文件清单

```
src/v3/memory/
├── __init__.py
├── models.py              # MemoryEntry dataclass
├── repository.py          # MemoryRepository: CRUD + FTS5
├── search.py              # MemorySearch: 高级搜索
├── analytics.py           # MemoryAnalytics: 命中率/信心校准/板块表现
├── review.py              # ReviewEngine: 复盘提醒 + 结果追踪
└── schema.sql             # 数据库建表 DDL
```

---

## 5. Module 2: Company Intelligence Engine

### 5.1 模块定位

> **公司智能分析** — 输入股票代码，输出结构化公司画像。

**不做的**：Bloomberg 级别的实时基本面分析。

**做的**：类似 Morningstar 的简洁公司一页纸 + 关键指标趋势。

**数据源**：akshare（免费、覆盖 A 股全部财报数据）。

### 5.2 分析维度

```
Company Intelligence
│
├── 📋 Company Profile（公司概览）
│   ├── 公司全称、股票代码、上市交易所
│   ├── 主营业务描述
│   ├── 行业分类（申万一级/二级/三级）
│   ├── 上市日期
│   ├── 总股本、流通股本
│   └── 实际控制人、管理层
│
├── 🏗️ Business Analysis（业务分析）
│   ├── 收入构成（按产品线/地区）
│   ├── 商业模式概述
│   ├── 竞争优势（护城河评估）
│   └── 产业链位置（上游/中游/下游）
│
├── 📊 Financial Metrics（财务指标）
│   ├── 估值: PE-TTM, PB, PS, EV/EBITDA
│   ├── 盈利: ROE, ROA, ROIC, 毛利率, 净利率
│   ├── 增长: 营收 YoY, 净利润 YoY, EPS 增长
│   ├── 质量: FCF, 经营现金流/净利润, 应收账款/营收
│   ├── 健康: 资产负债率, 流动比率, 利息覆盖倍数
│   └── 每股: EPS, 每股净资产, 每股分红
│
├── 📈 Historical Trends（历史趋势）
│   ├── PE-TTM 5 年走势（当前 vs 历史区间）
│   ├── PB 5 年走势
│   ├── ROE 5 年走势
│   ├── 营收/利润增速 5 年走势
│   └── 股价 + 估值叠加图
│
├── 🏢 Industry Position（行业地位）
│   ├── 申万行业分类
│   ├── 同行业可比公司列表
│   ├── 核心指标行业排名（PE、ROE、增速、市值）
│   └── 行业平均估值 vs 公司估值
│
├── 💰 Valuation Analysis（估值分析）
│   ├── PE 分位数（1年/3年/5年）
│   ├── PB 分位数（1年/3年/5年）
│   ├── PEG（PE / 盈利增速）
│   └── 估值评级: 低估/合理/高估（vs 历史和行业）
│
└── ⚠️ Risk Factors（风险因素）
    ├── 财务风险: 高负债、现金流差、应收账款异常
    ├── 经营风险: 客户集中度、单一产品依赖
    ├── 行业风险: 政策变化、技术颠覆
    └── 估值风险: 估值过高、盈利不及预期
```

### 5.3 数据获取策略

```python
# src/v3/intelligence/fetcher.py

class CompanyIntelligenceFetcher:
    """公司智能数据获取器"""

    # === 数据源映射 ===
    SOURCES = {
        "profile":       "akshare.stock_individual_info_ths",       # 公司基本信息
        "financials":    "akshare.stock_financial_abstract_ths",    # 财报摘要
        "valuation":     "akshare.stock_a_lg_indicator",            # PE/PB 每日估值
        "industry":      "akshare.stock_board_concept_cons_ths",   # 行业分类
        "industry_pe":   "akshare.stock_board_industry_pe_ths",    # 行业估值对比
        "cash_flow":     "akshare.stock_financial_cash_flow_ths",  # 现金流表
        "balance_sheet": "akshare.stock_financial_balance_sheet_ths", # 资产负债表
    }

    def fetch_company_profile(self, symbol: str) -> CompanyProfile:
        """拉取公司概览"""
        ...

    def fetch_financial_snapshots(self, symbol: str, years: int = 5) -> list[FundamentalSnapshot]:
        """拉取历年财报快照"""
        ...

    def fetch_valuation_series(self, symbol: str) -> FundamentalSeries:
        """拉取 PE/PB 历史序列"""
        ...

    def fetch_industry_context(self, symbol: str) -> IndustryContext:
        """拉取行业分类 + 同行对比"""
        ...

    def fetch_full_intelligence(self, symbol: str) -> CompanyIntelligence:
        """一键拉取全部公司智能数据"""
        ...
```

### 5.4 输出: 公司智能报告

```
┌─────────────────────────────────────────────────────────┐
│  五粮液 (000858.SZ)                        Company Intel│
├─────────────────────────────────────────────────────────┤
│                                                          │
│  📋 公司概览                                              │
│  宜宾五粮液股份有限公司 | 白酒 | 深交所主板                  │
│  上市日期: 1998-04-27 | 总市值: 5,820 亿元                │
│  主营业务: 白酒生产销售，"五粮液"系列高端白酒                 │
│                                                          │
│  ┌──────────┬──────────┬──────────┬──────────┐          │
│  │ PE-TTM   │ PB       │ ROE      │ 营收增速  │          │
│  │  25.3    │  5.2     │ 24.8%   │ +15.3%   │          │
│  │ 分位:65% │ 分位:58% │ 行业:5/47│ 行业:12/47│          │
│  └──────────┴──────────┴──────────┴──────────┘          │
│                                                          │
│  📈 PE-TTM 历史趋势                                       │
│  [Plotly 折线图: 当前值线 + 均值线 + ±1σ 区间]             │
│                                                          │
│  🏢 行业对比 (食品饮料, 47 家)                              │
│  指标          五粮液    行业中位数   排名   分位           │
│  PE-TTM        25.3      32.1      18/47  38%            │
│  ROE           24.8%     15.2%      5/47  89%  ▲        │
│  营收增速       +15.3%    +8.7%     12/47  74%  ▲        │
│  毛利率        75.2%     45.1%      3/47  94%  ▲        │
│                                                          │
│  💰 估值评级: 🟡 合理                                     │
│  PE 低于行业中位数 22%，处于自身 5 年 65% 分位              │
│  结合高于行业均值的 ROE 和增速，当前估值合理                  │
│                                                          │
│  ⚠️ 风险提示                                             │
│  · 白酒行业受政策影响大（消费税、限制三公消费）               │
│  · 高端白酒竞争加剧（茅台挤压、次高端崛起）                   │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### 5.5 文件清单

```
src/v3/intelligence/
├── __init__.py
├── contracts.py            # CompanyProfile, FundamentalSnapshot, FundamentalSeries, IndustryContext, CompanyIntelligence
├── fetcher.py              # CompanyIntelligenceFetcher: akshare 多接口聚合
├── analyzer.py             # CompanyAnalyzer: 估值评级、风险检测、趋势判断
├── storage.py              # IntelligenceStorage: 数据缓存到 lxl_v3.db
├── factor_bridge.py        # 7 个基本面因子注册到 V2 FACTOR_REGISTRY
└── templates/
    └── company_intel.html.jinja2  # 公司智能报告 HTML 模板
```

---

## 6. Module 3: Research Workspace

### 6.1 模块定位

> **投资研究工作台** — 一个股票 = 一个 Research Project。所有研究资料汇集一处。

**设计灵感**: Notion 的项目组织 + Bloomberg Research 的数据深度。

### 6.2 Research Project 模型

```
一个 Research Project = 一只股票的研究全集

ResearchProject
├── project_id: "proj-000858-20260806"
├── symbol: "000858"
├── name: "五粮液"
├── status: "active" | "archived" | "completed"
├── created_at: "2026-08-06"
│
├── 📋 Company Intelligence     (Module 2 输出)
│   └── 最新公司画像 + 财务指标
│
├── 💡 Investment Theses        (Module 1: entry_type="thesis")
│   ├── Thesis #1: "消费复苏 + 估值修复" (pending)
│   └── Thesis #2: "高端白酒结构性增长" (correct)
│
├── 📊 Quant Validation         (Module 4 输出)
│   ├── Validation #1: Score 72/100
│   │   └── 回测结果、因子分析、风险评估
│   └── Validation #2: Score 85/100
│
├── 📝 Research Notes           (Module 1: entry_type="note")
│   ├── "Q2 财报分析笔记"
│   └── "白酒行业政策梳理"
│
├── 📰 Related News             (未来 V4)
│
├── 📊 Decision Records         (Module 1: entry_type="decision")
│   ├── "2026-08-15: 买入 @ ¥145"
│   └── "2026-11-20: 卖出 @ ¥178"
│
├── 🧠 Reflections              (Module 1: entry_type="reflection")
│   └── "消费板块是我的能力圈"
│
└── 📄 Reports                  (Module 5 输出)
    ├── Investment_Brief_000858_20260806.html
    └── Research_Report_000858_20260806.md
```

### 6.3 Workspace 页面结构

```
┌──────────────────────────────────────────────────────────────┐
│  [LXL·QuantAxis V3]  Workspace  Pipeline  Journal  Companies │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─ 左侧: 项目列表 ───────────┐  ┌─ 右侧: 项目详情 ─────────┐ │
│  │                            │  │                           │ │
│  │ 🔍 [搜索项目...]            │  │  五粮液 (000858.SZ)       │ │
│  │                            │  │  Status: 🟢 Active        │ │
│  │ ├── 🟢 五粮液 000858       │  │                           │ │
│  │ │   Updated: 2h ago       │  │  ┌─────────────────────┐  │ │
│  │ │                         │  │  │ TABS:               │  │ │
│  │ ├── 🟢 中芯国际 688981     │  │  │ Overview │ Thesis   │  │ │
│  │ │   Updated: 1d ago       │  │  │ Validat. │ Journal  │  │ │
│  │ │                         │  │  │ Reports               │  │ │
│  │ ├── 🟡 茅台 600519         │  │  └─────────────────────┘  │ │
│  │ │   Updated: 3d ago       │  │                           │ │
│  │ │                         │  │  [Overview Tab 内容]      │ │
│  │ ├── ⚪ 药明康德 603259     │  │  ├── Company Intel 卡片  │ │
│  │ │   Updated: 7d ago       │  │  ├── 最新 Thesis 卡片    │ │
│  │ │                         │  │  ├── 最近 Decision 卡片  │ │
│  │ └── 🔒 宁德时代 300750     │  │  └── Validation 结果    │ │
│  │     Archived               │  │                           │ │
│  │                            │  │                           │ │
│  │ [+ New Project]            │  │                           │ │
│  └────────────────────────────┘  └───────────────────────────┘ │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

### 6.4 Workspace Dashboard（首页 `/workspace`）

```
┌──────────────────────────────────────────────────────────────┐
│  LXL·QuantAxis V3                    Welcome back, 研究员     │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐   │
│  │ 活跃项目  │ 论文命中率│ 待复盘    │ 本周论文  │ 连续记录  │   │
│  │    5     │   62%    │    3     │    2     │   12d   │   │
│  └──────────┴──────────┴──────────┴──────────┴──────────┘   │
│                                                               │
│  ┌─ Quick Actions ──────────┐  ┌─ Recent Activity ────────┐ │
│  │                           │  │                          │ │
│  │ [🔬 新建 Research Project] │  │ 2h ago  Thesis created   │ │
│  │ [✏️ 写 Investment Thesis]  │  │   五粮液: 消费复苏...    │ │
│  │ [📝 写研究笔记]            │  │                          │ │
│  │ [📊 跑 Quant Validation]   │  │ 1d ago  Decision recorded│ │
│  │ [📄 生成报告]              │  │   中芯国际: 买入 @ ¥58   │ │
│  └───────────────────────────┘  │                          │ │
│                                  │ 3d ago  Thesis reviewed  │ │
│  ┌─ Memory Insights ──────────┐ │   茅台: 估值修复 ✓       │ │
│  │                             │ │                          │ │
│  │ 💡 高信心论文命中率 80%     │ └──────────────────────────┘ │
│  │ 💡 消费板块表现最好 (75%)    │                              │
│  │ 💡 科技板块需要加强 (33%)    │  ┌─ Pending Reviews ──────┐ │
│  │ 💡 3 条论文等待复盘         │  │ 五粮液 Thesis #1 (90d)  │ │
│  │                             │  │ 药明康德 Thesis #1 (60d)│ │
│  └─────────────────────────────┘  │ 宁德时代 Thesis #2 (45d)│ │
│                                    └────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

### 6.5 文件清单

```
src/v3/workspace/
├── __init__.py
├── models.py               # ResearchProject dataclass
├── service.py              # WorkspaceService: project CRUD + 资源聚合
├── aggregator.py           # ProjectAggregator: 从各模块汇总数据
└── dashboard.py            # DashboardData: 首页 KPI 计算

templates/v3/
├── workspace/
│   ├── dashboard.html      # Dashboard 首页
│   ├── project_list.html   # 项目列表（左侧栏）
│   └── project_detail.html # 项目详情（右侧主区域 + Tab 切换）
```

---

## 7. Module 4: Quant Validation Engine

### 7.1 模块定位

> **量化验证引擎** — 不预测股票涨跌。验证你的投资逻辑是否在历史上成立。

### 7.2 设计哲学

```
❌ 错误认知: "系统告诉我这个股票会涨 → 我买"
✅ 正确认知: "我有一个投资逻辑 → 系统帮我验证这个逻辑在历史上是否有效 → 我判断是否交易"

核心区别:
  预测模型: 输入数据 → 输出涨跌概率（黑箱）
  验证引擎: 输入逻辑 → 输出验证结果（白箱，可解释）
```

### 7.3 验证流程

```
Investment Thesis (自然语言)
        │
        ▼
┌─────────────────────────────────────┐
│ Stage 1: Thesis Parsing             │
│ 输入: "五粮液受益于消费复苏..."       │
│ 输出: 结构化论文（标的/方向/逻辑/风险）│
│ 引擎: V2 ai_parser（复用）           │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ Stage 2: Logic Decomposition        │
│ 将论文分解为可验证的子逻辑:           │
│                                      │
│ Logic 1: "消费复苏 → 高端白酒需求↑"  │
│   → 验证: 消费板块 vs 白酒板块相关性   │
│                                      │
│ Logic 2: "ROE > 20% → 估值溢价"     │
│   → 验证: 高 ROE 公司 vs 行业平均估值 │
│                                      │
│ Logic 3: "PE 均值回归 → 价格修复"    │
│   → 验证: PE 分位 vs 后续 6M 收益    │
│                                      │
│ 引擎: V3 LogicDecomposer (NEW)      │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ Stage 3: Factor Mapping             │
│ 将子逻辑映射到量化因子:              │
│                                      │
│ Logic 1 → momentum_score, consumer   │
│ Logic 2 → roe_level, roe_trend      │
│ Logic 3 → pe_percentile_5y, mean_rev│
│                                      │
│ 引擎: V2 factor_mapper（复用+扩展）   │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ Stage 4: Strategy Construction      │
│ 因子 → DSL 策略规则:                 │
│                                      │
│ entry: pe_percentile_5y < 0.4 AND   │
│        roe_level > 0.6 AND           │
│        momentum_score > 0.5          │
│ exit:  pe_percentile_5y > 0.8 OR    │
│        max_drawdown > 0.15           │
│                                      │
│ 引擎: V2 strategy_builder（复用）     │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ Stage 5: Backtest Execution         │
│ 策略在历史数据上回测:                │
│ 时间: 2019-01-01 → 2026-08-06       │
│ 标的: 000858 + 消费板块可比公司      │
│                                      │
│ 引擎: V2 backtest engine（复用）     │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ Stage 6: Validation Scoring         │
│ 综合评估验证结果:                    │
│                                      │
│ Validation Score = weighted_sum(     │
│   Strategy Performance  (40%):      │
│     Sharpe > 1.0, 回撤 < 20%        │
│   Logic Coherence       (30%):      │
│     子逻辑是否得到数据支持           │
│   Factor Robustness     (20%):      │
│     因子 IC > 0.03, 衰减合理        │
│   Risk Assessment       (10%):      │
│     VaR 可控, 压力测试通过          │
│ )                                    │
│                                      │
│ 引擎: V3 ValidationScorer (NEW)     │
└──────────────┬──────────────────────┘
               │
               ▼
        ┌──────┴──────┐
        │             │
    Score ≥ 60    Score < 60
        │             │
        ▼             ▼
   ✅ Pass        ⚠️ Weak
   "逻辑在历史上  "逻辑验证不充分
    得到支持"     — 建议调整或
                  降低信心度"
```

### 7.4 Validation Score 计算细则

```python
# src/v3/validation/scorer.py

class ValidationScorer:
    """验证评分器 — 将管线输出转化为 0-100 的验证分数"""

    def score(self, pipeline_output: dict) -> ValidationResult:
        scores = {}

        # 1. 策略绩效 (40%)
        metrics = pipeline_output["backtest_result"]
        perf_score = self._score_performance(metrics)
        # Sharpe > 1.5 → 100, > 1.0 → 75, > 0.5 → 50, < 0 → 0
        # 综合: Sharpe(30%) + Sortino(20%) + MaxDD(25%) + WinRate(15%) + Calmar(10%)

        # 2. 逻辑一致性 (30%)
        thesis = pipeline_output["parsed_thesis"]
        factors = pipeline_output["factor_model"]
        logic_score = self._score_logic(thesis, factors)
        # 论文中的逻辑是否被正确映射为因子？
        # 因子权重是否与论文逻辑相符？

        # 3. 因子稳健性 (20%)
        factor_ic = pipeline_output.get("factor_ic", {})
        robustness_score = self._score_robustness(factor_ic)
        # IC > 0.05 → 强, 0.03-0.05 → 中, < 0.03 → 弱
        # IC 衰减是否合理？

        # 4. 风险评估 (10%)
        risk = pipeline_output.get("risk_assessment", {})
        risk_score = self._score_risk(risk)
        # VaR < 5% → 安全, 杠杆合理, 流动性充足

        total = (
            perf_score * 0.40
            + logic_score * 0.30
            + robustness_score * 0.20
            + risk_score * 0.10
        )

        return ValidationResult(
            score=round(total),
            breakdown={
                "performance": perf_score,
                "logic": logic_score,
                "robustness": robustness_score,
                "risk": risk_score,
            },
            verdict=self._verdict(total),
            suggestions=self._generate_suggestions(pipeline_output, total),
        )

    def _verdict(self, score: int) -> str:
        if score >= 80:    return "STRONG — 逻辑在历史上得到强有力支持"
        elif score >= 60:  return "PASS — 逻辑在历史上得到一定支持"
        elif score >= 40:  return "WEAK — 逻辑验证不充分，建议调整参数或降低信心"
        else:              return "FAIL — 历史数据不支持该逻辑"
```

### 7.5 文件清单

```
src/v3/validation/
├── __init__.py
├── scorer.py               # ValidationScorer: 评分引擎
├── decomposer.py           # LogicDecomposer: 论文 → 可验证子逻辑
└── contracts.py            # ValidationResult, LogicFragment
```

---

## 8. Module 5: Research Report Generator

### 8.1 模块定位

> **研究报告生成器** — 将研究过程转化为专业报告。

**风格**: LXL Equity Research Lab。

### 8.2 三种报告类型

```
Research Report Generator
│
├── 📄 Executive Brief（执行摘要，2-3页）
│   ├── 用途: 快速决策参考
│   ├── 读者: 自己（做交易决策前看）
│   ├── 内容:
│   │   ├── 股票信息 + 评级 + 目标价
│   │   ├── 3 句话投资逻辑
│   │   ├── 核心指标卡片 (PE/ROE/增速)
│   │   ├── Top 3 催化剂
│   │   ├── Top 3 风险
│   │   └── 操作建议（入场/止损/仓位）
│   └── 格式: HTML + Markdown
│
├── 📊 Investment Memo（投资备忘录，5-8页）
│   ├── 用途: 完整投资案例
│   ├── 读者: 自己（存档）+ 可分享给他人
│   ├── 内容:
│   │   ├── Executive Summary
│   │   ├── 公司概览 + 业务分析
│   │   ├── 投资论文（完整版，含 Bull/Base/Bear 三种情景）
│   │   ├── 财务分析（指标趋势 + 行业对比）
│   │   ├── 估值分析（PE/PB 分位 + 行业比较）
│   │   ├── 量化验证结果（Validation Score + 因子分析）
│   │   ├── 风险评估矩阵
│   │   └── 操作计划（仓位 + 加减仓条件）
│   └── 格式: HTML + Markdown
│
└── 📕 Equity Research Report（个股研究报告，12-18页）
    ├── 用途: 深度研究存档
    ├── 读者: 自己（深度研究）+ 作品集展示
    ├── 内容:
    │   ├── Cover Page
    │   ├── Table of Contents
    │   ├── Executive Summary（1页摘要）
    │   ├── Company Overview（公司概览、商业模式、竞争优势）
    │   ├── Industry Analysis（行业分析、产业链、竞争格局）
    │   ├── Investment Thesis（完整投资论文 + 情景分析）
    │   ├── Financial Analysis（三表分析、DuPont 分解、质量评估）
    │   ├── Valuation（DCF 框架 + PE/PB 分位 + 情景敏感度）
    │   ├── Quant Validation（因子映射、策略回测、验证评分）
    │   ├── Risk Assessment（风险矩阵、压力测试、监控指标）
    │   ├── Recommendation（评级、目标价、仓位、操作计划）
    │   └── Appendix（数据来源、方法论、免责声明）
    └── 格式: HTML + Markdown
```

### 8.3 报告生成流程

```
┌─────────────────────────────────────────────┐
│         Report Generation Pipeline           │
├─────────────────────────────────────────────┤
│                                              │
│  1. Data Gathering                           │
│     ├── Memory System → 相关 Thesis/Decision│
│     ├── Company Intelligence → 基本面数据    │
│     ├── Quant Validation → 验证结果          │
│     └── Quant Engine → 因子 + 回测数据       │
│                                              │
│  2. Data Assembly                            │
│     └── ReportDataBundle: 统一数据结构        │
│                                              │
│  3. Template Selection                       │
│     └── brief | memo | research              │
│                                              │
│  4. Rendering                                │
│     ├── Jinja2 模板引擎                      │
│     ├── Plotly → 内嵌图表 (HTML)             │
│     └── Markdown → GFM 格式                  │
│                                              │
│  5. Output                                   │
│     ├── HTML: 浏览器查看 + 打印              │
│     ├── Markdown: 文件保存 + Git 版本控制     │
│     └── (PDF: V4, 通过浏览器打印即可)         │
│                                              │
│  6. Link to Memory                           │
│     └── 报告路径写入 MemoryEntry.report_path │
│                                              │
└─────────────────────────────────────────────┘
```

### 8.4 模板设计系统

```
templates/v3/reports/
├── base/
│   ├── base.html.jinja2          # HTML 基础框架
│   ├── base.md.jinja2            # Markdown 基础框架
│   └── lxl_theme.css             # LXL Equity Research Lab 品牌样式
│
├── components/
│   ├── cover_page.jinja2         # 封面页
│   ├── metric_card.jinja2        # KPI 指标卡片
│   ├── metric_table.jinja2       # 财务指标表
│   ├── comparison_table.jinja2   # 行业对比表
│   ├── trend_chart.jinja2        # Plotly 趋势图
│   ├── risk_matrix.jinja2        # 风险矩阵
│   ├── scenario_table.jinja2     # 情景分析表
│   ├── factor_radar.jinja2       # 因子雷达图
│   ├── callout.jinja2            # 重点提示框
│   └── disclaimer.jinja2         # 免责声明
│
├── brief/
│   └── executive_brief.html.jinja2
│
├── memo/
│   └── investment_memo.html.jinja2
│
└── research/
    └── equity_research.html.jinja2
```

### 8.5 文件清单

```
src/v3/report/
├── __init__.py
├── generator.py            # ReportGenerator: 统一入口
├── assembler.py            # DataAssembler: 从各模块聚合数据
├── types/
│   ├── __init__.py
│   ├── brief.py            # BriefReport: 执行摘要数据组装
│   ├── memo.py             # MemoReport: 投资备忘录数据组装
│   └── research.py         # ResearchReport: 个股研报数据组装
└── contracts.py            # ReportDataBundle, ReportType, ReportFormat
```

---

## 9. Database Design

### 9.1 数据库策略

```
V2 数据库 (10个)           V3 新数据库 (1个)
├── trades.db               ┌── lxl_v3.db ──────────────────────┐
├── backtest_results.db     │                                    │
├── research_notes.db       │  memory_entries     (Module 1)     │
├── strategy_catalog.db     │  fundamental_snapshots (Module 2)  │
├── factor_analysis.db      │  fundamental_series   (Module 2)   │
├── portfolio_analytics.db  │  research_projects    (Module 3)   │
├── data_catalog.db         │  validation_results   (Module 4)   │
├── quality_metrics.db      │  report_archive       (Module 5)   │
├── financial_series.db     │                                    │
└── market_metadata.db      └────────────────────────────────────┘

原则: V2 数据库不动不碰。V3 只用 1 个新数据库。
```

### 9.2 `lxl_v3.db` 完整 Schema

```sql
-- ============================================================
-- lxl_v3.db: V3 唯一新数据库
-- ============================================================

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- -----------------------------------------------------------
-- Module 1: memory_entries — 统一记忆表
-- -----------------------------------------------------------
CREATE TABLE memory_entries (
    entry_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_type   TEXT NOT NULL CHECK (entry_type IN (
                    'note', 'thesis', 'decision', 'reflection'
                 )),
    date         TEXT NOT NULL,
    title        TEXT NOT NULL,
    content      TEXT NOT NULL,             -- Markdown body

    -- 关联
    symbols      TEXT NOT NULL DEFAULT '[]',   -- JSON array
    tags         TEXT NOT NULL DEFAULT '[]',   -- JSON array
    project_id   TEXT,                         -- FK → research_projects
    related_ids  TEXT NOT NULL DEFAULT '[]',   -- JSON array of entry_ids

    -- Thesis 字段
    thesis_conviction    REAL,
    thesis_catalysts     TEXT,                -- JSON array
    thesis_risks         TEXT,                -- JSON array
    thesis_timeline      TEXT,
    target_price         REAL,
    pipeline_snapshot    TEXT,                -- JSON blob
    report_path          TEXT,

    -- Decision 字段
    decision_type        TEXT,                -- buy | sell | hold
    decision_price       REAL,
    decision_quantity    REAL,
    decision_reason      TEXT,
    market_context       TEXT,
    mood                 TEXT,

    -- 结果追踪
    outcome_status       TEXT DEFAULT 'pending',  -- pending | correct | wrong | expired | partial
    outcome_detail       TEXT,
    outcome_return       REAL,
    reviewed_at          TEXT,

    created_at   TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at   TEXT
);

CREATE INDEX idx_memory_type    ON memory_entries(entry_type);
CREATE INDEX idx_memory_date    ON memory_entries(date);
CREATE INDEX idx_memory_outcome ON memory_entries(outcome_status);
CREATE INDEX idx_memory_project ON memory_entries(project_id);
CREATE INDEX idx_memory_symbols ON memory_entries(symbols);

-- FTS5 全文搜索
CREATE VIRTUAL TABLE memory_fts USING fts5(
    title, content, tags, symbols,
    content='memory_entries', content_rowid='rowid'
);

-- FTS 同步触发器 (INSERT/UPDATE/DELETE)
CREATE TRIGGER memory_ai AFTER INSERT ON memory_entries BEGIN
    INSERT INTO memory_fts(rowid, title, content, tags, symbols)
    VALUES (new.rowid, new.title, new.content, new.tags, new.symbols);
END;
CREATE TRIGGER memory_ad AFTER DELETE ON memory_entries BEGIN
    INSERT INTO memory_fts(memory_fts, rowid, title, content, tags, symbols)
    VALUES ('delete', old.rowid, old.title, old.content, old.tags, old.symbols);
END;
CREATE TRIGGER memory_au AFTER UPDATE ON memory_entries BEGIN
    INSERT INTO memory_fts(memory_fts, rowid, title, content, tags, symbols)
    VALUES ('delete', old.rowid, old.title, old.content, old.tags, old.symbols);
    INSERT INTO memory_fts(rowid, title, content, tags, symbols)
    VALUES (new.rowid, new.title, new.content, new.tags, new.symbols);
END;


-- -----------------------------------------------------------
-- Module 2: fundamental_snapshots — 基本面快照
-- -----------------------------------------------------------
CREATE TABLE fundamental_snapshots (
    symbol       TEXT NOT NULL,
    report_date  TEXT NOT NULL,             -- 报告期 "2024-12-31"

    -- 估值
    pe_ttm       REAL,
    pb           REAL,

    -- 盈利
    roe_ttm      REAL,
    gross_margin REAL,
    net_margin   REAL,

    -- 增长
    revenue_yoy  REAL,
    earnings_yoy REAL,

    -- 健康
    debt_to_equity REAL,

    -- 行情快照
    close_price  REAL,
    market_cap   REAL,                     -- 亿元

    -- 行业
    industry_sw  TEXT,                     -- 申万一级行业

    created_at   TEXT NOT NULL DEFAULT (datetime('now','localtime')),

    PRIMARY KEY (symbol, report_date)
);

CREATE INDEX idx_fs_industry ON fundamental_snapshots(industry_sw);

-- 基本面时序表
CREATE TABLE fundamental_series (
    symbol     TEXT NOT NULL,
    indicator  TEXT NOT NULL,              -- pe_ttm | pb | roe_ttm | revenue_yoy | earnings_yoy | gross_margin | net_margin
    date       TEXT NOT NULL,
    value      REAL NOT NULL,

    PRIMARY KEY (symbol, indicator, date)
);


-- -----------------------------------------------------------
-- Module 3: research_projects — 研究项目
-- -----------------------------------------------------------
CREATE TABLE research_projects (
    project_id   TEXT PRIMARY KEY,          -- "proj-000858-20260806"
    symbol       TEXT NOT NULL,
    name         TEXT NOT NULL,             -- "五粮液"
    description  TEXT DEFAULT '',
    status       TEXT NOT NULL DEFAULT 'active',  -- active | archived | completed
    created_at   TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at   TEXT
);

CREATE INDEX idx_projects_symbol ON research_projects(symbol);
CREATE INDEX idx_projects_status ON research_projects(status);


-- -----------------------------------------------------------
-- Module 4: validation_results — 验证结果
-- -----------------------------------------------------------
CREATE TABLE validation_results (
    validation_id TEXT PRIMARY KEY,         -- UUID
    thesis_id     INTEGER NOT NULL REFERENCES memory_entries(entry_id),
    project_id    TEXT REFERENCES research_projects(project_id),
    symbol        TEXT NOT NULL,

    score         INTEGER NOT NULL,         -- 0-100
    verdict       TEXT NOT NULL,            -- STRONG | PASS | WEAK | FAIL
    breakdown     TEXT NOT NULL,            -- JSON: {performance, logic, robustness, risk}
    pipeline_data TEXT NOT NULL,            -- JSON: 完整管线输出快照
    suggestions   TEXT,                     -- JSON: 改进建议列表

    created_at    TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE INDEX idx_validation_thesis ON validation_results(thesis_id);
CREATE INDEX idx_validation_project ON validation_results(project_id);
CREATE INDEX idx_validation_symbol ON validation_results(symbol);


-- -----------------------------------------------------------
-- Module 5: report_archive — 报告存档
-- -----------------------------------------------------------
CREATE TABLE report_archive (
    report_id     TEXT PRIMARY KEY,         -- UUID
    project_id    TEXT REFERENCES research_projects(project_id),
    symbol        TEXT NOT NULL,
    report_type   TEXT NOT NULL,            -- brief | memo | research
    report_format TEXT NOT NULL,            -- html | markdown
    file_path     TEXT NOT NULL,            -- 本地文件路径
    title         TEXT NOT NULL,
    created_at    TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE INDEX idx_report_project ON report_archive(project_id);
CREATE INDEX idx_report_symbol ON report_archive(symbol);
```

### 9.3 数据关系图

```
research_projects (1) ──────────< (N) memory_entries
       │                                    │
       │                                    │ (thesis type)
       │                                    │
       │                            validation_results (N:1)
       │
       ├─── fundamental_snapshots (N:1 by symbol)
       ├─── fundamental_series    (N:1 by symbol)
       └─── report_archive        (N:1 by project)
```

---

## 10. Page Architecture

### 10.1 页面总览

```
V3 页面 (5个)
├── /workspace          Dashboard 首页 + 统一 Shell
├── /workspace/:id      单个 Research Project 详情
├── /journal            记忆日记（日历 + 列表 + 搜索）
├── /companies          公司智能浏览器
└── /companies/:symbol  单个公司智能报告

V2 页面 (保持，增加统一导航栏)
├── /pipeline           AI 研究管线
├── /portfolio          投资组合仪表盘
├── /cases              研究案例存档
├── /terminal           AI 研究终端
└── /login              登录页
```

### 10.2 导航结构

```
┌──────────────────────────────────────────────────────────────┐
│  [LXL·QuantAxis V3]    Workspace  Pipeline  Journal  Companies│
│                                                               │
│  ←── 全局导航，所有页面可见 ──→                                │
│                                                               │
│  [Workspace]    = Dashboard + Project 管理                    │
│  [Pipeline]     = AI 研究管线 (V2)                            │
│  [Journal]      = 记忆日记 (V3)                               │
│  [Companies]    = 公司智能 (V3)                               │
│  [Portfolio]    = 投资组合 (V2) — 右上角小图标入口             │
│  [Cases]        = 研究案例 (V2) — 右上角小图标入口             │
└──────────────────────────────────────────────────────────────┘
```

### 10.3 页面详情

#### `/workspace` — Dashboard 首页

```
┌─────────────────────────────────────────────────────────────┐
│  KPI 行: 活跃项目 | 论文命中率 | 待复盘 | 本周论文 | 连续记录  │
├─────────────────────────────────────────────────────────────┤
│  ┌─ Quick Actions ───┐  ┌─ Recent Activity ──────────────┐ │
│  │ [新项目] [写论文]   │  │ 时间线: 论文创建/决策/复盘      │ │
│  │ [写笔记] [跑管线]   │  │                                │ │
│  └────────────────────┘  └────────────────────────────────┘ │
│  ┌─ Memory Insights ──┐  ┌─ Pending Reviews ─────────────┐ │
│  │ 信心校准 + 板块表现  │  │ 待复盘论文列表                  │ │
│  └────────────────────┘  └────────────────────────────────┘ │
│  ┌─ Recent Lessons ──────────────────────────────────────┐ │
│  │ 最近 5 条 Reflection                                   │ │
│  └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

#### `/workspace/:id` — Project 详情

```
┌─────────────────────────────────────────────────────────────┐
│  左侧: 项目列表                         右侧: 项目详情       │
│  ┌──────────────────┐  ┌──────────────────────────────────┐│
│  │ 🔍 搜索项目       │  │ 000858 五粮液  🟢 Active          ││
│  │                   │  │                                  ││
│  │ 🟢 五粮液         │  │ [Overview] [Thesis] [Validat.]  ││
│  │ 🟢 中芯国际       │  │ [Journal] [Reports]              ││
│  │ 🟡 茅台           │  │                                  ││
│  │ ⚪ 药明康德       │  │ Tab 内容根据选择动态切换:         ││
│  │ 🔒 宁德时代       │  │ Overview → Company Intel + 摘要  ││
│  │                   │  │ Thesis   → 该项目的论文列表       ││
│  │ [+ 新建项目]      │  │ Validat. → 验证结果 + 回测图表    ││
│  └──────────────────┘  │ Journal  → 该标的的记忆条目         ││
│                         │ Reports  → 已生成报告列表          ││
│                         └──────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

#### `/journal` — 记忆日记

```
┌─────────────────────────────────────────────────────────────┐
│  [+ New Entry]  [搜索: _____]  [筛选: 全部▼]  [标的: ___]   │
├─────────────────────────────────────────────────────────────┤
│  ┌─ 日历视图 ───────────────────────────────────────────┐  │
│  │     August 2026                          ◀ ▶        │  │
│  │  Mo  Tu  We  Th  Fr  Sa  Su                         │  │
│  │  ...  ...  ●   ●   ●   ...  ...                      │  │
│  │       thesis decision note                            │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌─ 条目列表 ───────────────────────────────────────────┐  │
│  │                                                       │  │
│  │  💡 Thesis · Aug 6                                     │  │
│  │  五粮液：消费复苏 + 估值修复                              │  │
│  │  000858 · conviction 0.7 · pending review               │  │
│  │                                                       │  │
│  │  📊 Decision · Aug 5                                   │  │
│  │  买入中芯国际 — 芯片周期底部                               │  │
│  │  688981 @ ¥58 · 5000 股                                 │  │
│  │                                                       │  │
│  │  📝 Note · Aug 4                                       │  │
│  │  消费板块 Q2 财报总结                                    │  │
│  │                                                       │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

#### `/companies` — 公司智能浏览器

```
┌─────────────────────────────────────────────────────────────┐
│  [搜索股票: 代码或名称__________] [行业筛选: 全部▼]          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─ 已研究公司 ──────────────────────────────────────────┐ │
│  │                                                        │ │
│  │ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │ │
│  │ │ 五粮液    │ │ 中芯国际  │ │ 茅台      │ │ 药明康德  │  │ │
│  │ │ 000858   │ │ 688981   │ │ 600519   │ │ 603259   │  │ │
│  │ │ PE 25.3  │ │ PE 45.2  │ │ PE 30.1  │ │ PE 22.8  │  │ │
│  │ │ ROE 24.8%│ │ ROE 8.2% │ │ ROE 32.1%│ │ ROE 18.5%│  │ │
│  │ │ 消费     │ │ 科技     │ │ 消费     │ │ 医疗     │  │ │
│  │ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌─ 快速搜索 ────────────────────────────────────────────┐ │
│  │ 输入任意 A 股代码，实时拉取公司智能数据                    │ │
│  │ [股票代码: _______________] [查询]                      │ │
│  └──────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## 11. API Design

### 11.1 API 策略

- **不创建新 API 版本**（不搞 `/api/v3/`）
- **直接在 `web_modern.py` 上增加路由**
- **所有 V2 API 保持不变**

### 11.2 V3 新增 API 路由

#### Memory API

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/memory/list` | 列表（支持 type/date/symbols/tags/outcome 筛选） |
| `GET` | `/api/memory/search?q=` | FTS5 全文搜索 |
| `POST` | `/api/memory/create` | 创建记忆条目 |
| `GET` | `/api/memory/<id>` | 获取详情 |
| `PUT` | `/api/memory/<id>` | 更新条目 |
| `DELETE` | `/api/memory/<id>` | 删除条目 |
| `POST` | `/api/memory/<id>/review` | 复盘（标记 outcome） |
| `GET` | `/api/memory/analytics` | Memory Analytics 数据 |
| `GET` | `/api/memory/pending-reviews` | 待复盘列表 |

#### Company Intelligence API

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/companies/search?q=` | 股票搜索（代码/名称） |
| `GET` | `/api/companies/<symbol>` | 公司完整智能数据 |
| `GET` | `/api/companies/<symbol>/fundamentals` | 财务指标 |
| `GET` | `/api/companies/<symbol>/series?indicator=` | 历史序列（PE/PB/ROE/...） |
| `GET` | `/api/companies/<symbol>/peers` | 行业对比 |
| `GET` | `/api/companies/<symbol>/valuation` | 估值分析 |

#### Workspace API

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/workspace/dashboard` | Dashboard 聚合数据 |
| `GET` | `/api/workspace/projects` | 项目列表 |
| `POST` | `/api/workspace/projects` | 创建项目 |
| `GET` | `/api/workspace/projects/<id>` | 项目详情（聚合所有模块数据） |
| `PUT` | `/api/workspace/projects/<id>` | 更新项目 |
| `DELETE` | `/api/workspace/projects/<id>` | 归档项目 |

#### Validation API

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/validation/run` | 运行验证管线 |
| `GET` | `/api/validation/results/<id>` | 验证结果详情 |
| `GET` | `/api/validation/history?symbol=` | 某标的的验证历史 |

#### Report API

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/report/generate` | 生成报告 |
| `GET` | `/api/report/list` | 报告列表 |
| `GET` | `/api/report/<id>` | 报告详情 |
| `GET` | `/api/report/<id>/view` | 浏览器查看 HTML 报告 |
| `GET` | `/api/report/<id>/download` | 下载 Markdown 报告 |

### 11.3 请求/响应示例

```json
// POST /api/memory/create
// Request:
{
  "entry_type": "thesis",
  "date": "2026-08-06",
  "title": "五粮液：消费复苏 + 估值修复",
  "content": "## 投资逻辑\n\n五粮液受益于消费复苏...",
  "symbols": ["000858"],
  "tags": ["消费", "白酒", "价值"],
  "project_id": "proj-000858-20260806",
  "thesis_conviction": 0.7,
  "thesis_catalysts": ["Q3消费旺季", "估值修复"],
  "thesis_risks": ["政策风险", "竞争加剧"],
  "target_price": 180.0
}

// Response:
{
  "entry_id": 42,
  "status": "created"
}
```

```json
// GET /api/companies/000858
// Response:
{
  "symbol": "000858",
  "name": "五粮液",
  "profile": {
    "full_name": "宜宾五粮液股份有限公司",
    "industry_sw_l1": "食品饮料",
    "market_cap": 5820,
    "listed_date": "1998-04-27"
  },
  "metrics": {
    "pe_ttm": 25.3,
    "pb": 5.2,
    "roe_ttm": 0.248,
    "revenue_yoy": 0.153,
    "earnings_yoy": 0.182
  },
  "valuation_rating": "fair",
  "peers": {
    "industry": "食品饮料",
    "peer_count": 47,
    "rankings": {
      "roe": {"value": 0.248, "rank": 5, "percentile": 0.89},
      "pe_ttm": {"value": 25.3, "rank": 18, "percentile": 0.38}
    }
  }
}
```

---

## 12. File Structure

### 12.1 完整目录结构

```
PythonProject1/
│
├── src/
│   ├── lxl_quantaxis/             # V2: 不动 (155 文件)
│   │   ├── factor/registry/       #    仅追加 1 行: import v3 因子
│   │   ├── research/application.py #   仅追加 ~20 行: Memory 钩子
│   │   └── ...
│   │
│   └── v3/                        # ★ V3: 所有新代码
│       ├── __init__.py
│       │
│       ├── memory/                # Module 1: Investment Memory System
│       │   ├── __init__.py
│       │   ├── models.py          # MemoryEntry
│       │   ├── repository.py      # MemoryRepository
│       │   ├── search.py          # MemorySearch
│       │   ├── analytics.py       # MemoryAnalytics
│       │   ├── review.py          # ReviewEngine
│       │   └── schema.sql         # DDL
│       │
│       ├── intelligence/          # Module 2: Company Intelligence Engine
│       │   ├── __init__.py
│       │   ├── contracts.py       # CompanyProfile, FundamentalSnapshot, etc.
│       │   ├── fetcher.py         # CompanyIntelligenceFetcher
│       │   ├── analyzer.py        # CompanyAnalyzer
│       │   ├── storage.py         # IntelligenceStorage
│       │   └── factor_bridge.py   # 7 基本面因子
│       │
│       ├── workspace/             # Module 3: Research Workspace
│       │   ├── __init__.py
│       │   ├── models.py          # ResearchProject
│       │   ├── service.py         # WorkspaceService
│       │   ├── aggregator.py      # ProjectAggregator
│       │   └── dashboard.py       # DashboardData
│       │
│       ├── validation/            # Module 4: Quant Validation Engine
│       │   ├── __init__.py
│       │   ├── contracts.py       # ValidationResult, LogicFragment
│       │   ├── scorer.py          # ValidationScorer
│       │   └── decomposer.py      # LogicDecomposer
│       │
│       ├── report/                # Module 5: Research Report Generator
│       │   ├── __init__.py
│       │   ├── contracts.py       # ReportDataBundle
│       │   ├── generator.py       # ReportGenerator
│       │   ├── assembler.py       # DataAssembler
│       │   └── types/
│       │       ├── __init__.py
│       │       ├── brief.py
│       │       ├── memo.py
│       │       └── research.py
│       │
│       └── db.py                  # V3 数据库初始化（建库建表）
│
├── templates/
│   └── v3/                        # ★ V3: 所有新模板
│       ├── workspace/
│       │   ├── dashboard.html
│       │   └── project_detail.html
│       ├── journal.html
│       ├── companies.html
│       ├── company_detail.html
│       └── reports/
│           ├── base/
│           │   ├── base.html.jinja2
│           │   └── lxl_theme.css
│           ├── components/
│           │   ├── metric_card.jinja2
│           │   ├── comparison_table.jinja2
│           │   ├── trend_chart.jinja2
│           │   ├── risk_matrix.jinja2
│           │   └── callout.jinja2
│           ├── brief/
│           │   └── executive_brief.html.jinja2
│           ├── memo/
│           │   └── investment_memo.html.jinja2
│           └── research/
│               └── equity_research.html.jinja2
│
├── static/
│   └── css/
│       └── v3/
│           └── v3-shell.css        # ★ V3: 导航栏 + 布局样式
│
├── tests/
│   └── v3/                         # ★ V3: 测试
│       ├── test_memory.py
│       ├── test_intelligence.py
│       ├── test_workspace.py
│       ├── test_validation.py
│       └── test_report.py
│
├── docs/
│   ├── V3_PRODUCT_ARCHITECTURE.md  # ★ 本文档
│   ├── V3_MVP_SPEC.md
│   ├── ARCHITECTURE_V3.md
│   └── ARCHITECTURE_V3_SCOPING.md
│
├── web_modern.py                   # MODIFIED: +V3 路由 + 导航栏注入
├── pyproject.toml                  # 不变（零新依赖）
└── requirements.txt                # 不变
```

### 12.2 代码量预估

```
Module 1 (memory):      6 files  ~600 行
Module 2 (intelligence): 6 files  ~800 行
Module 3 (workspace):    5 files  ~400 行
Module 4 (validation):   4 files  ~350 行
Module 5 (report):       7 files  ~500 行
Database (db.py):        1 file   ~80 行
─────────────────────────────────────
Python 合计:            29 files  ~2,730 行

Templates:              15 files  ~800 行
CSS:                     1 file   ~100 行
Tests:                   5 files  ~500 行
web_modern.py diff:                ~200 行
─────────────────────────────────────
总计:                   ~50 files  ~4,330 行
```

---

## 13. Development Roadmap

### 13.1 四阶段 · 八周

```
Week │ Phase │ Module               │ Deliverable
─────┼───────┼───────────────────────┼─────────────────────────────
  1  │   1   │ Memory System        │ 记忆 CRUD + FTS5 搜索
  2  │   1   │ Memory System        │ Analytics + Review + /journal 页面
─────┼───────┼───────────────────────┼─────────────────────────────
  3  │   2   │ Company Intelligence │ 财报拉取 + 指标计算 + 行业分类
  4  │   2   │ Company Intelligence │ 因子桥接 + /companies 页面
─────┼───────┼───────────────────────┼─────────────────────────────
  5  │   3   │ Workspace + Report   │ Project 系统 + /workspace 页面
  6  │   3   │ Workspace + Report   │ 报告生成 + Report 模板
─────┼───────┼───────────────────────┼─────────────────────────────
  7  │   4   │ Validation + Polish  │ 验证评分 + 管线集成优化
  8  │   4   │ Integration + Release│ 端到端测试 + 文档 + v3.0.0 发布
```

### 13.2 每阶段可独立部署

```
Phase 1 完成 → /journal 页面可用，Memory 系统工作
Phase 2 完成 → /companies 页面可用，基本面数据可用
Phase 3 完成 → /workspace 页面可用，报告生成可用
Phase 4 完成 → 验证引擎可用，全系统集成
```

### 13.3 依赖关系

```
Phase 1 (Memory)      — 无依赖，独立
Phase 2 (Intelligence) — 无依赖，独立（可与 Phase 1 并行）
Phase 3 (Workspace)    — 依赖 Phase 1 (Memory) + Phase 2 (Intelligence)
Phase 3 (Report)       — 依赖 Phase 1 + Phase 2
Phase 4 (Validation)   — 依赖 Phase 1 + Phase 2 + V2 Pipeline
```

---

## 14. Commit Plan

### 14.1 Phase 1: Memory System（Week 1-2, 14 commits）

```
Week 1: Data Layer
  feat(v3): initialize src/v3/ package structure
  feat(memory): add MemoryEntry dataclass and schema.sql
  feat(memory): add MemoryRepository — CRUD with FTS5 search
  feat(memory): add MemorySearch — advanced query engine
  feat(memory): add MemoryAnalytics — hit rate, calibration, tags
  feat(memory): add ReviewEngine — pending review detection and outcome tracking
  feat(v3): add lxl_v3.db auto-initialization (db.py)

Week 2: Web Layer
  feat(web): add /api/memory/* routes — list, search, create, detail, update, delete, review, analytics
  feat(web): add /journal page — calendar + entry list + search + filter
  feat(web): add journal entry editor — create/edit modal with Markdown
  feat(web): add /workspace page — dashboard with KPI tiles and recent activity
  feat(research): add memory hook to pipeline — auto-save thesis after pipeline completion
  test(memory): add memory module unit tests
  docs: update CHANGELOG with Phase 1 completion
```

### 14.2 Phase 2: Company Intelligence（Week 3-4, 12 commits）

```
Week 3: Data Layer
  feat(intelligence): add CompanyProfile, FundamentalSnapshot, FundamentalSeries contracts
  feat(intelligence): add CompanyIntelligenceFetcher — akshare multi-endpoint aggregation
  feat(intelligence): add IntelligenceStorage — cache fundamental data to lxl_v3.db
  feat(intelligence): add CompanyAnalyzer — valuation rating, risk detection, trend analysis
  feat(intelligence): add fundamental factor bridge — register 7 factors to V2 registry

Week 4: Web Layer
  feat(web): add /api/companies/* routes — search, detail, fundamentals, series, peers, valuation
  feat(web): add /companies page — studied companies grid + quick search
  feat(web): add /companies/<symbol> page — full company intelligence report
  feat(web): add Plotly trend charts — PE/PB/ROE 5-year history
  style(web): add v3-shell.css — unified navigation bar and layout
  test(intelligence): add intelligence module unit tests
  docs: update CHANGELOG with Phase 2 completion
```

### 14.3 Phase 3: Workspace + Report（Week 5-6, 14 commits）

```
Week 5: Workspace + Report Backend
  feat(workspace): add ResearchProject model and WorkspaceService
  feat(workspace): add ProjectAggregator — cross-module data aggregation
  feat(workspace): add DashboardData — KPI calculation for homepage
  feat(report): add ReportGenerator and DataAssembler
  feat(report): add ExecutiveBrief type — data assembly logic
  feat(report): add InvestmentMemo type — data assembly logic
  feat(report): add EquityResearchReport type — data assembly logic

Week 6: Web Layer
  feat(web): add /api/workspace/* routes — dashboard, projects CRUD
  feat(web): add /workspace/:id page — project detail with tab switching
  feat(web): add /api/report/* routes — generate, list, view, download
  feat(templates): add report base + component templates
  feat(templates): add brief/memo/research HTML templates
  feat(web): add V3 navigation bar to all V2 pages via context_processor
  docs: update CHANGELOG with Phase 3 completion
```

### 14.4 Phase 4: Validation + Polish（Week 7-8, 12 commits）

```
Week 7: Validation Engine
  feat(validation): add ValidationResult and LogicFragment contracts
  feat(validation): add LogicDecomposer — thesis → verifiable sub-logics
  feat(validation): add ValidationScorer — multi-dimensional scoring engine
  feat(web): add /api/validation/* routes — run, results, history
  feat(web): add validation results display in project detail page

Week 8: Integration + Release
  test: add end-to-end tests — full user journey
  test: add integration tests — cross-module data flow
  fix: edge cases, error handling, data staleness checks
  chore: ensure all V2 tests still pass (CI gate)
  docs: write V3 user guide and developer documentation
  docs: write RELEASE_NOTES_v3.0.0.md
  chore: bump version to 3.0.0, create git tag
```

### 14.5 Commit 统计

```
Phase 1: 14 commits
Phase 2: 12 commits
Phase 3: 14 commits
Phase 4: 12 commits
           ──
Total:    52 commits
```

---

## 15. Design Decisions

### 15.1 产品决策

| # | 决策 | 理由 |
|---|------|------|
| **P1** | 定位为"研究操作系统"而非"预测工具" | 预测工具 = 黑箱 = 用户不信任。研究 OS = 白箱 = 用户掌控。差异化定位 |
| **P2** | 六个环节形成闭环 | 单次管线 = 用完即走。闭环 = 用户留存 + 数据积累 + 系统进化 |
| **P3** | 一个股票 = 一个 Research Project | Notion 式组织逻辑，用户直觉理解。降低认知负担 |
| **P4** | 四种记忆类型统一一张表 | 简单 > 灵活。一张表 + entry_type = 3 张表 80% 的功能，1/3 的代码量 |
| **P5** | Validation Score 而非 Prediction Score | 验证逻辑 > 预测涨跌。可解释 > 高准确率。白箱 > 黑箱 |

### 15.2 技术决策

| # | 决策 | 理由 |
|---|------|------|
| **T1** | `src/v3/` 独立目录 | V2 代码零修改。新旧隔离。清理容易 |
| **T2** | 1 个新数据库 `lxl_v3.db` | 16 个数据库是维护噩梦。1 个数据库够用 |
| **T3** | Flask only，不加 FastAPI | 重写框架 = 零价值工作量。Flask 3.x 完全够用 |
| **T4** | 零新依赖 | akshare/flask/plotly/jinja2 全部已有 |
| **T5** | Jinja2 模板而非 React SPA | 服务端渲染 = 零 JS 构建。个人项目不需要 SPA |
| **T6** | HTML + Markdown 输出，不做 PDF | 浏览器打印 = 零开发成本。PDF 引擎增加复杂度 |

### 15.3 金融逻辑决策

| # | 决策 | 理由 |
|---|------|------|
| **F1** | PE 分位数用 5 年窗口 | 覆盖一个完整市场周期。1 年太短，10 年数据不可得 |
| **F2** | 申万行业分类作为行业基准 | akshare 原生支持。A 股研究标准分类 |
| **F3** | 验证评分四维加权（绩效 40% + 逻辑 30% + 因子 20% + 风险 10%） | 绩效重要但不是全部。逻辑一致性防止过拟合 |
| **F4** | 信心度由用户自评（非 AI 判断） | 信心是主观的。AI 判断信心 = 循环论证。用户自评 → 系统追踪校准 |
| **F5** | Thesis 必须有关闭条件（时间框架/目标价/止损） | 没有关闭条件的论文无法判断对错。可验证 = 论文的必要条件 |

---

## 附录 A: 不做清单 (V3 Scope Boundary)

```
═══════════════════════════════════════════════════════
V3 MVP 明确不做
═══════════════════════════════════════════════════════

AI 系统:
  ✗ Multi-Agent 框架
  ✗ Agent 自动选股
  ✗ Agent 调度与编排
  ✗ Custom Agent DSL

基础设施:
  ✗ FastAPI 迁移
  ✗ Redis 事件总线
  ✗ Docker 容器化
  ✗ Prometheus 监控

回测:
  ✗ Point-in-Time 数据门户
  ✗ 多资产组合回测
  ✗ Barra 风险模型
  ✗ 贝叶斯/遗传优化

数据:
  ✗ 美股/港股基本面
  ✗ 宏观数据 (CPI/PMI/M2)
  ✗ 另类数据
  ✗ 分析师一致预期

报告:
  ✗ PDF 渲染引擎
  ✗ Excel 导出
  ✗ Email 分发

用户:
  ✗ RBAC 多角色
  ✗ OAuth2/SSO
  ✗ 审计日志合规

═══════════════════════════════════════════════════════
以上全部进入 V4 评估队列
═══════════════════════════════════════════════════════
```

---

> **本文档为 V3.0 产品架构权威来源。所有设计决策、模块边界、数据模型均以此为准。**  
> **实施时遇到模棱两可处，回查本文档的产品愿景和设计决策章节。**  
> **下一份输出: 按 Phase 1 开始实施 Memory System。**
