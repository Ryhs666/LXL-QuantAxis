# LXL·QuantAxis V3 — Workspace Redesign

> **Investment Command Center**  
> 每天打开，有明确行动。不只是看数据，是知道自己该做什么。

**Status**: REDESIGN  
**Replaces**: docs/V3_WORKSPACE_SPEC.md  
**Reason**: Foundation 完成了数据层，但缺少"给用户行动指令"的能力

---

## 1. 问题诊断

### 当前 Workspace 的问题

```
Foundation 实现的功能:
  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
  │ Active   │  │ Watchlist│  │ Queue    │  │ Portfolio│
  │ Theses   │  │ Items    │  │ Items    │  │ Overview │
  │    2     │  │    3     │  │    4     │  │    1     │
  └──────────┘  └──────────┘  └──────────┘  └──────────┘

问题: 用户看到了数据，但不知道:
  ❌ "我今天应该先做什么？"
  ❌ "哪个 Thesis 该复盘了？"
  ❌ "哪个 Watchlist 标的可以开始研究了？"
  ❌ "我的组合有什么风险？"
  ❌ "我的研究流程卡在哪里？"
```

### 根因

当前设计是**数据展示型 Dashboard**，不是**行动导向的 Command Center**。

```
数据展示型:  "这里有你的数据，想看什么自己找"
行动导向型:  "你今天有 3 件事需要处理，最重要的是..."
```

---

## 2. Core Positioning

### 2.1 一句话定位

> **Investment Command Center** — 每天打开，系统告诉你今天该做什么投资决策。

### 2.2 三个核心问题

用户打开 Workspace，三秒内应该能回答：

| # | 问题 | 对应模块 |
|---|------|----------|
| 1 | **我今天需要做什么决策？** | Priority Actions |
| 2 | **我的研究管线有什么进展？** | Thesis Board |
| 3 | **我的组合是否健康？** | Portfolio Intelligence |

### 2.3 和其他页面的关系

```
/workspace     Command Center    "我今天该做什么？"      ← 行动入口
/journal       Memory Archive    "我过去做了什么？"      ← 历史回顾
/pipeline      Research Engine   "验证我的投资想法"       ← 量化工具
```

---

## 3. Daily Investment Workflow

### 3.1 用户的一天

```
═══════════════════════════════════════════════════════════════
8:45 AM — 开盘前检查
═══════════════════════════════════════════════════════════════

打开 /workspace → 顶部看到 Today's Focus:

  ┌─────────────────────────────────────────────────────────┐
  │ 🔴 PRIORITY: 中芯国际 Thesis 已 45 天未更新                │
  │    Q2 财报已出，需要更新催化剂状态并评估是否需要调整目标价    │
  │    [→ 更新 Thesis]                                       │
  │                                                          │
  │ 🟡 ATTENTION: 2 条待复盘论文超过 30 天                     │
  │    茅台 Thesis (20d) · NVDA Decision (35d)                │
  │    [→ 去复盘]                                             │
  │                                                          │
  │ 🟢 RESEARCH: 研究队列有 1 个高优先级任务已等待 7 天         │
  │    白酒行业竞争格局                                        │
  │    [→ 开始研究]                                           │
  └─────────────────────────────────────────────────────────┘

  用户点击第一个 → 更新中芯国际 Thesis → 完成

═══════════════════════════════════════════════════════════════
10:30 AM — 盘中产生想法
═══════════════════════════════════════════════════════════════

  用户想到一个新标的 → 打开 /workspace → Research Inbox

  ┌─ Research Inbox ─────────────────────────────────────┐
  │ [+ Quick Capture]                                     │
  │                                                       │
  │ 标题: [比亚迪 — 新能源出海逻辑___________]              │
  │ ticker: [002594]  priority: [high ▼]                  │
  │                                                       │
  │ [Save to Inbox]  [Save as Thesis Draft]               │
  └──────────────────────────────────────────────────────┘

  快速捕获，不打断当前工作。后续从 Inbox 中处理。

═══════════════════════════════════════════════════════════════
4:00 PM — 收盘后复盘
═══════════════════════════════════════════════════════════════

  打开 /workspace → Portfolio Intelligence:

  ┌─ Portfolio Health ────────────────────────────────────┐
  │                                                       │
  │  ⚠️ 五粮液：有持仓但没有活跃 Thesis                      │
  │     建议：为这笔持仓写一个投资论文，明确持有逻辑            │
  │     [→ 创建 Thesis]                                    │
  │                                                       │
  │  ✅ NVDA：Thesis 已标记 Correct (+41%)                  │
  │     持仓有明确的投资逻辑支撑                              │
  │                                                       │
  │  ⚠️ 集中度风险：NVDA 占比 35%，超过 25% 上限             │
  │     建议：评估是否需要减仓或对冲                          │
  │                                                       │
  └───────────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════
```

