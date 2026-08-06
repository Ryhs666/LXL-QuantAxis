# LXL·QuantAxis V3 — Investment Command Center

> **投资决策与成长操作系统**  
> 不只是管理工作。是记录你如何思考、如何决策、如何进化。

**Status**: FINAL DESIGN — 实施基准  
**Supersedes**: All previous workspace specs  
**Base**: V3 Memory System (Phase 1)

---

## 目录

**Part I: Foundation（基础架构）**

1. [产品定位](#1-产品定位)
2. [用户每日投资流程](#2-用户每日投资流程)
3. [页面信息架构](#3-页面信息架构)
4. [Market Context](#4-market-context)
5. [Investment Universe](#5-investment-universe)
6. [Action Center](#6-action-center)
7. [Thesis Board](#7-thesis-board)
8. [Portfolio Intelligence](#8-portfolio-intelligence)
9. [Investor Learning](#9-investor-learning)
10. [Memory 数据映射](#10-memory-数据映射)
11. [页面布局设计](#11-页面布局设计)

**Part II: Cognitive Layer（认知增强层）**

12. [Evidence Architecture](#12-evidence-architecture)
13. [Thesis Version System](#13-thesis-version-system)
14. [Decision Timeline Model](#14-decision-timeline-model)
15. [Conviction Calibration Engine](#15-conviction-calibration-engine)
16. [Investor Growth Metrics](#16-investor-growth-metrics)

**Part III: Implementation（实施计划）**

17. [开发拆分计划](#17-开发拆分计划)

---

## Part I: Foundation

---

## 1. 产品定位

### 1.1 三层定位

```
Layer 1: 投资管理工具
  "管理股票和研究任务"
  → Watchlist, Queue, Thesis Board, Portfolio

Layer 2: 投资决策支持
  "告诉你该做什么决策"
  → Action Center, Priority Engine, Risk Alerts

Layer 3: 投资认知系统          ← NEW
  "记录你如何思考、为什么决策、怎样进化"
  → Evidence, Version Control, Decision Timeline, Calibration
```

### 1.2 六个核心问题 + 四个认知能力

```
六个问题（Part I 回答）:
  Q1: 今天市场发生什么？      → Market Context
  Q2: 我应该关注什么？         → Investment Universe
  Q3: 我现在相信什么？         → Thesis Board
  Q4: 我下一步做什么？         → Action Center
  Q5: 我的组合风险在哪里？     → Portfolio Intelligence
  Q6: 我是否变得更好？         → Investor Learning

四个认知能力（Part II 回答）:
  C1: 我的观点有证据支撑吗？    → Evidence Architecture
  C2: 我的观点如何演变？       → Thesis Version System
  C3: 我的决策如何形成？       → Decision Timeline Model
  C4: 我了解自己的判断力吗？    → Conviction Calibration Engine
```

### 1.3 系统进化路径

```
V2.0:  AI Research Pipeline
       "验证一个投资想法"

V3 Phase 1:  Investment Memory System
             "记住我研究过什么"

V3 Phase 2:  Investment Command Center
             "告诉我该做什么"       ← 当前 spec

V3 Phase 2+: Investment Decision & Growth OS
             "理解我如何思考和进化"  ← 本次升级
```

---

## 2. 用户每日投资流程

*(保持原有内容)*

---

## 3. 页面信息架构

*(保持原有三行布局: ROW 1 Context+Universe, ROW 2 Beliefs+Actions, ROW 3 Portfolio+Learning)*

---

## 4. Market Context

*(保持原有设计)*

---

## 5. Investment Universe

*(保持原有设计)*

---

## 6. Action Center

*(保持原有 7 条规则)*

---

## 7. Thesis Board

### 7.1 原有四列

*(保持 Forming / Validating / Waiting / Completed)*

### 7.2 新增：证据指示器

每个 Thesis 卡片右下角增加证据状态：

```
┌─────────────────────────────┐
│ 💡 000858 五粮液              │
│ 消费复苏 + 估值修复            │
│ conf: 70% · target: ¥180     │
│                              │
│ Evidence: ●●●○○ (3 supporting, 1 counter)
│ Version: v2 (updated 3d ago)
│                              │
│ [→ View] [→ Edit]            │
└─────────────────────────────┘
```

---

## 8. Portfolio Intelligence

*(保持原有三个维度: Coverage, Concentration, Alignment)*

---

## 9. Investor Learning

*(保持原有四个指标: Hit Rate, Calibration, Decision Quality, Learning Velocity)*

---

## 10. Memory 数据映射

### 10.1 扩展后的数据模型

```
memory_entries (一张表):

  基础字段:
    id, type, ticker, title, content, tags
    confidence, status
    created_at, updated_at

  JSON 扩展字段:
    thesis: {
      # 原有
      catalysts: [...]
      risks: [...]
      target_price: float
      timeline: str

      # NEW: Evidence
      evidence: {
        supporting: [
          {id, description, source, strength, date_added}
        ]
        counter: [
          {id, description, source, strength, date_added}
        ]
      }

      # NEW: Version History
      version_history: [
        {version, date, confidence, change_summary}
      ]

      # 原有
      pipeline_snapshot: {...}
    }

    decision: {
      type, price, quantity, reason
      market_context, mood

      # NEW: Decision context
      trigger: str           # 触发决策的事件
      alternatives_considered: str  # 考虑过的替代方案
    }

    outcome: {
      detail: str
      return_pct: float
      reviewed_at: str

      # NEW: Learning extraction
      lesson_tags: [...]     # 从这次结果中学到的教训标签
      principle_updates: [...] # 更新的投资原则
    }
```

### 10.2 零新表保证

```
所有新增能力的数据 → thesis/decision/outcome JSON blob 扩展
不创建新表。不修改 schema。不需要 migration。

已有 entry 的 thesis JSON 中缺少 evidence/version_history 字段时:
  → 前端显示 "No evidence yet"
  → 向后兼容
```

---

## 11. 页面布局设计

*(保持原有三行布局，Thesis Board 卡片增加证据指示器)*

---

## Part II: Cognitive Layer

---

## 12. Evidence Architecture

### 12.1 定位

> 回答: **"我的观点有证据支撑吗？"**
> 让 Theis 从"我觉得"变成"我有证据表明"。

### 12.2 证据模型

```python
# 存储在 thesis.evidence 中

{
  "supporting": [
    {
      "id": "ev-001",
      "description": "NVIDIA Q2 数据中心营收 +154% YoY",
      "source": "Q2 FY2025 Earnings Report",
      "source_type": "earnings",       # earnings | industry_data | macro | news | research
      "strength": "strong",            # strong | moderate | weak
      "date_added": "2026-07-15",
      "confidence_impact": +0.10       # 对信心的影响
    },
    {
      "id": "ev-002",
      "description": "台积电 CoWoS 产能已被预订至 2026",
      "source": "TSMC supply chain check",
      "source_type": "industry_data",
      "strength": "strong",
      "date_added": "2026-07-16",
      "confidence_impact": +0.05
    }
  ],
  "counter": [
    {
      "id": "ev-003",
      "description": "AMD MI300 性价比优势明显，Google TPU 大规模部署",
      "source": "Competitor analysis",
      "source_type": "industry_data",
      "strength": "moderate",
      "date_added": "2026-07-17",
      "confidence_impact": -0.05
    }
  ]
}
```

### 12.3 证据强度评级

```
strong:   经过验证的定量数据（财报、官方统计）
          产业链多方验证的信息

moderate: 行业报告、分析师一致预期
          单一来源但可信度高的信息

weak:     新闻报道、传闻
          个人观察但未验证的信息
```

### 12.4 证据对信心的影响

```
每添加一条 evidence → 可选地调整 confidence:

  Supporting + strong   → +0.05 ~ +0.15
  Supporting + moderate → +0.02 ~ +0.08
  Supporting + weak     → +0.01 ~ +0.03

  Counter + strong      → -0.10 ~ -0.20
  Counter + moderate    → -0.05 ~ -0.10
  Counter + weak        → -0.01 ~ -0.05

系统不自动调整 confidence。
用户手动确认 confidence 变化。
证据只是记录和提醒。
```

### 12.5 Evidence Board 展示

```
┌─ Evidence: NVIDIA AI Infra Thesis ─────────────────────────┐
│                                                             │
│  Current Confidence: 0.80                                   │
│                                                             │
│  Supporting Evidence (3):                                   │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ 🟢 STRONG  Q2 DC revenue +154% YoY                    │ │
│  │    Source: Q2 FY2025 Earnings Report                   │ │
│  │    Impact: +0.10 · Added: Jul 15                       │ │
│  │                                                        │ │
│  │ 🟢 STRONG  TSMC CoWoS fully booked through 2026        │ │
│  │    Source: TSMC supply chain check                     │ │
│  │    Impact: +0.05 · Added: Jul 16                       │ │
│  │                                                        │ │
│  │ 🟡 MODERATE  Cloud CAPEX growth accelerating            │ │
│  │    Source: Gartner Cloud Spending Forecast             │ │
│  │    Impact: +0.03 · Added: Jul 20                       │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
│  Counter Evidence (1):                                      │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ 🟡 MODERATE  AMD MI300 gaining hyperscaler adoption     │ │
│  │    Source: Competitor analysis                          │ │
│  │    Impact: -0.05 · Added: Jul 17                        │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
│  Net Evidence Impact: +0.13                                 │
│  Evidence Score: ●●●○○ (3S / 1C / 0W)                      │
│                                                             │
│  [+ Add Evidence]                                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 12.6 数据存储

```
全部存储在 memory_entries.thesis JSON blob 中。
不创建新表。

向后兼容:
  thesis.evidence 不存在 → 显示 "No evidence added yet"
  thesis.evidence 存在 → Evidence Board 展示
```

---

## 13. Thesis Version System

### 13.1 定位

> 回答: **"我的观点如何演变？"**
> 类似 Git blame for investment thinking。

### 13.2 为什么需要

```
场景:
  半年后回顾一个成功的投资。
  "我当时为什么看好的？信心从哪来的？中间改过判断吗？"

没有版本控制:
  "我记得好像是...不太确定了"

有版本控制:
  v1 (Jun 15): 初步判断, conf 0.60, 催化剂: AI需求
  v2 (Jul 10): Q2财报后加仓判断, conf 0.75, 新增证据: 财报+154%
  v3 (Aug 01): 看到竞品威胁, conf 0.70, 新增反证: AMD进展
  v4 (Sep 20): 目标价到达, 标记 correct
```

### 13.3 版本模型

```python
# 存储在 thesis.version_history 中

"version_history": [
  {
    "version": 1,
    "date": "2026-06-15",
    "confidence": 0.60,
    "change_summary": "Initial thesis formed after reading NVIDIA Q1 report",
    "change_type": "creation",
    "evidence_added": ["ev-001"],
    "evidence_removed": []
  },
  {
    "version": 2,
    "date": "2026-07-10",
    "confidence": 0.75,
    "change_summary": "Q2 earnings beat expectations. Data center revenue +154% YoY. Raised conviction.",
    "change_type": "confidence_change",
    "evidence_added": ["ev-002"],
    "evidence_removed": []
  },
  {
    "version": 3,
    "date": "2026-08-01",
    "confidence": 0.70,
    "change_summary": "AMD MI300 gaining traction with hyperscalers. Added counter evidence.",
    "change_type": "risk_update",
    "evidence_added": ["ev-003"],
    "evidence_removed": []
  }
]
```

### 13.4 版本触发时机

```
自动创建新版本:
  1. confidence 变化 > 0.05
  2. catalysts 列表变化（新增/移除）
  3. risks 列表变化（新增/移除）
  4. target_price 变化 > 5%
  5. 新增或移除 evidence

版本由系统自动记录。
用户只需要正常编辑 Thesis。
系统检测到实质性变化 → 自动追加 version_history。
```

### 13.5 Version Timeline 展示

```
┌─ Thesis Version History: NVIDIA AI Infra ───────────────────┐
│                                                              │
│  v4  Sep 20  ✅ Marked CORRECT (+41%)                        │
│  │    Outcome: Target reached at $1200                       │
│  │                                                           │
│  v3  Aug 01  ⚠️ Confidence: 0.80 → 0.70                     │
│  │    Added counter evidence: AMD MI300 traction             │
│  │                                                           │
│  v2  Jul 10  🔺 Confidence: 0.60 → 0.75                     │
│  │    Q2 earnings beat. DC +154% YoY.                        │
│  │                                                           │
│  v1  Jun 15  💡 Thesis created                               │
│       Initial thesis. Conviction: 0.60                       │
│       Catalyst: AI demand surge                              │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### 13.6 数据存储

```
全部存储在 memory_entries.thesis.version_history 中。
不创建新表。

每次更新 thesis → 比较前后变化 → 如果触发条件满足 → 追加 version 记录。
```

---

## 14. Decision Timeline Model

### 14.1 定位

> 回答: **"我的决策如何形成？"**
> 不是列出决策。是展示从发现到复盘的完整链条。

### 14.2 完整生命周期

```
一个投资标的的完整旅程:

  Market Event           "NVIDIA Q1 报告引起注意"
       │
       ▼
  Research Trigger       "开始研究 AI GPU 市场"
       │
       ▼
  📝 Research Note       "AI GPU 市场分析"
       │
       ▼
  💡 Thesis v1           "NVIDIA: AI 基建受益"
       │
       ├─→ Evidence added "Q2 财报 +154%"
       │
       ▼
  💡 Thesis v2           "信心提升至 0.75"
       │
       ▼
  📊 Decision            "Buy NVDA @ $955"
       │
       ▼
  ⏳ Waiting             "等待催化剂"
       │
       ▼
  ✅ Outcome             "Correct, +41%"
       │
       ▼
  🧠 Reflection          "AI 基建投资模式"
```

### 14.3 Timeline 数据组装

```python
def build_decision_timeline(ticker: str) -> DecisionTimeline:
    """
    从 memory_entries 中提取某个 ticker 的完整投资时间线。

    SQL:
      SELECT * FROM memory_entries
      WHERE ticker LIKE '%{ticker}%'
      ORDER BY created_at ASC

    然后按 type 分类展示:
      - note:        Research phase
      - thesis:      Belief formation (with version_history)
      - decision:    Action phase
      - reflection:  Learning phase

    每个 entry 在时间线上显示为一点。
    Thesis 的 version_history 在 Thesis 点下缩进显示。
    """
```

### 14.4 Timeline 展示

```
┌─ Investment Journey: NVDA ──────────────────────────────────┐
│                                                              │
│  Jun 10  📰  Market Event                                   │
│          NVIDIA Q1 earnings highlight AI demand surge        │
│          │                                                   │
│  Jun 12  📝  Research Started                               │
│          AI GPU Market Analysis — NVIDIA Dominance           │
│          │                                                   │
│  Jun 15  💡  Thesis v1 (conf: 0.60)                         │
│          NVIDIA: Core AI Infra Beneficiary                   │
│          │  Catalysts: AI demand surge                       │
│          │  Target: $1200                                    │
│          │                                                   │
│  Jul 10  💡  Thesis v2 (conf: 0.75) 🔺                      │
│          Q2 earnings beat. DC revenue +154% YoY.             │
│          │  Added evidence: Q2 earnings report               │
│          │  Added evidence: TSMC CoWoS capacity check        │
│          │                                                   │
│  Jul 15  📊  Decision                                       │
│          Buy NVDA @ $955 · 50 shares · 10% position          │
│          │  Reason: Q2 beat, PEG < 1, supply chain verified  │
│          │  Mood: Confident                                  │
│          │                                                   │
│  Aug 01  💡  Thesis v3 (conf: 0.70) ⚠️                      │
│          Added counter: AMD MI300 hyperscaler adoption       │
│          │                                                   │
│  Sep 20  ✅  Outcome: CORRECT (+41%)                         │
│          Target $1200 reached. Inference market exploded.    │
│          │                                                   │
│  Sep 22  🧠  Reflection                                     │
│          AI infrastructure investing success pattern         │
│          │  Pattern: Supply chain + earnings confirmation    │
│          │  Principle: Verify before entry, not predict      │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### 14.5 数据存储

```
不创建新表。
Timeline 是 memory_entries 的聚合视图（按 ticker + created_at 排序）。
Thesis 的 version_history 在时间线上展开显示。
```

---

## 15. Conviction Calibration Engine

### 15.1 定位

> 回答: **"我了解自己的判断力吗？"**
> 不只是计算命中率。是**分析判断质量的模式**。

### 15.2 校准的四个层次

```
Level 1: Overall Accuracy
  "我整体判断准确率是多少？"
  → thesis_hit_rate = correct / resolved

Level 2: Confidence Calibration
  "我高信心时的准确率和低信心时一样吗？"
  → 分桶对比: High vs Medium vs Low

Level 3: Contextual Accuracy
  "我在什么情况下判断准确？什么情况下不准确？"
  → 按 sector, market_cap, strategy_type 分组

Level 4: Temporal Calibration
  "我的判断力在改善还是退化？"
  → 滚动窗口趋势
```

### 15.3 校准引擎实现

```python
class ConvictionCalibrationEngine:
    """Analyzes the relationship between self-assessed confidence and accuracy."""

    def __init__(self, memory_db: MemoryDatabase):
        self._db = memory_db

    # Level 1: Overall
    def overall_accuracy(self) -> dict:
        """hit_rate, total_resolved, correct_count, wrong_count"""
        ...

    # Level 2: Bucket analysis
    def calibration_buckets(self) -> list[CalibrationBucket]:
        """High/Medium/Low confidence → hit_rate per bucket"""
        ...

    def calibration_score(self) -> float:
        """
        Brier-like calibration score (0-100).

        Perfect calibration (100):
          High confidence → high accuracy
          Low confidence → low accuracy

        Poor calibration (0):
          High confidence → low accuracy (overconfident)
          Low confidence → high accuracy (underconfident)
        """
        ...

    # Level 3: Contextual
    def accuracy_by_tag(self) -> list[TagPerformance]:
        """Hit rate broken down by investment theme/sector/strategy"""
        ...

    def accuracy_by_market_cap(self) -> dict:
        """Large cap vs mid cap vs small cap accuracy"""
        ...

    # Level 4: Temporal
    def rolling_hit_rate(self, window_days: int = 90) -> list[dict]:
        """Rolling window hit rate over time → is judgment improving?"""
        ...

    # Insights
    def generate_insights(self) -> list[str]:
        """
        Generate actionable insights from calibration data.

        Examples:
          - "High-confidence theses hit at 100%. You know when you know."
          - "Medium-confidence theses underperform. Raise conviction threshold."
          - "Your tech sector accuracy (100%) far exceeds consumer (33%)."
          - "Hit rate improved from 50% (Q1) to 75% (Q2). You're getting better."
          - "You've never made a low-confidence thesis. Consider tracking more ideas."
        """
        ...
```

### 15.4 Calibration Score 计算

```
Calibration Score (0-100):

基于 Brier Score 的变体:

  For each confidence bucket b:
    expected[b] = midpoint_confidence[b]
    actual[b]   = hit_rate[b]
    error[b]    = (expected[b] - actual[b]) ^ 2

  Weight by number of theses in each bucket.

  calibration_score = 100 * (1 - weighted_error)

解读:
  90-100:  Excellent calibration
  70-89:   Good calibration
  50-69:   Moderate — some over/under confidence
  30-49:   Poor — significant miscalibration
  0-29:    Very poor — confidence unrelated to accuracy
```

### 15.5 Learning Dashboard 展示

```
┌─ Conviction Calibration ──────────────────────────────────┐
│                                                            │
│  Calibration Score: 78/100  🟢 Good                        │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  Confidence    Theses   Hit Rate   Expected   Delta  │ │
│  │  ─────────────────────────────────────────────────── │ │
│  │  High (>0.7)     3       100%       85%      +15%   │ │
│  │  Med (0.5-0.7)   2        50%       60%      -10%   │ │
│  │  Low (<0.5)      0        N/A       35%       N/A   │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
│  Interpretation:                                           │
│  ✅ High confidence: well calibrated (slightly conservative)│
│  ⚠️ Medium confidence: slightly overconfident              │
│  💡 You don't make low-confidence theses.                   │
│     Consider tracking some low-conviction ideas to test    │
│     whether you can distinguish good from bad setups.      │
│                                                            │
│  Trend:                                                     │
│  Calibration Score over time:                               │
│  Q1: 65 → Q2: 72 → Q3: 78  ▲ Improving                    │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

---

## 16. Investor Growth Metrics

### 16.1 定位

> 不只是数字。是**投资能力的成长轨迹**。

### 16.2 五个成长指标

```
1. Judgment Quality（判断质量）
   - Thesis Hit Rate (trend)
   - Calibration Score (trend)
   - Profit Factor (avg win / avg loss)

2. Decision Discipline（决策纪律）
   - Decision-to-Thesis Ratio（有论文的决策 / 总决策）
   - Stop-Loss Adherence（触发止损实际执行率）
   - Impulse Trade Ratio（无论文的冲动交易占比）

3. Learning Velocity（学习速度）
   - Lessons Logged per Month
   - Principles Updated per Quarter
   - Reflection-to-Thesis Ratio

4. Process Consistency（流程一致性）
   - Streak Days（连续记录天数）
   - Weekly Review Completion Rate
   - Inbox Triage Regularity

5. Emotional Awareness（情绪觉察）
   - Mood-Correct Correlation（什么情绪下判断更准？）
   - Decision Quality by Mood
   - Overconfidence Detection（信心 > 实际准确率的频率）
```

### 16.3 Growth Dashboard

```
┌─ Investor Growth ──────────────────────────────────────────┐
│                                                             │
│  Judgment Quality                    Decision Discipline    │
│  ┌────────────────────────┐         ┌────────────────────┐ │
│  │ Hit Rate:  67% ▲       │         │ Thesis-backed: 75% │ │
│  │ Calibration: 78/100 ▲  │         │ Stop-loss: 100% ✅ │ │
│  │ Profit Factor: 5.75    │         │ Impulse: 0% ✅     │ │
│  └────────────────────────┘         └────────────────────┘ │
│                                                             │
│  Learning Velocity                   Process Consistency    │
│  ┌────────────────────────┐         ┌────────────────────┐ │
│  │ Lessons: 4/month       │         │ Streak: 12 days    │ │
│  │ Principles: 5 total    │         │ Weekly Review: 80% │ │
│  │ Refl/Thesis: 0.8       │         │ Inbox Triage: 90%  │ │
│  └────────────────────────┘         └────────────────────┘ │
│                                                             │
│  Emotional Awareness                                        │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Mood     Decisions   Win Rate   Insight                │ │
│  │ ────────────────────────────────────────────────────── │ │
│  │ Confident    3        67%       Good decisions        │ │
│  │ Calm         1       100%       Best state             │ │
│  │ Anxious      0        N/A       No anxious trades ✅   │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 16.4 数据来源

```
全部来自已有数据:

  memory_entries:
    - type='thesis' + status → hit_rate, calibration
    - type='decision' + decision.mood → emotional awareness
    - type='reflection' → learning velocity
    - created_at → streak, consistency

  V2 trades.db:
    - paired trades → profit_factor

不创建新表。纯计算。
```

---

## Part III: Implementation

---

## 17. 开发拆分计划

### 17.1 总览

```
Phase 2: 10 commits · ~2,800 lines · 3 周

Part I (Foundation):     Commits 7-11    ~1,700 lines   2 周
Part II (Cognitive):     Commits 12-16   ~1,100 lines   1 周
```

### 17.2 Part I: Foundation（恢复原有计划）

```
Commit  7: Market Context + Investment Universe
Commit  8: Action Center + Research Inbox
Commit  9: Thesis Board
Commit 10: Portfolio Intelligence + Investor Learning
Commit 11: Command Center UI Finalize
```

### 17.3 Part II: Cognitive Layer（新增）

```
Commit 12: feat(workspace): add evidence architecture

  src/v3/workspace/evidence.py            ★ NEW  (~150 lines)
  src/v3/workspace/routes.py              ★ MODIFY (+40 lines)
  templates/v3/partials/evidence_board.html ★ NEW (~80 lines)
  tests/v3/test_evidence.py               ★ NEW  (~80 lines)

  内容:
    - EvidenceManager: add_evidence(), remove_evidence(), list_evidence()
    - 证据存储到 thesis.evidence JSON
    - Evidence Board UI（supporting + counter 分开展示）
    - 证据强度 + 信心影响计算
    - 向后兼容: thesis.evidence 不存在 → 空状态展示

Commit 13: feat(workspace): add thesis version system

  src/v3/workspace/versioning.py          ★ NEW  (~120 lines)
  src/v3/workspace/routes.py              ★ MODIFY (+20 lines)
  templates/v3/partials/version_timeline.html ★ NEW (~60 lines)
  tests/v3/test_versioning.py             ★ NEW  (~70 lines)

  内容:
    - VersionTracker: detect_changes(), create_version()
    - 自动检测 confidence/catalysts/risks/target_price/evidence 变化
    - 变化 > 阈值 → 自动追加 version_history
    - Version Timeline UI
    - 整合到 Thesis 编辑流程: 每次 update → 自动检测 → 追加 version

Commit 14: feat(workspace): add decision timeline model

  src/v3/workspace/timeline.py            ★ NEW  (~130 lines)
  src/v3/workspace/routes.py              ★ MODIFY (+30 lines)
  templates/v3/partials/decision_timeline.html ★ NEW (~80 lines)
  tests/v3/test_timeline.py               ★ NEW  (~80 lines)

  内容:
    - DecisionTimelineBuilder: 按 ticker 聚合完整投资旅程
    - 时间线展示: Event → Research → Thesis → Decision → Outcome → Reflection
    - Thesis version_history 在时间线上展开
    - API: GET /api/workspace/timeline/<ticker>

Commit 15: feat(workspace): add conviction calibration engine

  src/v3/workspace/calibration.py         ★ NEW  (~180 lines)
  src/v3/workspace/routes.py              ★ MODIFY (+30 lines)
  templates/v3/partials/calibration.html  ★ NEW  (~80 lines)
  tests/v3/test_calibration.py            ★ NEW  (~90 lines)

  内容:
    - ConvictionCalibrationEngine: 4 个 level 的分析
    - Calibration Score (Brier-based, 0-100)
    - 上下文准确率: by_tag, by_market_cap
    - 时间趋势: rolling_hit_rate
    - Insight 自动生成
    - API: GET /api/workspace/calibration

Commit 16: feat(workspace): add investor growth metrics

  src/v3/workspace/growth.py              ★ NEW  (~160 lines)
  src/v3/workspace/routes.py              ★ MODIFY (+30 lines)
  templates/v3/partials/growth.html       ★ NEW  (~80 lines)
  tests/v3/test_growth.py                 ★ NEW  (~80 lines)

  内容:
    - GrowthTracker: 5 个维度的计算
    - Judgment Quality, Decision Discipline, Learning Velocity,
      Process Consistency, Emotional Awareness
    - Growth Dashboard UI
    - API: GET /api/workspace/growth
```

### 17.4 代码量汇总

```
Part I (Foundation):
  market_context.py         80
  universe.py              100
  intelligence.py          200
  inbox.py                 120
  thesis_board.py          100
  portfolio_intel.py       130
  learning.py              100
  routes.py (delta)       +160
  HTML templates           700
  Tests                    520
                          ────
  Subtotal               2,210

Part II (Cognitive):
  evidence.py              150
  versioning.py            120
  timeline.py              130
  calibration.py           180
  growth.py                160
  routes.py (delta)       +150
  HTML templates           380
  Tests                    400
                          ────
  Subtotal               1,670

Total:                   ~3,880 lines
```

### 17.5 零新表验证

```
所有新增数据存储:
  evidence          → thesis.evidence (JSON)
  version_history   → thesis.version_history (JSON)
  decision context  → decision JSON 扩展
  calibration       → 纯计算，不存储
  growth metrics    → 纯计算，不存储

Phase 2 结束后的 lxl_v3.db:
  仍然只有 memory_entries 一张表。
```

---

> **完整 Workspace V3 Architecture。等待确认。**
