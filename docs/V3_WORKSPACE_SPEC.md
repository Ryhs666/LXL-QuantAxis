# LXL·QuantAxis V3 — Personal Investment Workspace Spec

> **Phase 2: 投资者每日操作台**  
> 真实投资使用优先 · 零新表 · 零新依赖

**Status**: DESIGN — 等待确认后开发  
**Base**: V3 Memory Showcase (Phase 1)  
**Target**: V3.0 Phase 2  
**Lines**: ~900 · **Commits**: 8 · **Duration**: 2 weeks

---

## 目录

1. [产品目标](#1-产品目标)
2. [用户每日使用流程](#2-用户每日使用流程)
3. [Dashboard 设计](#3-dashboard-设计)
4. [Watchlist 设计](#4-watchlist-设计)
5. [Research Queue 设计](#5-research-queue-设计)
6. [Active Thesis 设计](#6-active-thesis-设计)
7. [Portfolio Overview 设计](#7-portfolio-overview-设计)
8. [与 Investment Memory 集成方案](#8-与-investment-memory-集成方案)
9. [数据模型设计](#9-数据模型设计)
10. [页面结构设计](#10-页面结构设计)
11. [开发 Commit 规划](#11-开发-commit-规划)

---

## 1. 产品目标

### 1.1 问题

Phase 1 (Memory System) 完成了投研闭环的**后半段**：记录→跟踪→复盘。但每天打开系统时，缺少一个**起点**。

```
当前状态:
  打开浏览器 → 不知道去哪 → /journal 看到一堆历史记录
  → "我现在该干什么？"

目标状态:
  打开浏览器 → /workspace 一眼看到:
    1. 我在盯哪些股票
    2. 我有哪些活跃观点
    3. 我接下来该研究什么
    4. 我的组合现在怎么样
```

### 1.2 定位

```
Phase 1 (Memory):    "我研究过什么？判断对不对？"
Phase 2 (Workspace):  "我现在该关注什么？接下来研究什么？"
```

**Workspace 是投资者每天打开的第一个页面。操作台，不是展示页。**

### 1.3 不做

- 不是 Bloomberg Terminal 替代品
- 不是实时行情看板（V2 已有 Studio）
- 不是 Demo 数据展示（Phase 1 已完成）
- **是个人投资者每天开盘前/收盘后会打开的操作台**

---

## 2. 用户每日使用流程

### 2.1 三种日常场景

#### 场景 A: 开盘前（8:45 AM）

```
1. 打开 /workspace
2. 扫一眼 Watchlist → 关注的股票有没有重大消息？
3. 看 Active Thesis → 是否有观点需要调整？
4. 看 Portfolio Overview → 当前仓位是否在计划内？
5. 从 Research Queue 选一个今天要研究的任务
   → 开始研究工作
```

#### 场景 B: 盘中（可选操作）

```
6. 产生新的投资想法
   → 点击 [+ Add to Watchlist] 快速记录
   → 或点击 [+ New Thesis] 写下初步观点

7. 执行交易
   → 在 /journal 记录 Decision（买入理由+仓位+情绪）
   → Decision 自动关联到对应的 Thesis

8. 更新 Thesis 状态
   → 如果某个 thesis 的催化剂触发或风险暴露
   → 点击 [Edit] 更新内容
```

#### 场景 C: 收盘后（4:00 PM）

```
9. 回顾今日操作
   → 在 /workspace 看到 Pending Reviews 提醒
   → 点击进入需要复盘的 Thesis

10. 标记结果
   → 对到期/有结果的 Thesis → [Mark Correct] 或 [Mark Wrong]
   → 填写 outcome_detail 和 actual return
   → 写出 Reflection（如果教训深刻）

11. 清理 Research Queue
   → 标记完成的研究任务 → [Done]
   → 添加新的研究任务 → [+ Add to Queue]

12. 写 Journal entry
   → 跳转 /journal → 写今日市场观察
```

### 2.2 流程与模块映射

```
时间      操作                        模块
────────────────────────────────────────────
8:45    扫 Watchlist               → Watchlist
        看 Active Thesis           → Active Thesis
        看组合结构                  → Portfolio Overview
        选研究任务                  → Research Queue

盘中     记录新想法                  → Watchlist / Thesis
        执行交易                    → Memory (Decision)
        更新观点                    → Active Thesis

16:00   复盘 Thesis                → Active Thesis → Memory
        标记结果                    → Memory (Outcome)
        清理 Queue                 → Research Queue
        写日志                      → /journal
```

---

## 3. Dashboard 设计

### 3.1 信息架构

Dashboard 回答四个问题：

| 问题 | 模块 | 展示形式 |
|------|------|----------|
| 我在盯什么？ | Watchlist | 紧凑列表，3-5条，带优先级 |
| 我在等什么？ | Active Thesis | 卡片列表，显示催化剂和剩余时间 |
| 我该研究什么？ | Research Queue | 编号列表，按优先级排序 |
| 我的钱在哪？ | Portfolio Overview | 迷你持仓表 + P&L |

### 3.2 布局

```
┌──────────────────────────────────────────────────────────────┐
│  [LXL·QuantAxis V3]   Workspace   Journal   Pipeline         │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐   │
│  │ Active   │ Watchlist│ Queue    │ Pending  │ Today's  │   │
│  │ Theses   │ Items    │ Items    │ Reviews  │ P&L      │   │
│  │    2     │    3     │    4     │    1     │  --      │   │
│  └──────────┴──────────┴──────────┴──────────┴──────────┘   │
│                                                               │
│  ┌─ Left (60%) ───────────────────┐ ┌─ Right (40%) ────────┐ │
│  │                                 │ │                       │ │
│  │  📋 Active Thesis               │ │  📈 Portfolio          │ │
│  │  (当前活跃观点 — 等结果)         │ │  (持仓结构 — 钱在哪)   │ │
│  │                                 │ │                       │ │
│  │  👀 Watchlist                    │ │  ⏳ Pending Reviews    │ │
│  │  (关注列表 — 盯什么)             │ │  (待复盘 — 别忘记)     │ │
│  │                                 │ │                       │ │
│  │  📝 Research Queue              │ │  🧠 Recent             │ │
│  │  (待研究 — 下一步做什么)         │ │     Reflections        │ │
│  │                                 │ │  (最近反思)            │ │
│  └─────────────────────────────────┘ └───────────────────────┘ │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

### 3.3 顶部统计栏

5 个数字，一眼看到系统状态：

| 统计项 | 数据来源 | 问的是什么 |
|--------|----------|-----------|
| Active Theses | `type='thesis' AND status='pending'` | 有多少观点在等待验证？ |
| Watchlist | `type='note' AND tags 包含 'watchlist'` | 在盯多少只股票？ |
| Queue | `type='note' AND tags 包含 'queue'` | 待研究任务积压了多少？ |
| Pending Reviews | `type='thesis' AND status='pending' AND created_at > 30d` | 有多少论文该复盘了？ |
| Today's P&L | V2 `trades.db` 查询当前持仓 + 最新价格 | 今天赚了还是亏了？ |

---

## 4. Watchlist 设计

### 4.1 定位

> 你关注的股票清单。不是持仓（持仓在 Portfolio），不是预测（预测在 Thesis），是**关注**。
> "我在盯这几只，等待合适的时机。"

### 4.2 数据结构

使用 `memory_entries` 表，**标签约定**：

```
MemoryEntry:
  type      = "note"
  ticker    = ["000858"]              ← 必填
  title     = "五粮液 — 消费复苏受益"   ← 一句话关注理由
  content   = "## 关注理由\n\n..."     ← 可选，详细分析
  tags      = ["watchlist", "消费", "白酒", "priority:high"]

优先级标签:
  priority:high — 高优先级，近期可能交易
  priority:med  — 中优先级，持续跟踪
  priority:low  — 低优先级，观察
```

### 4.3 为什么不建新表

| 方案 | 优点 | 缺点 |
|------|------|------|
| 新建 watchlist 表 | 结构独立 | 需要 migration、新 CRUD、与 Memory 割裂 |
| 标签约定 | 零 schema 变更、Memory 搜索原生支持 | 依赖标签纪律 |

**选择标签约定。一个个人投资者不需要为每类数据建一张表。**

### 4.4 用户操作

```
添加:  [+ Add to Watchlist]
       → 弹出 Modal：输入 ticker + 关注理由 + 优先级
       → 后台 create MemoryEntry(type="note", tags=["watchlist", ...])

查看:  在 /workspace 的 Watchlist 面板中显示
       每条显示: ticker, 理由摘要, 添加日期, 优先级

移除:  [Remove]
       → 确认 → 删除该条 note

关联:  点击 ticker → 跳转 /journal 查看该标的所有 Memory 条目

转 Thesis:  [→ Create Thesis]
       → 从 Watchlist 条目创建一条新 Thesis
       → 保留原 Watchlist 条目（关注理由和研究论文是不同的东西）
```

### 4.5 前端展示

```
┌─ Watchlist (3) ───────────────────────────── [+ Add] ─┐
│                                                        │
│  🔴 000858  五粮液                                     │
│     消费复苏受益 · added 15d ago                        │
│     [消费] [白酒] [priority:high]          [×]         │
│                                                        │
│  🟡 688981  中芯国际                                   │
│     芯片国产替代 · added 7d ago                         │
│     [半导体] [priority:med]                 [×]         │
│                                                        │
│  🟢 NVDA    NVIDIA                                     │
│     AI算力龙头 · added 30d ago                          │
│     [AI] [美股] [priority:high]            [×]         │
│                                                        │
└────────────────────────────────────────────────────────┘
```

---

## 5. Research Queue 设计

### 5.1 定位

> 待研究任务清单。"我接下来应该研究什么？"
> 不是 Todo app。是**研究流程的起点**。

### 5.2 数据结构

```
MemoryEntry:
  type      = "note"
  ticker    = [] 或 ["000858"]        ← 可选（如果已确定标的）
  title     = "分析白酒行业竞争格局"     ← 研究任务标题
  content   = """## 待研究问题           ← 可选，研究提纲
                 1. 高端白酒市场份额变化
                 2. 次高端价格带竞争
                 3. 渠道库存水平""""
  tags      = ["queue", "消费", "priority:high"]
```

**与 Watchlist 的区别**：
- Watchlist = "我在盯这只股票"（有 ticker）
- Queue = "我该研究这个主题"（可能有 ticker，也可能没有）

### 5.3 用户操作

```
添加:  [+ Add to Queue]
       → 输入标题、可选 ticker、优先级
       → 后台 create MemoryEntry(type="note", tags=["queue", ...])

完成:  [Done]
       → 从 tags 中移除 "queue"
       → 条目保留在 Memory 中作为普通 note
       → 如果产生了研究结论，可以从中创建 Thesis

排序:  按 priority 排序: high → med → low
       同级按 created_at 排序（旧的优先处理）

清理:  定期清理超过 60 天未完成的 queue 条目
```

### 5.4 前端展示

```
┌─ Research Queue (4) ──────────────────────── [+ Add] ─┐
│                                                        │
│  🔴 #1  研究白酒行业竞争格局                             │
│     priority:high · added 3d ago                        │
│     [消费] [白酒]                           [Done]      │
│                                                        │
│  🔴 #2  分析 NVDA Q2 财报                               │
│     ticker: NVDA · priority:high · added 5d ago         │
│     [AI] [美股] [earnings]                  [Done]      │
│                                                        │
│  🟡 #3  调研光伏产业链                                   │
│     priority:med · added 7d ago                          │
│     [光伏] [产业链]                          [Done]      │
│                                                        │
│  🟢 #4  阅读 Howard Marks 最新备忘录                     │
│     priority:low · added 10d ago                         │
│     [reading]                               [Done]      │
│                                                        │
└────────────────────────────────────────────────────────┘
```

---

## 6. Active Thesis 设计

### 6.1 定位

> 当前活跃的投资观点。"我有哪些正在验证中的判断？"

**与 Memory 中的 Thesis 是什么关系？**
Memory 中的所有 thesis 条目 = 完整历史。Active Thesis = 其中 `status='pending'` 的子集。

### 6.2 数据来源

```
MemoryEntry:
  type       = "thesis"
  status     = "pending"             ← 关键筛选条件
  ticker     = ["688981"]
  title      = "中芯国际：大陆半导体制造核心资产"
  content    = "## 核心逻辑\n\n..."    ← 投资逻辑（Markdown）
  thesis     = {
    catalysts: ["产能利用率回升", "华为回归", "大基金三期"],
    risks: ["制裁升级", "先进制程良率"],
    target_price: 65.0,
    timeline: "6-12 months"
  }
  confidence = 0.55
  created_at = "2026-06-22"         ← 论文创建日期
```

### 6.3 状态流转

```
      新建 Thesis
          │
          ▼
    ┌──────────┐
    │ PENDING   │  ← Active Thesis 显示在这里
    │ 等待验证   │
    └─────┬─────┘
          │  催化剂触发 OR 时间到期
          ▼
    ┌──────────────┐
    │ 用户判断结果   │
    └──┬────────┬──┘
       │        │
    ✅ CORRECT  ❌ WRONG     ⏸️ EXPIRED
       │        │               │
       └────────┴───────────────┘
                │
                ▼
          Memory Analytics
          (命中率/校准/标签表现)
```

### 6.4 用户操作

```
查看:   在 /workspace 首页的 Active Thesis 卡片中展示
        显示: title, ticker, confidence, catalysts, risks, 创建天数

编辑:   点击 thesis → 打开 Modal（复用 /journal 的编辑 Modal）
        → 更新逻辑、调整 confidence、增减 catalysts/risks

标记结果:
  [Mark Correct] → 弹窗输入 outcome_detail + actual_return
  [Mark Wrong]   → 弹窗输入 outcome_detail + actual_return
  → 更新 status，自动写入 outcome JSON
  → thesis 从 Active 列表移除
  → Analytics 自动重算

新建:  [+ New Thesis]
       → 打开 Modal → 输入标题、ticker、逻辑、catalysts、risks、confidence
       → 保存为 type='thesis', status='pending'
```

### 6.5 前端展示

```
┌─ Active Thesis (2) ────────────────────── [+ New Thesis] ─┐
│                                                            │
│  💡 中芯国际 (688981)                                       │
│     大陆半导体制造核心资产                                    │
│     Confidence: 0.55 · Target: ¥65 · Created: 45d ago      │
│     Catalysts: 产能利用率回升, 华为回归, 大基金三期           │
│     Risks: 制裁升级, 先进制程良率                             │
│     [Edit] [Mark Correct] [Mark Wrong]                      │
│                                                            │
│  💡 茅台 (600519)                                           │
│     高端消费防御性配置                                        │
│     Confidence: 0.60 · Target: ¥2100 · Created: 20d ago    │
│     Catalysts: 消费旺季, 提价预期                            │
│     Risks: 政策收紧, 消费降级                                 │
│     [Edit] [Mark Correct] [Mark Wrong]                      │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

---

## 7. Portfolio Overview 设计

### 7.1 定位

> 当前持仓结构概览。**只读**。"我的钱现在在哪里？"

### 7.2 数据来源

V2 `trades.db` → `trades` 表。V1 已有数据，只读查询，不通过 Workspace 修改。

```
trades 表 (V2 已有):
  symbol      TEXT    股票代码
  name        TEXT    股票名称
  market      TEXT    A股/美股/港股
  quantity    REAL    持仓数量
  avg_cost    REAL    平均成本
```

### 7.3 Thesis 关联

Portfolio 中的每个持仓，通过 ticker 匹配 Memory 中的活跃 thesis：

```python
# 伪代码
for position in portfolio:
    position.thesis = memory.search(
        type="thesis", ticker=position.symbol, status="pending"
    ).first()
```

| 匹配结果 | 显示 |
|----------|------|
| 有活跃 thesis | ✅ Correct / ⏳ Pending（可点击跳转） |
| 无活跃 thesis | ⚠️ No thesis — 提示"是否需要为这笔持仓写一个投资逻辑？" |

### 7.4 前端展示

```
┌─ Portfolio Overview ───────────────────────────────────┐
│                                                        │
│  Total Value: ¥XXX,XXX    Today's P&L: +3.2%           │
│                                                        │
│  ┌──────────┬────────┬────────┬────────┬────────────┐ │
│  │ Ticker   │ Name   │ Weight │ P&L    │ Thesis     │ │
│  ├──────────┼────────┼────────┼────────┼────────────┤ │
│  │ NVDA     │ NVIDIA │ 35%    │ +41% ▲ │ ✅ Correct │ │
│  │ 000063   │ 中兴   │ 22%    │ +28% ▲ │ ✅ Correct │ │
│  │ 600519   │ 茅台   │ 18%    │ +5%  ▲ │ ⏳ Pending │ │
│  │ 000858   │ 五粮液 │ 0%     │ —      │ ⚠️ No thesis│ │
│  │ Cash     │ —      │ 25%    │ —      │ —          │ │
│  └──────────┴────────┴────────┴────────┴────────────┘ │
│                                                        │
│  ⚠️ 五粮液有持仓但没有投资论文。                           │
│     [→ 为这笔持仓写一个 Thesis]                            │
│                                                        │
└────────────────────────────────────────────────────────┘
```

---

## 8. 与 Investment Memory 集成方案

### 8.1 集成原则

```
Workspace 是 Memory 的 VIEW 层，不是新数据层。

  /workspace               /journal
       │                       │
       └───────┬───────────────┘
               │
         Memory System
         (memory_entries)
               │
          lxl_v3.db
```

**Workspace 不存储任何数据。所有写操作最终写入 `memory_entries` 表。**

### 8.2 操作映射

| Workspace 操作 | Memory 操作 | 说明 |
|---------------|------------|------|
| Add to Watchlist | `MemoryRepository.save(type='note', tags=['watchlist', ...])` | 创建一条 note |
| Remove from Watchlist | `MemoryRepository.delete(id)` | 删除该条 note |
| Add to Queue | `MemoryRepository.save(type='note', tags=['queue', ...])` | 创建一条 note |
| Complete Queue item | `MemoryRepository.update(id)` — 从 tags 移除 'queue' | 更新标签 |
| New Thesis | `MemoryRepository.save(type='thesis', status='pending', ...)` | 创建一条 thesis |
| Edit Thesis | `MemoryRepository.update(id, ...)` | 更新 thesis 内容 |
| Mark Correct/Wrong | `MemoryRepository.update(id, status='correct', outcome={...})` | 更新状态 |
| Portfolio read | V2 `TradeRepository.find_all()` | 只读查询 |

### 8.3 搜索与筛选

Workspace 使用 `MemorySearch`（Phase 1 已完成）进行数据查询：

```python
# Watchlist 查询
searcher.query(SearchFilters(
    entry_type="note",
    tags=["watchlist"],
))

# Active Thesis 查询
searcher.query(SearchFilters(
    entry_type="thesis",
    status="pending",
))

# Research Queue 查询
searcher.query(SearchFilters(
    entry_type="note",
    tags=["queue"],
))
```

### 8.4 数据一致性

Workspace 操作后，`/journal` 页面立即可见新数据（同一张表）。

```
用户在 /workspace 创建 Watchlist 条目
  → MemoryRepository.save() → memory_entries 写入
  → 用户在 /journal 可以看到这条 note
  → MemoryAnalytics 统计自动更新（下次 GET /api/memory/analytics 时）
```

**Workflow 示例**：

```
1. 用户发现 000858 值得关注
   → /workspace → [+ Add to Watchlist]

2. 研究 000858 → 形成观点
   → /journal → 查看该 ticker 的 watchlist note
   → [+ New Thesis] → 填写投资逻辑

3. Thesis 状态变为 pending → 出现在 /workspace Active Thesis 中

4. 等待催化剂 → 结果确认
   → /workspace → Active Thesis → [Mark Correct]
   → 填写 outcome → status 变为 correct

5. 回顾 → 写 Reflection
   → /journal → [+ New Reflection]
   → 关联到该 thesis → 标签 lesson

6. Analytics 更新
   → 命中率、信心校准自动重算
```

### 8.5 与 /journal 的职责边界

```
/workspace (操作台)              /journal (记忆库)
─────────────────────────────────────────────────
看当前状态                        看历史记录
管理 Active Thesis                搜索所有 Thesis
管理 Watchlist                    浏览完整时间线
管理 Research Queue               FTS5 全文搜索
看持仓快照                         深度分析
快速操作（添加/标记完成）           详细编辑/复盘
```

**两个页面，一张表。职责分明，数据互通。**

---

## 9. 数据模型设计

### 9.1 零新表策略

```
Phase 1: lxl_v3.db
├── memory_entries          ← 唯一的表
├── memory_entries_fts      ← FTS5 索引
├── fundamental_snapshots   ← (Phase 2 原计划，暂不创建)
└── fundamental_series      ← (Phase 2 原计划，暂不创建)

Phase 2: 零新表
  Watchlist    → memory_entries (type='note', tags=['watchlist'])
  Queue        → memory_entries (type='note', tags=['queue'])
  Active Thesis → memory_entries (type='thesis', status='pending')
  Portfolio    → V2 trades.db (只读)
```

### 9.2 标签约定规范

```
系统标签（由 Workspace 自动管理）:
  watchlist     — Watchlist 条目
  queue         — Research Queue 条目

用户标签（自由定义）:
  priority:high — 高优先级
  priority:med  — 中优先级
  priority:low  — 低优先级
  [行业]        — 消费、科技、金融...
  [主题]        — AI、新能源、国产替代...
  [策略]        — 价值、成长、周期...
```

### 9.3 Watchlist 条目示例

```python
MemoryEntry(
    type="note",
    ticker=["000858"],
    title="五粮液 — 消费复苏受益",
    content="""## 关注理由

- 高端白酒龙头，品牌护城河深厚
- 当前 PE 25x，处于 5 年中位
- ROE 24%，行业领先
- 等待更好的入场时机（PE < 22x 或 Q3 财报确认趋势）""",
    tags=["watchlist", "消费", "白酒", "priority:high"],
)
```

### 9.4 Queue 条目示例

```python
MemoryEntry(
    type="note",
    ticker=[],
    title="研究白酒行业竞争格局",
    content="""## 待研究问题

1. 高端白酒（茅台/五粮液/泸州老窖）市场份额变化
2. 次高端价格带（300-800元）竞争态势
3. 渠道库存水平 — 经销商调研
4. 消费税率变化预期
5. 年轻消费者白酒消费趋势""",
    tags=["queue", "消费", "白酒", "priority:high"],
)
```

---

## 10. 页面结构设计

### 10.1 路由设计

```
页面路由:
  GET  /workspace          → workspace.html（Dashboard 首页）

API 路由:
  GET    /api/workspace/dashboard        → 首页聚合数据 JSON
  GET    /api/workspace/watchlist        → Watchlist 列表 HTML partial
  POST   /api/workspace/watchlist        → 添加 Watchlist 条目
  DELETE /api/workspace/watchlist/<id>   → 删除 Watchlist 条目
  GET    /api/workspace/theses           → Active Thesis 列表 HTML partial
  GET    /api/workspace/queue            → Research Queue 列表 HTML partial
  POST   /api/workspace/queue            → 添加 Queue 条目
  PUT    /api/workspace/queue/<id>/done  → 完成 Queue 条目
  GET    /api/workspace/portfolio        → Portfolio 概览 HTML partial
```

### 10.2 导航更新

```
[LXL·QuantAxis V3]   Workspace   Journal   Pipeline
                       ↑ 新增       ↑ 已有     ↑ 已有
                       默认首页
```

`/` 重定向到 `/workspace`（替代原来的 `/login` 重定向）。

### 10.3 文件结构

```
src/v3/workspace/                  ★ NEW (6 files, ~400 lines)
├── __init__.py                    # Flask Blueprint
├── routes.py                      # 页面 + API 路由（~150 lines）
├── dashboard.py                   # Dashboard 数据聚合（~80 lines）
├── watchlist.py                   # Watchlist CRUD（~60 lines）
├── queue.py                       # Queue CRUD（~60 lines）
└── portfolio_reader.py            # V2 trades.db 只读（~50 lines）

src/v3/web/__init__.py             ★ MODIFY (+2 lines)
                                   # 增加 workspace blueprint import

templates/v3/                      ★ NEW (5 files, ~300 lines)
├── workspace.html                 # Dashboard 首页
└── partials/
    ├── workspace_watchlist.html   # Watchlist 面板
    ├── workspace_thesis.html      # Active Thesis 面板
    ├── workspace_queue.html       # Research Queue 面板
    └── workspace_portfolio.html   # Portfolio 面板

tests/v3/                          ★ NEW (1 file, ~200 lines)
└── test_workspace.py              # 15 tests
```

### 10.4 代码量汇总

| 模块 | 文件数 | 行数 |
|------|--------|------|
| `src/v3/workspace/` | 6 | ~400 |
| `templates/v3/` | 5 | ~300 |
| `web_modern.py` integration | — | +3 |
| `tests/v3/` | 1 | ~200 |
| **总计** | **12** | **~903** |

---

## 11. 开发 Commit 规划

### Phase 2: 2 周 · 8 commits

```
Week 1: Backend Layer (4 commits)

  Commit 1: feat(workspace): add workspace module structure
    - src/v3/workspace/__init__.py — Flask Blueprint
    - Register in src/v3/web/__init__.py
    - Basic /workspace route returning placeholder HTML
    Files: 3, Lines: ~40

  Commit 2: feat(workspace): add watchlist service
    - watchlist.py — MemoryEntry CRUD with tag convention
    - API: GET list, POST create, DELETE remove
    - Tests: 4 test cases
    Files: 2, Lines: ~120

  Commit 3: feat(workspace): add research queue service
    - queue.py — MemoryEntry CRUD with tag convention
    - API: GET list, POST create, PUT mark done
    - Tests: 3 test cases
    Files: 2, Lines: ~100

  Commit 4: feat(workspace): add portfolio reader
    - portfolio_reader.py — V2 trades.db read-only query
    - API: GET portfolio snapshot with thesis linkage
    - Tests: 3 test cases
    Files: 2, Lines: ~100

Week 2: Web Layer (4 commits)

  Commit 5: feat(workspace): add dashboard aggregator
    - dashboard.py — aggregate data from all 4 modules
    - API: GET /api/workspace/dashboard
    Files: 1, Lines: ~80

  Commit 6: feat(workspace): add /workspace page
    - workspace.html — full dashboard layout
    - HTMX partials: watchlist, thesis, queue, portfolio
    - terminal.css dark theme
    Files: 5, Lines: ~300

  Commit 7: feat(workspace): add workspace API routes
    - routes.py — all workspace routes
    - HTMX partial responses for inline updates
    - Navigation: add Workspace tab, redirect / to /workspace
    Files: 2, Lines: ~150

  Commit 8: test(workspace): add workspace integration tests
    - test_workspace.py — 15 test cases
    - Cover: CRUD, tag conventions, portfolio read, thesis linkage
    - V2 regression: full test suite must pass
    Files: 1, Lines: ~200
```

### 验收清单

| # | 验收项 | 方式 |
|---|--------|------|
| F1 | `/workspace` 为默认首页 | 访问 `/` → 重定向到 `/workspace` |
| F2 | 5 卡统计栏正确显示数据 | 手动验证 |
| F3 | Watchlist 添加/删除立即生效 | 手动 + 查 DB |
| F4 | Queue 标记完成后从列表消失 | 手动 |
| F5 | Active Thesis 只显示 `status='pending'` | 查 + 验证 |
| F6 | Mark Correct/Wrong 后 thesis 从 Active 移除 | 手动 |
| F7 | Portfolio 从 V2 trades.db 读取正确 | 查数据 |
| F8 | `/workspace` 和 `/journal` 导航互通 | 手动 |
| F9 | 零新数据库表 (`lxl_v3.db` 表数不变) | 查 schema |
| F10 | V2 测试全部通过 (400+) | CI |
| F11 | 零新 pip 依赖 | `pip freeze` diff |
| F12 | ruff clean | CI |

---

> **设计完成。11 个章节覆盖全部需求。等待确认后进入开发。**