---

## 4. Dashboard 信息层级

### 4.1 三层架构

```
Layer 1: COMMAND (行动指令)
  用户最先看到。红色=紧急，黄色=注意，绿色=正常。
  Priority Actions — "你今天需要..."

Layer 2: STATUS (状态概览)
  一眼看完当前状态。不需要交互，纯信息展示。
  Thesis Board · Portfolio Snapshot · Research Pipeline

Layer 3: DETAIL (深入分析)
  需要时才展开。点击进入详情。
  Watchlist · Queue · Analytics · Market Context
```

### 4.2 布局

```
┌──────────────────────────────────────────────────────────────┐
│  [LXL·QuantAxis V3]   Command   Journal   Pipeline            │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─ L1: PRIORITY ACTIONS ────────────────────────────────┐  │
│  │                                                         │  │
│  │  🔴 Review: 中芯国际 thesis 45d stale                    │  │
│  │  🟡 Pending: 2 reviews overdue                          │  │
│  │  🟢 Research: 白酒竞争格局 (7d in queue)                 │  │
│  │                                                         │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌─ L2: STATUS OVERVIEW ────────────────────────────────┐   │
│  │                                                         │  │
│  │  ┌─ Thesis Board ───────┐  ┌─ Portfolio Snapshot ───┐ │  │
│  │  │ Forming  Validating  │  │ NVDA   35%  ✅ covered  │ │  │
│  │  │    1        1        │  │ 000063 22%  ✅ covered  │ │  │
│  │  │ Waiting  Completed   │  │ 600519 18%  ⏳ pending  │ │  │
│  │  │    1        4        │  │ 000858  0%  ⚠️ missing  │ │  │
│  │  └──────────────────────┘  └────────────────────────┘ │  │
│  │                                                         │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌─ L3: DETAIL (collapsible) ────────────────────────────┐  │
│  │  [Watchlist] [Queue] [Market Context] [Analytics]      │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

---

## 5. Priority Action System

### 5.1 设计目标

> 不只是排序列表。是**告诉用户该做什么**。

### 5.2 Action 类型

```python
@dataclass(frozen=True, slots=True)
class PriorityAction:
    action_id: str              # e.g. "review-thesis-42"
    level: str                  # "critical" | "warning" | "info"
    category: str               # "review" | "research" | "decide" | "risk"
    title: str                  # "Review: 中芯国际 thesis 45d stale"
    description: str            # "Q2 earnings are out. Update thesis."
    source_type: str            # "thesis" | "decision" | "queue" | "position"
    source_id: int              # entry_id or position reference
    action_label: str           # "→ Update Thesis"
    action_route: str           # "/journal?edit=42" or "/api/workspace/theses/42/outcome"
```

### 5.3 规则引擎

系统自动扫描并生成 Action：

```
Rule 1: STALE THESIS
  IF thesis.status = 'pending'
     AND days_since_created > 45
  → Level: CRITICAL
  → Action: "Review or mark outcome"

Rule 2: OVERDUE REVIEW
  IF thesis.status = 'pending'
     AND days_since_created > 30
  → Level: WARNING
  → Action: "Schedule review"

Rule 3: STALE QUEUE ITEM
  IF queue_item.priority = 'high'
     AND days_since_created > 5
  → Level: WARNING
  → Action: "Start research or adjust priority"

Rule 4: UNCOVERED POSITION
  IF portfolio.has_position(symbol)
     AND NOT memory.has_active_thesis(symbol)
  → Level: WARNING
  → Action: "Write thesis for this holding"

Rule 5: CONCENTRATION RISK
  IF position.weight > 25%
  → Level: WARNING
  → Action: "Review concentration"

Rule 6: HIGH CONVICTION, NO ACTION
  IF thesis.confidence > 0.7
     AND NOT memory.has_decision(thesis.ticker)
     AND days_since_created > 14
  → Level: INFO
  → Action: "Consider acting on this high-conviction thesis"

Rule 7: DORMANT WATCHLIST
  IF watchlist_item.days_since_created > 30
     AND NOT memory.has_recent_activity(ticker, days=30)
  → Level: INFO
  → Action: "Research or remove from watchlist"
```

### 5.4 排序逻辑

```
Priority = level_weight + age_factor + conviction_factor + exposure_factor

level_weight:
  critical → 100
  warning  →  50
  info     →  10

age_factor:
  days_stale / 30 (每超过阈值 30 天 +10)

conviction_factor (仅 thesis):
  confidence > 0.7 → +15

exposure_factor (仅 matched positions):
  position_weight_pct > 20 → +20
  position_weight_pct > 10 → +10
