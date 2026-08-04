# Web Refactor Plan — web_modern.py (3242行 → Blueprints)

**日期**: 2026-08-04  
**当前**: 单文件 3242行, 60+ 路由, 模板内联, SocketIO混用

## 目标结构

```
web_modern.py              → 精简为 app factory (~100行)

web/
├── __init__.py            # create_app() factory
├── config.py              # Flask + SocketIO config
├── routes/
│   ├── __init__.py        # 注册所有 blueprint
│   ├── market.py          # /api/kline, /api/stock, /api/valuation, /api/signals
│   ├── strategy.py        # /api/strategies, /api/strategy_list, /api/run_strategy,
│   │                      #   /api/backtest, /api/factor_backtest, /api/diagnosis
│   ├── portfolio.py       # /api/portfolio, /api/daily_brief, /api/daily_scan
│   ├── research.py        # /api/recommend, /api/factors, /api/valuation
│   ├── ai.py              # /api/ai/chat, /api/ai/create_strategy, /api/ai/review,
│   │                      #   /api/ai/market, /api/ai/recommend_chat
│   ├── auth.py            # /api/login, /api/register, /api/me, /api/alert
│   ├── admin.py           # /api/admin/*, /api/database/*
│   ├── game.py            # /api/game/*
│   └── pages.py           # /, /v2, /classic, /studio, /game, /admin (页面路由)
├── services/              # 业务逻辑 (从 routes 中抽离)
│   ├── backtest_service.py
│   ├── ai_service.py
│   └── portfolio_service.py
└── templates/             # Jinja2 模板 (替代内联 HTML 字符串)
    ├── v2_dashboard.html
    ├── classic.html
    └── ...
```

## 迁移步骤

### Step 1: 抽离页面路由 → `routes/pages.py`
- `/` → redirect /v2
- `/v2` → v2_dashboard HTML
- `/classic` → 经典面板 HTML
- `/studio` → 交易工作室
- `/game` → 模拟交易
- `/admin` → 管理后台
- `/login` → 登录页

### Step 2: 抽离行情路由 → `routes/market.py`
- `/api/kline`, `/api/kline/poll`, `/api/kline/<symbol>`
- `/api/stock/lookup`, `/api/stock/search`, `/api/stock/quote`
- `/api/valuation`
- `/api/signals`
- `/api/chart_data`

### Step 3: 抽离策略路由 → `routes/strategy.py`
- `/api/strategies`, `/api/strategy_list`
- `/api/run_strategy`, `/api/backtest`
- `/api/factor_backtest`, `/api/diagnosis`
- `/api/strategy_bank`, `/api/strategy_bank/<id>`

### Step 4: 抽离 AI 路由 → `routes/ai.py`
- `/api/ai/chat`, `/api/ai/create_strategy`
- `/api/ai/review`, `/api/ai/market`, `/api/ai/recommend_chat`

### Step 5: 抽离认证路由 → `routes/auth.py`
- `/api/login`, `/api/register`, `/api/me`
- `/api/alert`

### Step 6: 抽离管理+游戏路由

### Step 7: 创建 services/ 层
将 routes 中的业务逻辑（回测执行、AI调用、组合计算）移到 services/。

## 每步验证

- 启动 `python app.py` → 所有 URL 返回相同状态码
- `pytest tests/` → 394 tests pass
- 手动验证每个页面加载正常

## 不改的部分

- 路由 URL 不变
- 请求/响应格式不变
- 认证装饰器不变
- SocketIO 事件名称不变
