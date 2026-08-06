# LXL·QuantAxis V3 — Investment Memory System Spec

> **Phase 1: 投资认知数据库**  
> 个人投资研究操作系统的核心模块

**Document Type**: Detailed Design Spec（详细设计规格）  
**Status**: DESIGN COMPLETE — ready for implementation  
**Module**: Module 1 — Investment Memory System  
**Phase**: 1 of 4  
**Duration**: Week 1-2  
**Base**: V2.0.0 Showcase  
**Dependency**: None（独立模块，无 V3 内部依赖）

---

## 目录

1. [产品目标](#1-产品目标)
2. [用户使用流程](#2-用户使用流程)
3. [数据库设计](#3-数据库设计)
4. [memory_entries Schema](#4-memory_entries-schema)
5. [FTS5 搜索设计](#5-fts5-搜索设计)
6. [API 设计](#6-api-设计)
7. [Web 页面设计](#7-web-页面设计)
8. [V2 管线连接方式](#8-v2-管线连接方式)
9. [测试方案](#9-测试方案)
10. [Commit 计划](#10-commit-计划)
11. [验收清单](#11-验收清单)

---

## 1. 产品目标

### 1.1 模块定位

```
Investment Memory System = 投资认知数据库

记录:
  ✓ 你研究过什么     (Research Notes)
  ✓ 你看好/看空什么   (Investment Thesis)
  ✓ 你做了什么交易    (Decision Record)
  ✓ 你学到了什么      (Reflection)

追踪:
  ✓ 你的判断有多准    (Thesis Hit Rate)
  ✓ 你的信心是否校准  (Conviction Calibration)
  ✓ 你的决策质量如何  (Decision Win Rate)
  ✓ 你的学习速度      (Lesson Density)
```

### 1.2 四种记忆类型

```
entry_type 枚举:

  "note"        研究笔记    自由格式，Markdown
                "我对消费行业的理解"
                "Q2 季报阅读笔记"

  "thesis"      投资论文    结构化，可验证
                "五粮液受益于消费复苏"
                含: 信心度、催化剂、风险、目标价、时间框架
                可追踪: 事后标记 correct/wrong/expired

  "decision"    决策记录    交易操作
                "2026-08-15 买入五粮液 @ ¥145"
                含: 决策理由、市场环境、情绪状态
                可追踪: 事后标记 good/bad/neutral

  "reflection"  反思笔记    经验教训
                "追高买入导致回撤超限"
                "消费板块是我的能力圈"
                关联: 可关联到具体 thesis 或 decision
```

### 1.3 成功指标

| 指标 | 目标 | 测量方式 |
|------|------|----------|
| 数据完整性 | 100% 管线 thesis 自动写入 | 跑 10 次管线 → 检查 `memory_entries` 表 |
| 搜索性能 | < 100ms（1000 条数据） | FTS5 搜索计时 |
| 搜索准确性 | 中文关键词返回相关结果 | 手动测试 10 个搜索词 |
| V2 兼容 | 管线失败不影响 Memory 写入 | 模拟数据库错误 → 管线正常返回 |
| 零依赖 | `pip freeze` 无新增 | 安装前后 diff |

---

## 2. 用户使用流程

### 2.1 核心流程

```
═══════════════════════════════════════════════════════════════
FLOW 1: 管线结束后自动记录 Thesis
═══════════════════════════════════════════════════════════════

  用户在 /pipeline 输入投资论文
  → 7-stage pipeline 运行完成
  → [自动] Memory System 静默写入一条 entry_type="thesis"
  → 用户在 /journal 看到新条目
  → 状态: outcome_status = "pending"

═══════════════════════════════════════════════════════════════
FLOW 2: 手动记录 Decision
═══════════════════════════════════════════════════════════════

  用户做了交易
  → 打开 /journal
  → 点击 [+ New Entry] → 选择类型 "Decision"
  → 填写: 标的、方向、价格、数量、理由、市场环境、情绪
  → [可选] 关联到已有的 Thesis
  → 保存

═══════════════════════════════════════════════════════════════
FLOW 3: 搜索和回顾
═══════════════════════════════════════════════════════════════

  用户想回顾关于"白酒"的所有记忆
  → 在 /journal 搜索框输入 "白酒"
  → FTS5 返回所有标题或内容包含"白酒"的条目
  → 可按 entry_type / date / symbol / outcome_status 进一步筛选

═══════════════════════════════════════════════════════════════
FLOW 4: 复盘 Thesis
═══════════════════════════════════════════════════════════════

  用户在 Dashboard 看到 "3 条论文待复盘"
  → 点击进入待复盘列表
  → 选择一条 Thesis → 查看原始内容 + pipeline_snapshot
  → 评估: 当时的目标价 vs 当前价格
  → 标记 outcome_status: "correct" / "wrong" / "expired"
  → 写 outcome_notes
  → [可选] 创建关联的 Reflection（"为什么对了/错了？"）
  → 系统自动重算 Analytics

═══════════════════════════════════════════════════════════════
FLOW 5: 查看 Memory Analytics
═══════════════════════════════════════════════════════════════

  用户打开 /workspace Dashboard
  → 看到 KPI 卡片: 论文总数 / 命中率 / 待复盘 / 决策胜率
  → 看到信心校准: 高信心论文命中率 vs 低信心论文命中率
  → 看到板块表现: 各行业论文命中率
  → 看到最近教训: 最新 5 条 Reflection

═══════════════════════════════════════════════════════════════
FLOW 6: 每日笔记
═══════════════════════════════════════════════════════════════

  收盘后
  → 用户打开 /journal
  → 点击 [+ New Entry] → 选择类型 "Note"
  → 写今日市场观察
  → 保存
```

---

## 3. 数据库设计

### 3.1 数据库策略

```
数据库文件: D:/trading_data/lxl_v3.db
引擎:       SQLite 3 (WAL mode)
创建时机:   首次 MemoryRepository 实例化时自动创建
创建方式:   执行 schema.sql 文件

与其他数据库的关系:
  lxl_v3.db           ← V3 新建
  trades.db           ← V2 已有，不碰
  backtest_results.db ← V2 已有，不碰
  research_notes.db   ← V2 已有，不碰（V2 管线继续使用）
  ...                 ← 其他 V2 数据库不动
```

### 3.2 表设计

```
lxl_v3.db 在 Phase 1 只创建 1 张表:
  memory_entries      — 统一记忆表

后续 Phase 追加:
  fundamental_snapshots  (Phase 2)
  fundamental_series     (Phase 2)
  research_projects      (Phase 3)
  validation_results     (Phase 4)
  report_archive         (Phase 3)
```

### 3.3 数据量估算

```
假设:
  - 活跃用户每天 1-3 条记录
  - 每年约 500-1000 条
  - 3 年累计 < 3000 条

SQLite 性能:
  - 3000 条: < 1MB 磁盘占用
  - FTS5 索引: < 500KB 额外空间
  - 全文搜索: < 5ms
  - 条件查询: < 1ms

结论: SQLite 完全够用，无需考虑性能优化。
```

---

## 4. memory_entries Schema

### 4.1 完整 DDL

```sql
-- ============================================================
-- memory_entries: V3 Investment Memory System 核心表
-- 承载四种记忆类型: note / thesis / decision / reflection
-- ============================================================

CREATE TABLE IF NOT EXISTS memory_entries (

    -- ── 主键 ──
    entry_id     INTEGER PRIMARY KEY AUTOINCREMENT,

    -- ── 核心分类字段 ──
    entry_type   TEXT    NOT NULL CHECK (entry_type IN (
                    'note',        -- 研究笔记
                    'thesis',      -- 投资论文
                    'decision',    -- 决策记录
                    'reflection'   -- 反思笔记
                 )),
    date         TEXT    NOT NULL,          -- ISO date "2026-08-06"
    title        TEXT    NOT NULL,          -- 标题（必填）
    content      TEXT    NOT NULL,          -- Markdown 正文（必填）

    -- ── 关联字段（全部可选，JSON array 存储）──
    symbols      TEXT    NOT NULL DEFAULT '[]',
        -- JSON array of strings
        -- thesis:   ["000858"]           — 论文涉及的标的
        -- decision: ["000858"]           — 交易的标的
        -- note:     ["000858","600519"]  — 笔记涉及的标的（可多个）
        -- reflection: []                  — 反思可不关联标的

    tags         TEXT    NOT NULL DEFAULT '[]',
        -- JSON array of strings
        -- 多级标签体系:
        --   资产: "股票","债券","基金"
        --   市场: "A股","港股","美股"
        --   行业: "消费","科技","金融","医疗","能源","制造"
        --   风格: "价值","成长","红利","周期","防御"
        --   策略: "趋势跟踪","均值回归","动量","基本面"
        --   主题: "AI","新能源","消费升级","老龄化"
        --   操作: "买入","卖出","加仓","减仓"
        --   结果: "盈利","亏损","持平"

    project_id   TEXT,
        -- 关联 Research Project (Phase 3 实现)
        -- Phase 1 设默认值 NULL 即可

    related_ids  TEXT    NOT NULL DEFAULT '[]',
        -- JSON array of integers
        -- 关联的其他 memory_entries.entry_id
        -- 例如: Decision 关联到 Thesis, Reflection 关联到 Decision

    -- ── Thesis 专属字段 ──
    -- (仅 entry_type='thesis' 时填充，其他类型为 NULL)

    thesis_conviction    REAL,
        -- 信心度: 0.0 - 1.0
        -- 用户自评，非 AI 判断
        -- 0.0 = 完全不确定，1.0 = 极度确信

    thesis_catalysts     TEXT,
        -- JSON array of strings
        -- 催化剂列表: ["Q3消费旺季","估值修复","政策利好"]

    thesis_risks         TEXT,
        -- JSON array of strings
        -- 风险列表: ["政策风险","竞争加剧","原材料涨价"]

    thesis_timeline      TEXT,
        -- 预期时间框架: "3个月" | "6个月" | "12个月"

    target_price         REAL,
        -- 目标价（元）

    pipeline_snapshot    TEXT,
        -- JSON blob: 管线验证结果的完整快照
        -- {
        --   "parsed_thesis": {...},
        --   "factor_model": {...},
        --   "strategy_spec": {...},
        --   "backtest_result": {...},
        --   "ai_assessment": {...}
        -- }

    report_path          TEXT,
        -- 关联的 V2 研究报告文件路径
        -- 例如: "reports/000858_20260806.md"

    -- ── Decision 专属字段 ──
    -- (仅 entry_type='decision' 时填充)

    decision_type        TEXT,
        -- "buy" | "sell" | "hold" | "add" | "reduce"

    decision_price       REAL,
        -- 成交价格

    decision_quantity    REAL,
        -- 成交数量（股）

    decision_reason      TEXT,
        -- 决策理由（自由文本）

    market_context       TEXT,
        -- 决策时的市场环境描述
        -- "沪深300震荡上行，消费板块资金流入，成交量温和放大"

    mood                 TEXT,
        -- 决策时的情绪状态
        -- "calm" | "excited" | "anxious" | "fearful" | "confident" | "uncertain"

    -- ── 结果追踪（Thesis 和 Decision 共用）──

    outcome_status       TEXT    DEFAULT 'pending',
        -- Thesis:  "pending" | "correct" | "wrong" | "expired" | "partial"
        -- Decision: "pending" | "good"    | "bad"   | "neutral"
        -- 其他类型: NULL

    outcome_detail       TEXT,
        -- 详细复盘笔记（Markdown）
        -- "论文方向正确但幅度不足。
        --  目标价 180 元，实际最高 165 元。
        --  消费复苏逻辑成立但力度弱于预期。"

    outcome_return       REAL,
        -- 实际收益（%）
        -- Thesis: 论文发布到目标时间的实际涨跌幅
        -- Decision: 交易盈亏百分比

    reviewed_at          TEXT,
        -- 复盘时间戳

    -- ── 时间戳 ──

    created_at   TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at   TEXT
);
```

### 4.2 索引设计

```sql
-- 查询频率最高的字段
CREATE INDEX IF NOT EXISTS idx_memory_type    ON memory_entries(entry_type);
CREATE INDEX IF NOT EXISTS idx_memory_date    ON memory_entries(date);
CREATE INDEX IF NOT EXISTS idx_memory_outcome ON memory_entries(outcome_status);
CREATE INDEX IF NOT EXISTS idx_memory_project ON memory_entries(project_id);
CREATE INDEX IF NOT EXISTS idx_memory_created ON memory_entries(created_at);

-- symbols 是 JSON array 字符串，用 LIKE 查询比全表扫描快
-- 但 SQLite 不支持 JSON 索引，所以用普通索引 + LIKE 匹配
CREATE INDEX IF NOT EXISTS idx_memory_symbols ON memory_entries(symbols);
```

### 4.3 Python 数据模型

```python
# src/v3/memory/models.py

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class MemoryEntry:
    """统一记忆条目 — V3 Investment Memory System 核心数据模型"""

    # ── 基础字段 ──
    entry_id: int = 0                      # 自增主键，新建时为 0
    entry_type: str = "note"               # note | thesis | decision | reflection
    date: str = ""                         # ISO date
    title: str = ""
    content: str = ""                      # Markdown

    # ── 关联字段 ──
    symbols: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    project_id: str | None = None
    related_ids: list[int] = field(default_factory=list)

    # ── Thesis 专属 ──
    thesis_conviction: float | None = None
    thesis_catalysts: list[str] | None = None
    thesis_risks: list[str] | None = None
    thesis_timeline: str | None = None
    target_price: float | None = None
    pipeline_snapshot: dict | None = None
    report_path: str | None = None

    # ── Decision 专属 ──
    decision_type: str | None = None        # buy | sell | hold | add | reduce
    decision_price: float | None = None
    decision_quantity: float | None = None
    decision_reason: str | None = None
    market_context: str | None = None
    mood: str | None = None

    # ── 结果追踪 ──
    outcome_status: str | None = None       # pending | correct | wrong | expired | partial
    outcome_detail: str | None = None
    outcome_return: float | None = None
    reviewed_at: str | None = None

    # ── 元数据 ──
    created_at: str = ""
    updated_at: str = ""


# 类型常量
ENTRY_TYPES = ("note", "thesis", "decision", "reflection")

ENTRY_TYPE_LABELS = {
    "note":       "📝 研究笔记",
    "thesis":     "💡 投资论文",
    "decision":   "📊 决策记录",
    "reflection": "🧠 反思笔记",
}

OUTCOME_STATUSES = {
    "thesis":    ("pending", "correct", "wrong", "expired", "partial"),
    "decision":  ("pending", "good", "bad", "neutral"),
}
```

### 4.4 数据验证规则

```python
# 在 repository.py 中实现

validation_rules = {
    # entry_type 必填且在枚举内
    "entry_type": lambda v: v in ENTRY_TYPES,

    # date 必填且为有效 ISO date
    "date": lambda v: bool(re.match(r"^\d{4}-\d{2}-\d{2}$", v)),

    # title 必填且非空
    "title": lambda v: len(v.strip()) > 0,

    # content 必填且非空
    "content": lambda v: len(v.strip()) > 0,

    # thesis_conviction 在 0.0-1.0 之间
    "conviction": lambda v: v is None or (0.0 <= v <= 1.0),

    # symbols 和 tags 是 list[str]
    "symbols": lambda v: isinstance(v, list) and all(isinstance(s, str) for s in v),
    "tags": lambda v: isinstance(v, list) and all(isinstance(t, str) for t in v),
}
```

---

## 5. FTS5 搜索设计

### 5.1 设计目标

```
搜索范围: title + content + tags + symbols
搜索语言: 中文 + 英文
性能目标: < 100ms（3000 条数据规模）
结果排序: 按 BM25 相关性评分降序
```

### 5.2 FTS5 表定义

```sql
-- FTS5 虚拟表，内容同步自 memory_entries
CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
    title,
    content,
    tags,
    symbols,
    content='memory_entries',      -- 内容表
    content_rowid='rowid',         -- 行标识
    tokenize='unicode61'           -- 分词器（支持中文 n-gram）
);
```

### 5.3 分词策略

```
SQLite FTS5 默认 tokenizer: unicode61
  - 英文: 空格和标点分词 → 正常工作
  - 中文: 默认按字符切分 → 支持单字匹配和短语匹配

FTS5 查询语法:
  "白酒 消费"        → AND 逻辑：包含"白酒"且包含"消费"
  "白酒 OR 茅台"     → OR 逻辑
  "消费 -白酒"       → 包含"消费"但不包含"白酒"
  "五粮液*"          → 前缀匹配
  "\"消费复苏\""     → 精确短语匹配
```

### 5.4 同步触发器

```sql
-- INSERT 触发器: 新条目自动加入 FTS 索引
CREATE TRIGGER IF NOT EXISTS memory_fts_ai AFTER INSERT ON memory_entries BEGIN
    INSERT INTO memory_fts(rowid, title, content, tags, symbols)
    VALUES (new.rowid, new.title, new.content, new.tags, new.symbols);
END;

-- DELETE 触发器: 删除条目自动从 FTS 索引移除
CREATE TRIGGER IF NOT EXISTS memory_fts_ad AFTER DELETE ON memory_entries BEGIN
    INSERT INTO memory_fts(memory_fts, rowid, title, content, tags, symbols)
    VALUES ('delete', old.rowid, old.title, old.content, old.tags, old.symbols);
END;

-- UPDATE 触发器: 更新条目时重建 FTS 索引
CREATE TRIGGER IF NOT EXISTS memory_fts_au AFTER UPDATE ON memory_entries BEGIN
    INSERT INTO memory_fts(memory_fts, rowid, title, content, tags, symbols)
    VALUES ('delete', old.rowid, old.title, old.content, old.tags, old.symbols);
    INSERT INTO memory_fts(rowid, title, content, tags, symbols)
    VALUES (new.rowid, new.title, new.content, new.tags, new.symbols);
END;
```

### 5.5 搜索实现

```python
# src/v3/memory/search.py

class MemorySearch:
    """基于 SQLite FTS5 的 Memory 搜索引擎"""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def search(
        self,
        query: str,
        entry_type: str | None = None,
        symbols: list[str] | None = None,
        tags: list[str] | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        outcome_status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[MemoryEntry]:
        """
        全文搜索 + 条件筛选

        Args:
            query: FTS5 搜索字符串。支持:
                   "白酒"            — 单词搜索
                   "白酒 消费"       — AND 搜索
                   "白酒 OR 茅台"    — OR 搜索
                   "\"消费复苏\""    — 精确短语
            entry_type: 筛选类型
            symbols: 筛选标的
            tags: 筛选标签
            date_from/date_to: 日期范围
            outcome_status: 结果状态筛选
            limit/offset: 分页
        """
        ...

    def list_all(
        self,
        entry_type: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[MemoryEntry]:
        """列表查询（非搜索），支持筛选和分页"""
        ...

    def get_pending_reviews(self) -> list[MemoryEntry]:
        """获取所有待复盘的 thesis（outcome_status='pending'）"""
        ...
```

### 5.6 搜索 SQL 构建逻辑

```python
def _build_search_sql(self, query: str, **filters) -> tuple[str, list]:
    """
    构建参数化搜索 SQL。

    示例:
      query="白酒 消费", entry_type="thesis"
      →
      SELECT me.* FROM memory_entries me
      JOIN memory_fts fts ON me.rowid = fts.rowid
      WHERE memory_fts MATCH ?
        AND me.entry_type = ?
      ORDER BY rank
      LIMIT ? OFFSET ?
      params: ["白酒 消费", "thesis", 50, 0]
    """
    ...
```

---

## 6. API 设计

### 6.1 路由总览

```
所有路由挂在现有 Flask app (web_modern.py) 上。
不创建新的 Blueprint 或 Flask 实例。

Base URL: http://127.0.0.1:5000

页面路由:
  GET  /journal                  → journal.html（记忆日记页面）
  GET  /workspace                → workspace/dashboard.html（Dashboard 首页）

API 路由:
  GET    /api/memory/list        → 列表查询（筛选 + 分页）
  GET    /api/memory/search?q=   → 全文搜索
  POST   /api/memory/create      → 创建记忆条目
  GET    /api/memory/<id>        → 获取单条详情
  PUT    /api/memory/<id>        → 更新条目
  DELETE /api/memory/<id>        → 删除条目
  POST   /api/memory/<id>/review → 复盘（更新 outcome）
  GET    /api/memory/analytics   → Memory Analytics 聚合数据
  GET    /api/memory/pending-reviews → 待复盘列表
```

### 6.2 接口详细规格

#### `GET /api/memory/list`

```
查询参数:
  entry_type     string  可选  筛选类型: note|thesis|decision|reflection
  symbols        string  可选  筛选标的: "000858,600519"
  tags           string  可选  筛选标签: "消费,白酒"
  date_from      string  可选  起始日期: "2026-01-01"
  date_to        string  可选  结束日期: "2026-08-06"
  outcome        string  可选  结果状态: pending|correct|wrong|expired
  limit          int     可选  每页条数，默认 50
  offset         int     可选  偏移量，默认 0

响应 (200):
  {
    "entries": [...],
    "total": 47,
    "limit": 50,
    "offset": 0
  }

示例:
  GET /api/memory/list?entry_type=thesis&outcome=pending&limit=20
  → 返回待复盘的 thesis，前 20 条
```

#### `GET /api/memory/search`

```
查询参数:
  q              string  必填  搜索关键词（FTS5 语法）
  entry_type     string  可选  类型筛选
  limit          int     可选  默认 50

响应 (200):
  {
    "query": "白酒 消费",
    "entries": [...],
    "total": 12
  }

示例:
  GET /api/memory/search?q=白酒+消费
  → FTS5 全文搜索
```

#### `POST /api/memory/create`

```
Content-Type: application/json

请求体:
  {
    "entry_type": "thesis",
    "date": "2026-08-06",
    "title": "五粮液：消费复苏 + 估值修复",
    "content": "## 投资逻辑\n\n...",
    "symbols": ["000858"],
    "tags": ["消费", "白酒", "价值"],
    "thesis_conviction": 0.7,
    "thesis_catalysts": ["Q3消费旺季", "估值修复"],
    "thesis_risks": ["政策风险", "竞争加剧"],
    "target_price": 180.0
  }

响应 (201):
  {
    "entry_id": 42,
    "message": "created"
  }

错误 (400):
  {
    "error": "validation_failed",
    "details": {"entry_type": "must be one of: note, thesis, decision, reflection"}
  }
```

#### `GET /api/memory/<int:entry_id>`

```
响应 (200):
  {
    "entry_id": 42,
    "entry_type": "thesis",
    "date": "2026-08-06",
    "title": "五粮液：消费复苏 + 估值修复",
    "content": "## 投资逻辑\n\n...",
    "symbols": ["000858"],
    "tags": ["消费", "白酒"],
    "thesis_conviction": 0.7,
    "outcome_status": "pending",
    "created_at": "2026-08-06 15:30:00",
    "updated_at": null
  }

错误 (404):
  {
    "error": "not_found"
  }
```

#### `PUT /api/memory/<int:entry_id>`

```
请求体: 要更新的字段（部分更新）
  {
    "title": "五粮液：消费复苏 + 估值修复 [已更新]",
    "content": "## 更新后的内容\n\n..."
  }

响应 (200):
  {
    "entry_id": 42,
    "message": "updated"
  }
```

#### `DELETE /api/memory/<int:entry_id>`

```
响应 (200):
  {
    "entry_id": 42,
    "message": "deleted"
  }
```

#### `POST /api/memory/<int:entry_id>/review`

```
请求体:
  {
    "outcome_status": "correct",
    "outcome_detail": "论文方向正确，目标价 180 实际到达 178，涨幅 22%",
    "outcome_return": 22.0
  }

响应 (200):
  {
    "entry_id": 42,
    "message": "reviewed",
    "outcome_status": "correct"
  }
```

#### `GET /api/memory/analytics`

```
响应 (200):
  {
    "total_entries": 47,
    "by_type": {
      "note": 12,
      "thesis": 15,
      "decision": 14,
      "reflection": 6
    },
    "thesis_stats": {
      "total": 15,
      "hit_rate": 0.62,
      "high_conviction_total": 5,
      "high_conviction_hit_rate": 0.80,
      "low_conviction_total": 4,
      "low_conviction_hit_rate": 0.25,
      "pending_reviews": 3,
      "by_tag": {
        "消费": {"total": 8, "correct": 6, "hit_rate": 0.75},
        "科技": {"total": 5, "correct": 2, "hit_rate": 0.40}
      }
    },
    "decision_stats": {
      "total": 14,
      "win_rate": 0.58,
      "by_mood": {
        "confident": {"total": 6, "good": 4, "win_rate": 0.67},
        "anxious": {"total": 3, "good": 1, "win_rate": 0.33}
      }
    },
    "recent_lessons": [
      {"entry_id": 40, "title": "追高买入的教训", "created_at": "..."},
      ...
    ],
    "streak_days": 12
  }
```

#### `GET /api/memory/pending-reviews`

```
响应 (200):
  {
    "pending_reviews": [
      {
        "entry_id": 15,
        "title": "五粮液：消费复苏 + 估值修复",
        "symbols": ["000858"],
        "thesis_conviction": 0.7,
        "created_at": "2026-05-06",
        "days_since_created": 92
      },
      ...
    ],
    "total": 3
  }
```

### 6.3 认证要求

所有 `/api/memory/*` 路由使用 V2 已有的 `@token_required` 装饰器：

```python
# web_modern.py

@app.route("/api/memory/list")
@token_required
def api_memory_list(current_user):
    ...
```

---

## 7. Web 页面设计

### 7.1 页面清单

```
Phase 1 创建 2 个页面:

templates/v3/journal.html
  - 路径: /journal
  - 功能: 记忆日记（日历 + 列表 + 搜索 + CRUD）

templates/v3/workspace/dashboard.html
  - 路径: /workspace
  - 功能: Dashboard 首页（KPI + 最近活动 + Memory Insights + 待复盘）
```

### 7.2 `/journal` 页面设计

```
┌──────────────────────────────────────────────────────────────┐
│  [LXL·QuantAxis V3]    Workspace  Pipeline  Journal  Companies│
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─ 操作栏 ───────────────────────────────────────────────┐  │
│  │ [+ New Entry]  [搜索: ____________] [🔍]               │  │
│  │                                                        │  │
│  │ 筛选: [类型: 全部 ▼] [标的: ____] [标签: ____]         │  │
│  │       [日期: 从 __ 到 __] [结果: 全部 ▼]              │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌─ 日历面板 ────────────────────────────────────────────┐  │
│  │  ◀ July                    August 2026              ▶  │  │
│  │  Mo   Tu   We   Th   Fr   Sa   Su                      │  │
│  │                           ·    ·    ·                   │  │
│  │   4    5    6    7    8    9   10                      │  │
│  │        ●    ●                                             │  │
│  │      thesis decision                                      │  │
│  │  11   12   13   14   15   16   17                      │  │
│  │  ...                                                    │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌─ 条目列表 ────────────────────────────────────────────┐  │
│  │                                                        │  │
│  │  ┌──────────────────────────────────────────────────┐  │  │
│  │  │ 💡 Thesis · 2026-08-06                    [Edit] │  │  │
│  │  │ 五粮液：消费复苏 + 估值修复                        │  │  │
│  │  │ 000858 · conviction: 0.7 · pending review         │  │  │
│  │  │ tags: 消费 白酒 价值                               │  │  │
│  │  │ ───────────────────────────────────               │  │  │
│  │  │ ## 投资逻辑                                       │  │  │
│  │  │ 五粮液受益于消费复苏和高端白酒结构性升级...          │  │  │
│  │  │ [展开更多]                                         │  │  │
│  │  └──────────────────────────────────────────────────┘  │  │
│  │                                                        │  │
│  │  ┌──────────────────────────────────────────────────┐  │  │
│  │  │ 📊 Decision · 2026-08-05                  [Edit] │  │  │
│  │  │ 买入中芯国际 @ ¥58                                 │  │  │
│  │  │ 688981 · 5,000 shares · outcome: pending          │  │  │
│  │  │ reason: 芯片周期底部，AI算力需求驱动               │  │  │
│  │  └──────────────────────────────────────────────────┘  │  │
│  │                                                        │  │
│  │  ┌──────────────────────────────────────────────────┐  │  │
│  │  │ 📝 Note · 2026-08-04                      [Edit] │  │  │
│  │  │ 消费板块 Q2 财报总结                               │  │  │
│  │  │ tags: 消费 财报 Q2                                 │  │  │
│  │  └──────────────────────────────────────────────────┘  │  │
│  │                                                        │  │
│  │  ── 分页: ◀ 1 2 3 ... 5 ▶  (共 47 条) ──            │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌─ New/Edit Entry Modal（弹窗）────────────────────────┐   │
│  │                                                        │  │
│  │  类型: [thesis ▼]                                      │  │
│  │  日期: [2026-08-06]                                    │  │
│  │  标题: [___________________________________]           │  │
│  │  标的: [________] [+添加]                               │  │
│  │  标签: [________] [+添加]                               │  │
│  │                                                        │  │
│  │  正文 (Markdown):                                      │  │
│  │  ┌──────────────────────────────────────────────┐    │  │
│  │  │                                              │    │  │
│  │  │  ## 投资逻辑                                  │    │  │
│  │  │                                              │    │  │
│  │  │  1. ...                                      │    │  │
│  │  │  2. ...                                      │    │  │
│  │  │                                              │    │  │
│  │  └──────────────────────────────────────────────┘    │  │
│  │                                                        │  │
│  │  [Thesis 专属字段 — 仅 entry_type=thesis 时显示]       │  │
│  │  信心度: [0.7] (0-1)                                   │  │
│  │  目标价: [180.0]                                       │  │
│  │  催化剂: [________] [+添加]                             │  │
│  │  风险:   [________] [+添加]                             │  │
│  │  时间框架: [6个月 ▼]                                    │  │
│  │                                                        │  │
│  │  [Decision 专属字段 — 仅 entry_type=decision 时显示]   │  │
│  │  操作: [买入 ▼]  价格: [145.0]  数量: [1000]          │  │
│  │  理由: [__________________________]                    │  │
│  │  市场环境: [_______________________]                    │  │
│  │  情绪: [calm ▼]                                        │  │
│  │                                                        │  │
│  │  [Cancel]  [Save]                                      │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

### 7.3 `/workspace` Dashboard 页面设计

```
┌──────────────────────────────────────────────────────────────┐
│  [LXL·QuantAxis V3]    Workspace  Pipeline  Journal  Companies│
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  Welcome back, 研究员                         2026-08-06 周三 │
│                                                               │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐   │
│  │ 📝       │ 🎯       │ ⏳       │ 📊       │ 🔥       │   │
│  │ 论文总数  │ 命中率    │ 待复盘    │ 决策胜率  │ 连续记录  │   │
│  │   15     │  62% ▲   │    3     │  58%     │  12天    │   │
│  └──────────┴──────────┴──────────┴──────────┴──────────┘   │
│                                                               │
│  ┌─── Quick Actions ────────┐  ┌─── Recent Activity ──────┐ │
│  │                           │  │                            │ │
│  │ [✏️ 写投资论文]            │  │ 2h ago  💡 Thesis created  │ │
│  │ [📝 写研究笔记]            │  │   五粮液：消费复苏...      │ │
│  │ [📊 记录交易决策]          │  │                            │ │
│  │ [🧠 写反思笔记]            │  │ 1d ago  📊 Decision made   │ │
│  │ [🔬 跑 AI 研究管线]        │  │   买入中芯国际 @ ¥58      │ │
│  │ [📄 生成研究报告]          │  │                            │ │
│  └───────────────────────────┘  │ 3d ago  ✅ Thesis reviewed  │ │
│                                  │   茅台：估值修复 ✓         │ │
│  ┌─── Memory Insights ────────┐ │                            │ │
│  │                             │ │ 5d ago  📝 Note created    │ │
│  │ 信心校准:                   │ │   消费板块 Q2 财报总结     │ │
│  │   高信心(>0.7): ████ 80%   │ └────────────────────────────┘ │
│  │   中信心(0.5-0.7): ██ 50%  │                                │
│  │   低信心(<0.5): █ 25%      │  ┌─── Pending Reviews ──────┐ │
│  │                             │  │                            │ │
│  │ 板块表现:                   │  │ ⏳ 五粮液 Thesis (92天)   │ │
│  │   消费: ██████ 75% (6/8)   │  │   消费复苏 + 估值修复      │ │
│  │   科技: ██ 40% (2/5)       │  │   conviction: 0.7          │ │
│  │   金融: ████ 67% (2/3)     │  │   [Review →]               │ │
│  │                             │  │                            │ │
│  │ 最近教训:                   │  │ ⏳ 药明康德 Thesis (60天) │ │
│  │ 💡 追高买入→回撤超限       │  │   医药 CXO 周期反转       │ │
│  │ 💡 基本面恶化不抄底         │  │   conviction: 0.5          │ │
│  │ 💡 高信心时才重仓           │  │   [Review →]               │ │
│  └─────────────────────────────┘  │                            │ │
│                                    │ ⏳ 宁德时代 Thesis (45天) │ │
│                                    │   锂电龙头估值修复        │ │
│                                    │   conviction: 0.6          │ │
│                                    │   [Review →]               │ │
│                                    └────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

### 7.4 前端技术方案

```
技术栈:
  - Jinja2 服务端模板渲染（Flask 内置）
  - HTMX: 无整页刷新（列表筛选、搜索、分页、CRUD）
  - Alpine.js: 客户端交互（Modal 开关、表单切换、日历交互）
  - Plotly: 暂不需要（Phase 1 无图表）

CSS:
  - 复用 V2 的 terminal.css 暗色主题设计系统
  - 新增 v3-shell.css: 导航栏 + 布局 + 卡片 + 日历 + Modal

JS 库:
  - htmx.org@1.9.x（CDN，约 14KB）
  - alpinejs@3.x（CDN，约 15KB）
  - 无构建工具，无 npm，无打包
```

---

## 8. V2 管线连接方式

### 8.1 设计原则

```
集成方式:  非侵入钩子（Non-invasive Hook）
触发时机:  7-stage pipeline 完成、报告生成后
失败处理:  静默失败 — Memory 写入失败不影响管线返回结果
代码位置:  src/lxl_quantaxis/research/application.py
代码量:    ~25 行
```

### 8.2 集成点

```python
# 文件: src/lxl_quantaxis/research/application.py
# 位置: EquityResearchService.run_pipeline() 方法末尾

class EquityResearchService:
    def run_pipeline(self, thesis_text: str) -> ResearchReport:
        # =========================================
        # Stage 1-7: V2 现有管线（完全不改）
        # =========================================
        parsed_thesis = self.ai_parser.parse(thesis_text)
        factor_model = self.factor_mapper.map(parsed_thesis)
        strategy_spec = self.strategy_builder.build(factor_model)
        self.validator.validate(strategy_spec)
        backtest_result = self.backtest_bridge.run(strategy_spec)
        ai_assessment = self.backtest_analyzer.analyze(backtest_result)
        report = self.report_generator.generate(
            parsed_thesis, factor_model, strategy_spec,
            backtest_result, ai_assessment
        )

        # =========================================
        # ★ V3 HOOK: 管线结果写入 Memory（Phase 1 新增）
        # =========================================
        self._save_to_memory(
            thesis_text=thesis_text,
            parsed_thesis=parsed_thesis,
            factor_model=factor_model,
            strategy_spec=strategy_spec,
            backtest_result=backtest_result,
            ai_assessment=ai_assessment,
            report_path=report.file_path,
        )

        return report

    def _save_to_memory(self, **kwargs):
        """
        V3 钩子: 将管线结果保存到 Memory System。

        此方法:
        - 静默失败（异常被捕获，不向上传播）
        - 不阻塞管线返回
        - 不影响 V2 任何行为
        """
        try:
            from src.v3.memory.repository import MemoryRepository
            from src.v3.memory.models import MemoryEntry

            repo = MemoryRepository()

            entry = MemoryEntry(
                entry_type="thesis",
                date=datetime.now().strftime("%Y-%m-%d"),
                title=self._extract_title(kwargs["parsed_thesis"]),
                content=kwargs["thesis_text"],
                symbols=[kwargs["parsed_thesis"].symbol],
                tags=self._extract_tags(kwargs["parsed_thesis"]),
                thesis_conviction=kwargs["parsed_thesis"].confidence or 0.5,
                thesis_catalysts=kwargs["parsed_thesis"].catalysts or [],
                thesis_risks=kwargs["parsed_thesis"].risks or [],
                target_price=kwargs["parsed_thesis"].target_price,
                pipeline_snapshot={
                    "parsed_thesis": dataclasses.asdict(kwargs["parsed_thesis"]),
                    "factor_model": dataclasses.asdict(kwargs["factor_model"]),
                    "strategy_spec": dataclasses.asdict(kwargs["strategy_spec"]),
                    "backtest_result": kwargs["backtest_result"],
                    "ai_assessment": kwargs["ai_assessment"],
                },
                report_path=kwargs["report_path"],
            )
            repo.save(entry)

        except ImportError:
            # V3 模块未安装，静默跳过
            pass
        except Exception as e:
            # Memory 写入失败不应该影响管线
            import logging
            logging.getLogger("lxl.v3").warning(
                f"Failed to save pipeline result to memory: {e}"
            )

    def _extract_title(self, parsed_thesis) -> str:
        """从结构化论文中提取标题"""
        # 从 symbol + direction + core argument 生成标题
        ...

    def _extract_tags(self, parsed_thesis) -> list[str]:
        """从结构化论文中提取标签"""
        # 从 sector, style, theme 字段生成标签
        ...
```

### 8.3 修改范围

```
修改文件: src/lxl_quantaxis/research/application.py
修改内容:
  - 新增 import (1 行)
  - 新增 _save_to_memory 方法 (~20 行)
  - 新增 _extract_title 方法 (~5 行)
  - 新增 _extract_tags 方法 (~5 行)
  - 在 run_pipeline 末尾调用 _save_to_memory (1 行)
修改行数: ~32 行
风险等级: 极低（try/except 保护，静默失败）
```

---

## 9. 测试方案

### 9.1 测试文件

```
tests/v3/
├── __init__.py
└── test_memory.py          # Memory System 完整测试套件
```

### 9.2 测试用例清单

```
═══════════════════════════════════════════════════════════════
Category 1: 数据模型测试 (5 tests)
═══════════════════════════════════════════════════════════════

T1.1  test_create_memory_entry_thesis
      创建 thesis 类型 MemoryEntry → 验证所有字段

T1.2  test_create_memory_entry_decision
      创建 decision 类型 MemoryEntry → 验证 decision_* 字段

T1.3  test_create_memory_entry_note
      创建 note 类型 → 验证基础字段

T1.4  test_create_memory_entry_reflection
      创建 reflection 类型 → 验证 related_ids 关联

T1.5  test_memory_entry_defaults
      验证默认值: symbols=[], tags=[], outcome_status=None, related_ids=[]

═══════════════════════════════════════════════════════════════
Category 2: Repository CRUD 测试 (6 tests)
═══════════════════════════════════════════════════════════════

T2.1  test_save_and_retrieve
      save(entry) → get_by_id(id) → 验证数据往返一致性

T2.2  test_update_entry
      创建 → 更新 title → 验证 updated_at 变化

T2.3  test_delete_entry
      创建 → 删除 → get_by_id → 404

T2.4  test_list_with_filters
      创建 5 条不同类型的条目 → 按 type 筛选 → 验证数量

T2.5  test_list_with_date_range
      创建不同日期的条目 → 按日期范围筛选

T2.6  test_list_pagination
      创建 100 条 → limit=20, offset=40 → 验证返回 20 条

═══════════════════════════════════════════════════════════════
Category 3: FTS5 搜索测试 (5 tests)
═══════════════════════════════════════════════════════════════

T3.1  test_search_chinese_single_word
      创建含"白酒"的条目 → 搜索"白酒" → 返回匹配条目

T3.2  test_search_chinese_phrase
      创建含"消费复苏"的条目 → 搜索"消费复苏" → 返回匹配条目

T3.3  test_search_and_logic
      搜索"白酒 消费" → AND 逻辑验证

T3.4  test_search_no_results
      搜索"比特币" → 返回空列表

T3.5  test_search_with_type_filter
      搜索"白酒" + entry_type=thesis → 只返回 thesis

═══════════════════════════════════════════════════════════════
Category 4: Analytics 测试 (4 tests)
═══════════════════════════════════════════════════════════════

T4.1  test_thesis_hit_rate
      创建 5 条 thesis: 3 correct + 2 wrong → hit_rate = 0.6

T4.2  test_conviction_calibration
      高信心(>0.7) thesis: 4/5 correct → high_conviction_hit_rate = 0.8
      低信心(<0.5) thesis: 1/4 correct → low_conviction_hit_rate = 0.25

T4.3  test_decision_win_rate
      创建 decisions: 3 good + 2 bad → win_rate = 0.6

T4.4  test_pending_reviews
      创建 thesis: 2 pending + 3 reviewed → pending_reviews = 2

═══════════════════════════════════════════════════════════════
Category 5: Review 流程测试 (3 tests)
═══════════════════════════════════════════════════════════════

T5.1  test_review_thesis
      创建 thesis(pending) → review(correct, return=22%)
      → 验证 outcome_status="correct", reviewed_at 非空

T5.2  test_review_updates_analytics
      创建 thesis + review → analytics.hit_rate 更新

T5.3  test_cannot_review_non_thesis
      尝试 review 一个 note → 返回错误

═══════════════════════════════════════════════════════════════
Category 6: 管线集成测试 (3 tests)
═══════════════════════════════════════════════════════════════

T6.1  test_pipeline_saves_to_memory
      运行 pipeline → 检查 memory_entries 表有新 thesis

T6.2  test_pipeline_continues_on_memory_failure
      模拟 Memory DB 损坏 → pipeline 正常返回报告

T6.3  test_pipeline_tags_extraction
      运行 pipeline → 验证自动生成的 tags 合理

═══════════════════════════════════════════════════════════════
Category 7: 边界与异常测试 (4 tests)
═══════════════════════════════════════════════════════════════

T7.1  test_validation_rejects_invalid_type
      entry_type="invalid" → 返回验证错误

T7.2  test_validation_rejects_empty_title
      title="" → 返回验证错误

T7.3  test_validation_rejects_invalid_conviction
      thesis_conviction=1.5 → 返回验证错误

T7.4  test_handles_empty_database
      空数据库 → list 返回空列表, analytics 返回 0 值

═══════════════════════════════════════════════════════════════
Total: 30 tests
═══════════════════════════════════════════════════════════════
```

### 9.3 测试基础设施

```python
# tests/v3/conftest.py (如需要)

import pytest
import tempfile
import os

@pytest.fixture
def memory_repo():
    """创建临时数据库的 MemoryRepository"""
    from src.v3.memory.repository import MemoryRepository
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    repo = MemoryRepository(db_path)
    yield repo
    os.unlink(db_path)

@pytest.fixture
def sample_thesis():
    """标准 thesis 测试数据"""
    from src.v3.memory.models import MemoryEntry
    return MemoryEntry(
        entry_type="thesis",
        date="2026-08-06",
        title="测试论文：消费复苏",
        content="## 投资逻辑\n\n测试内容",
        symbols=["000858"],
        tags=["消费", "白酒"],
        thesis_conviction=0.7,
        thesis_catalysts=["消费旺季"],
        thesis_risks=["政策风险"],
        target_price=180.0,
    )
```

---

## 10. Commit 计划

### 10.1 Week 1: Data Layer (7 commits)

```
Commit 1: feat(v3): initialize src/v3/ package structure
  - 创建 src/v3/__init__.py
  - 创建 src/v3/db.py（lxl_v3.db 自动初始化）
  - 更新 pyproject.toml 的 packages 配置（如需要）
  Files: 3
  Lines: ~30

Commit 2: feat(memory): add MemoryEntry dataclass and type constants
  - 创建 src/v3/memory/__init__.py
  - 创建 src/v3/memory/models.py
  - MemoryEntry(frozen, slots) + ENTRY_TYPES + ENTRY_TYPE_LABELS
  Files: 2
  Lines: ~80

Commit 3: feat(memory): add schema.sql with memory_entries DDL + FTS5 + triggers
  - 创建 src/v3/memory/schema.sql
  - CREATE TABLE memory_entries
  - CREATE VIRTUAL TABLE memory_fts
  - CREATE TRIGGER x3 (INSERT/UPDATE/DELETE)
  - CREATE INDEX x6
  Files: 1
  Lines: ~120

Commit 4: feat(memory): add MemoryRepository — core CRUD operations
  - 创建 src/v3/memory/repository.py
  - save(entry) → int
  - get_by_id(id) → MemoryEntry | None
  - update(id, fields) → None
  - delete(id) → None
  - list_all(filters) → list[MemoryEntry]
  - JSON serialization for symbols/tags/related_ids/pipeline_snapshot
  - Input validation
  Files: 1
  Lines: ~250

Commit 5: feat(memory): add MemorySearch — FTS5 query engine
  - 创建 src/v3/memory/search.py
  - search(query, filters) → list[MemoryEntry]
  - list_all(filters) → list[MemoryEntry]
  - get_pending_reviews() → list[MemoryEntry]
  - Parameterized SQL to prevent injection
  Files: 1
  Lines: ~150

Commit 6: feat(memory): add MemoryAnalytics — aggregate statistics
  - 创建 src/v3/memory/analytics.py
  - get_stats() → dict with hit_rate, calibration, by_tag, by_mood
  - get_pending_reviews() → list with days_since_created
  - get_recent_lessons(limit=5) → list
  - get_streak_days() → int
  Files: 1
  Lines: ~120

Commit 7: feat(memory): add ReviewEngine — outcome tracking
  - 创建 src/v3/memory/review.py
  - review_entry(entry_id, outcome_status, detail, return)
  - 验证 outcome_status 合法性
  - 验证 entry_type 必须是 thesis 或 decision
  Files: 1
  Lines: ~60
```

### 10.2 Week 2: Web Layer + Integration (7 commits)

```
Commit 8: feat(web): add /api/memory/* routes to web_modern.py
  - GET /api/memory/list
  - GET /api/memory/search?q=
  - POST /api/memory/create
  - GET /api/memory/<id>
  - PUT /api/memory/<id>
  - DELETE /api/memory/<id>
  - POST /api/memory/<id>/review
  - GET /api/memory/analytics
  - GET /api/memory/pending-reviews
  - 所有路由使用 @token_required
  - JSON 请求体解析 + 验证错误处理
  Files: 1 (web_modern.py)
  Lines: ~150

Commit 9: feat(web): add /journal page — calendar + entry list
  - 创建 templates/v3/journal.html
  - 日历视图（当月日历 + 有记录的日期高亮）
  - 条目列表（卡片式，每种 type 不同图标和颜色）
  - 筛选栏（type/date/symbols/tags/outcome）
  - HTMX 实现无刷新筛选和分页
  - 搜索框 + FTS5 搜索结果展示
  Files: 1
  Lines: ~200

Commit 10: feat(web): add journal entry editor — create/edit modal
  - New Entry Modal（弹窗）
  - Edit Entry Modal
  - 类型切换时动态显示/隐藏专属字段
  - Markdown 正文输入（textarea）
  - 标签和标的多值输入
  - HTMX POST → 服务器验证 → 错误提示或成功刷新列表
  Files: 1 (journal.html 内)
  Lines: ~150

Commit 11: feat(web): add /workspace dashboard page
  - 创建 templates/v3/workspace/dashboard.html
  - KPI 卡片行（论文总数/命中率/待复盘/决策胜率/连续记录）
  - Quick Actions 按钮组
  - Recent Activity 时间线（最近 10 条）
  - Memory Insights（信心校准 + 板块表现）
  - Pending Reviews 列表
  - Recent Lessons 列表
  Files: 1
  Lines: ~200

Commit 12: feat(research): add memory hook to V2 pipeline
  - 修改 src/lxl_quantaxis/research/application.py
  - 新增 _save_to_memory() 方法
  - 新增 _extract_title() 和 _extract_tags() 辅助方法
  - try/except 保护，静默失败
  Files: 1 (修改)
  Lines: ~32

Commit 13: test(memory): add comprehensive test suite
  - 创建 tests/v3/__init__.py
  - 创建 tests/v3/test_memory.py
  - 30 test cases covering all categories
  Files: 2
  Lines: ~400

Commit 14: docs: update changelog and documentation for Phase 1
  - 更新 CHANGELOG.md
  - 更新 ARCHITECTURE.md 的 V3 部分
  - 标记 Phase 1 完成
  Files: 2
  Lines: ~50
```

### 10.3 Commit 统计

```
Phase 1: 14 commits
  Week 1: 7 commits (Data Layer)
  Week 2: 7 commits (Web Layer + Integration)

New files:     12
Modified files: 3
Total lines:   ~1,900
Test cases:    30
```

---

## 11. 验收清单

### 11.1 功能验收

| # | 验收项 | 测试方式 |
|---|--------|----------|
| F1 | 创建 note/thesis/decision/reflection 四种类型的 MemoryEntry | 手动 /journal → 各创建一条 |
| F2 | FTS5 中文搜索返回正确结果 | 搜索"白酒" → 返回含"白酒"的条目 |
| F3 | FTS5 AND 搜索 | 搜索"白酒 消费" → 返回同时包含两者的条目 |
| F4 | 按 entry_type 筛选 | 筛选 thesis → 只显示 thesis |
| F5 | 按 date 范围筛选 | 选日期范围 → 正确筛选 |
| F6 | 编辑条目 | 修改 title → 保存 → 刷新 → 确认更新 |
| F7 | 删除条目 | 删除 → 确认消失 |
| F8 | Review thesis（标记 outcome） | 标记 correct → outcome_status 更新 |
| F9 | Memory Analytics 数据正确 | 检查命中率、信心校准计算 |
| F10 | Pending Reviews 列表正确 | 只看 outcome_status='pending' |
| F11 | 管线完成后自动创建 thesis | 跑 pipeline → /journal 出现新 thesis |
| F12 | 管线 Memory 写入失败不影响管线 | 模拟 DB 错误 → 管线正常返回报告 |

### 11.2 非功能验收

| # | 验收项 | 标准 |
|---|--------|------|
| NF1 | 零新增依赖 | `pip freeze` diff = 空 |
| NF2 | V2 测试全部通过 | `pytest tests/` 400+ tests pass |
| NF3 | 新代码测试覆盖率 | > 80% |
| NF4 | 搜索性能 | FTS5 搜索 < 50ms（3000 条以内） |
| NF5 | V2 管线不受影响 | demo_ai_research.py 输出不变 |
| NF6 | 代码风格 | ruff check src/v3/ 零错误 |
| NF7 | 类型检查 | mypy src/v3/ --strict 通过 |
| NF8 | 数据库自动创建 | 删除 lxl_v3.db → 重启自动创建 |

---

> **Phase 1 设计完成。下一步：按 Commit 1 开始实施。**