```

---

## 6. Research Inbox

### 6.1 定位

> 快速捕获投资想法的地方。不要求结构化，不打断当前工作。

### 6.2 和 Queue 的区别

```
Inbox:   "我突然想到..."           → 快速捕获，零摩擦
Queue:   "我计划研究..."           → 有结构，有优先级
Thesis:  "我的投资观点是..."        → 完整论文，可验证
```

### 6.3 Inbox → Queue → Thesis 流转

```
Inbox (快速捕获)
  │
  │  Triage: 定期处理 Inbox
  │
  ├─→ Queue (值得研究)
  │     │
  │     │  研究完成
  │     │
  │     ├─→ Thesis (形成观点)
  │     │     │
  │     │     │  结果确认
  │     │     │
  │     │     └─→ Correct / Wrong → Memory Analytics
  │     │
  │     └─→ Note (研究记录，不交易)
  │
  └─→ Note (仅供参考)
```

### 6.4 数据结构（复用 memory_entries）

```
Inbox 条目:
  type   = "note"
  tags   = ["inbox"]         ← 新增约定
  ticker = [] 或 ["002594"]
  title  = "比亚迪 — 新能源出海"
  content = ""  (Inbox 条目不需要正文)
```

---

## 7. Thesis Board

### 7.1 定位

> Kanban 式论文管线视图。一眼看到所有论文的进度。

### 7.2 列定义

```
┌──────────┬──────────┬──────────┬──────────┐
│ FORMING  │VALIDATING│ WAITING  │COMPLETED │
│ 形成中    │ 验证中    │ 等待结果  │ 已完成    │
├──────────┼──────────┼──────────┼──────────┤
│          │          │          │          │
│ Inbox    │ Pipeline │ Pending  │ Correct  │
│ items    │ results  │ theses   │ Wrong    │
│ converted│ attached │ awaiting │ theses   │
│ to draft │          │ outcome  │          │
│ theses   │          │          │          │
│          │          │          │          │
└──────────┴──────────┴──────────┴──────────┘

列定义:
  FORMING:    type='note' + tags=['inbox']   (从 Inbox 转入的草稿)
              type='thesis' + 无 pipeline_snapshot
  VALIDATING: type='thesis' + pipeline_snapshot 不为空
  WAITING:    type='thesis' + status='pending' + pipeline_snapshot 不为空
  COMPLETED:  type='thesis' + status IN ('correct', 'wrong', 'expired')
```

### 7.3 卡片信息

```
┌─────────────────────────────┐
│ 💡 000858 五粮液              │
│ 消费复苏 + 估值修复            │
│ conf: 0.70 · target: ¥180    │
│ created: 15d ago             │
│ ⚠️ 30d until review needed   │
│ [→ View] [→ Edit]            │
└─────────────────────────────┘
```

---

## 8. Portfolio Intelligence

### 8.1 定位

> 不只是列出持仓。是**分析组合健康度**。

### 8.2 三个检查维度

```
1. Thesis Coverage（论文覆盖度）
   每笔持仓是否都有对应的投资论文？
   - 有活跃 thesis → ✅ Covered
   - 有 thesis 但已过期 → ⚠️ Stale
   - 无 thesis → ❌ Uncovered

2. Concentration Risk（集中度风险）
   单只股票 > 25% → ⚠️ Warning
   单只股票 > 35% → 🔴 Critical
   单一行业 > 40% → ⚠️ Warning

3. Conviction Alignment（信心匹配）
   持仓权重是否和 thesis confidence 匹配？
   - 高信心 (>0.7) + 低仓位 (<10%) → 💡 Consider increasing
   - 低信心 (<0.5) + 高仓位 (>15%) → ⚠️ Mismatch
```

### 8.3 Dashboard 展示

```
┌─ Portfolio Intelligence ───────────────────────────────────┐
│                                                            │
│  Thesis Coverage:  3/4 positions covered                   │
│  Concentration:    ⚠️ NVDA at 35% (limit: 25%)             │
│  Alignment:        2 matched, 1 mismatched                  │
│                                                            │
│  ┌──────────┬────────┬────────┬──────────┬──────────────┐ │
│  │ Position │ Weight │ Thesis │ Conviction│ Status       │ │
│  ├──────────┼────────┼────────┼──────────┼──────────────┤ │
│  │ NVDA     │ 35% 🔴 │ ✅     │ 0.80     │ ✅ Covered   │ │
│  │ 000063   │ 22%    │ ✅     │ 0.70     │ ✅ Covered   │ │
│  │ 600519   │ 18%    │ ⏳     │ 0.60     │ ⚠️ Pending   │ │
│  │ 000858   │ 0%*    │ ❌     │ —        │ ❌ No thesis  │ │
│  └──────────┴────────┴────────┴──────────┴──────────────┘ │
│  * in watchlist but no open position yet                   │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

