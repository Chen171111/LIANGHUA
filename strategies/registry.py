"""策略注册表：按名称创建/列出策略，支持外部注册自定义策略。"""
from .base import Strategy
from .builtin import (MomentumStrategy, MeanReversionStrategy, CrossMovingStrategy,
                      MultiFactorStrategy, LianbanLeadStrategy)

STRATEGIES = {
    "momentum": MomentumStrategy,
    "mean_reversion": MeanReversionStrategy,
    "cross_moving": CrossMovingStrategy,
    "multifactor": MultiFactorStrategy,
    "lianban_lead": LianbanLeadStrategy,
}


def register_strategy(name: str, cls):
    """注册自定义策略类（继承 Strategy）。"""
    STRATEGIES[name] = cls


def list_strategies() -> list:
    return list(STRATEGIES.keys())


def create_strategy(name: str, **params) -> Strategy:
    """按名称创建策略实例。"""
    if name not in STRATEGIES:
        raise KeyError("未知策略: {}，可用: {}".format(name, list_strategies()))
    return STRATEGIES[name](**params)