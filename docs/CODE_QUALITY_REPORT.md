# Code Quality Report — Phase 1.5 Validation

**日期**: 2026-08-04  
**分支**: `fix/portfolio-metrics-v2`  
**范围**: 287 files, 37,597 lines

## 1. 硬编码路径

| 问题 | 数量 | 示例 |
|------|------|------|
| `D:/trading_data` 硬编码 | **15 处** | `src/realtime/engine.py`, `src/data/stock_db.py`, `web_modern.py` |
| `print()` 调用 | **703 处** | 散落全部模块 |

**优先级**: P0 — 阻碍可移植性。下一步应全部替换为 `QuantConfig.data_dir`。

## 2. 异常处理

| 问题 | 数量 |
|------|------|
| `except Exception:` (宽泛捕获) | **92 处** |
| `except Exception: pass` (静默吞错) | 约 30 处 |

**高发区**: `engine.py` (5), `batch_runner.py` (4), `data_feed.py` (4), `optimizer.py` (4)

**优先级**: P0 — 生产环境最危险的模式。逐步替换为 `QuantAxisError` 子类。

## 3. 日志系统

| 现状 | 数量 |
|------|------|
| `print()` | 703 |
| `logging.getLogger()` | ~40 |
| `logger.info()` | ~30 |
| 使用 V2 `get_logger()` | **0** (刚创建) |

**优先级**: P1 — 需要逐步推广 V2 logger。

## 4. 配置系统

| 现状 | 数量 |
|------|------|
| 使用旧 `src/config.py` | ~25 模块 |
| 使用 V2 `QuantConfig.load()` | 0 (刚创建) |
| 直接读环境变量 | ~15 模块 (各自独立) |

**优先级**: P1 — 需要将旧 config.py 改为委托给 V2 QuantConfig。

## 5. 架构边界

| 方向 | 数量 | 结论 |
|------|------|------|
| V1→V2 导入 | 14 模块 | ✅ 正确方向, V1 正在迁移到 V2 |
| V2→V1 导入 | **0** | ✅ V2 完全独立, 无反向依赖 |

## 6. 建议处理顺序

1. **立即**: 替换 15 处硬编码路径 → `QuantConfig.data_dir`
2. **本周**: 替换高频 `except Exception: pass` → typed exceptions
3. **本周**: `src/config.py` 内部委托给 V2 `QuantConfig`
4. **本月**: `print()` → `logger.info()` (分批, 不影响功能)