---

## 9. Market Context

### 9.1 定位

> 快速市场快照。不替代行情软件。只是给研究提供背景。

### 9.2 内容

```
┌─ Market Context ──────────────────────────────────────────┐
│                                                            │
│  CSI 300:  3,842  ▲ +0.8%     Volume:  ¥320B  (+12%)     │
│  SSE STAR:   892  ▲ +1.5%                                  │
│                                                             │
│  Today's Leaders:         Today's Laggards:                 │
│  🟢 科技 +3.2%             🔴 地产 -2.1%                    │
│  🟢 通信 +2.8%             🔴 银行 -1.5%                    │
│                                                             │
│  Your Watchlist Today:                                       │
│  000858 五粮液  152.30  +1.2%                               │
│  688981 中芯国际  52.10  -0.8%                              │
│  NVDA   NVIDIA   $955   +3.5%  ▲                            │
│                                                             │
│  Data: akshare, delayed 15min                               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**注意**: Market Context 是 Phase 2.5 的功能，Phase 2 可以先用静态占位。核心是 Priority Actions + Thesis Board + Portfolio Intelligence。

---

## 10. 与 Memory 架构的连接

### 10.1 数据流

```
                        lxl_v3.db (memory_entries)
                              │
                    ┌─────────┼─────────┐
                    │         │         │
              MemoryAdapter     │    MemorySearch
              (tag queries)     │    (FTS5)
                    │         │         │
                    ▼         ▼         ▼
              ┌──────────────────────────────────┐
              │        WorkspaceService          │
              │  (aggregation + composition)     │
              ├──────────────────────────────────┤
              │        IntelligenceLayer         │
              │  PriorityEngine                  │
              │  ThesisBoardBuilder              │
              │  PortfolioAnalyzer               │
              │  InboxManager                    │
              ├──────────────────────────────────┤
              │        WorkspaceDashboard        │
              │  (unified response to /workspace)│
              └──────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │                   │
              V2 trades.db        V2 data providers
              (read-only)         (akshare — future)
```

### 10.2 标签约定（扩展）

```
现有约定:
  watchlist     → Watchlist 条目
  queue         → Research Queue 条目

新增约定:
  inbox         → Research Inbox 条目
  draft         → 草稿 Thesis（从 Inbox 转入，尚未验证）

优先级标签（不变）:
  priority:high
  priority:med
  priority:low
```

### 10.3 零新表保证

```
Phase 2 全程不创建新数据库表。

所有 Workspace 数据:
  - memory_entries (type + tags + status)
  - V2 trades.db (只读)

所有 Intelligence 计算:
  - 纯 Python 逻辑
  - 无状态，无缓存
  - 每次请求实时计算
```

---

## 11. 实现计划

### 11.1 Commit 规划（调整后）

```
Commit 7: feat(workspace): add intelligence layer
  - intelligence.py: PriorityEngine, ThesisBoardBuilder, PortfolioAnalyzer
  - Update service.py: add get_priority_actions(), get_thesis_board(), get_portfolio_intel()
  - Update routes.py: new API endpoints
  - Update workspace.html: L1 Priority Actions panel
  - Tests: 15+ test cases

Commit 8: feat(workspace): add research inbox
  - inbox.py: InboxManager (Memory-based)
  - Inbox → Queue → Thesis flow
  - Quick Capture UI
  - Tests: 5 test cases

Commit 9: feat(workspace): add thesis board view
  - Kanban-style thesis board in workspace.html
  - 4 columns: Forming / Validating / Waiting / Completed
  - Drag cards between columns (Alpine.js)
  - Tests: 5 test cases

Commit 10: feat(workspace): add portfolio intelligence
  - PortfolioAnalyzer: coverage, concentration, alignment checks
  - Dashboard integration
  - Tests: 5 test cases

Commit 11: polish(workspace): finalize Command Center UI
  - Layer 1-3 layout implementation
  - Market Context placeholder
  - Navigation polish
  - Integration tests
```

### 11.2 代码量估算

```
src/v3/workspace/
  intelligence.py        ~250 lines (NEW)
  inbox.py               ~150 lines (NEW)
  service.py             +80 lines (MODIFY)
  routes.py              +60 lines (MODIFY)

templates/v3/
  workspace.html         +200 lines (MODIFY)
  partials/thesis_board.html  ~80 lines (NEW)
  partials/inbox.html         ~50 lines (NEW)
  partials/priority.html      ~50 lines (NEW)

tests/v3/
  test_intelligence.py   ~200 lines (NEW)
  test_inbox.py          ~100 lines (NEW)
                        ────
  Total:                 ~1,220 lines
```

---

> **设计完成。等待确认后执行 Commit 7。**
