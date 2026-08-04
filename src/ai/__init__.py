"""AI 量化助手模块"""

# 启动时自动恢复持久化的 AI 挖掘因子
try:
    from src.ai.factor_persistence import factor_persistence
    _reloaded = factor_persistence.reload_into_registry(verbose=False)
    if _reloaded > 0:
        import sys
        print(f"[AI] 已恢复 {_reloaded} 个持久化因子", file=sys.stderr)
except Exception:
    pass  # 静默失败, 不影响系统启动
