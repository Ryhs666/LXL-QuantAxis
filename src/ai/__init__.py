"""AI 量化助手模块 — LLM-powered research assistants."""

from src.ai.engine import LLMClient, llm
from src.ai.assistants import (
    AITradeReviewer,
    AIStrategyAdvisor,
    AIMarketAnalyst,
    AIChat,
    setup_ai_config,
)

# Backward-compatible aliases
TradeReviewCoach = AITradeReviewer
StrategyAdvisor = AIStrategyAdvisor
MarketAnalyst = AIMarketAnalyst

__all__ = [
    "LLMClient",
    "llm",
    "AITradeReviewer",
    "AIStrategyAdvisor",
    "AIMarketAnalyst",
    "AIChat",
    "setup_ai_config",
    # Aliases
    "TradeReviewCoach",
    "StrategyAdvisor",
    "MarketAnalyst",
]
