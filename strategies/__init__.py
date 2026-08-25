"""多策略引擎：策略接口、注册表与内置策略。"""
from .base import Strategy
from .builtin import MomentumStrategy, MeanReversionStrategy, CrossMovingStrategy, MultiFactorStrategy
from .registry import STRATEGIES, register_strategy, create_strategy, list_strategies

__all__ = ["Strategy", "MomentumStrategy", "MeanReversionStrategy",
           "CrossMovingStrategy", "MultiFactorStrategy",
           "STRATEGIES", "register_strategy", "create_strategy", "list_strategies"]