"""内置策略：动量、均值回归、双均线、多因子。"""
import pandas as pd

from .base import Strategy, weighted_score, rank_snapshot


class MomentumStrategy(Strategy):
    """动量轮动：按近 N 日收益率排名，取 TopK 等权持有。"""
    name = "momentum"

    def __init__(self, topk=3, window=20, **kw):
        super().__init__(topk=topk, **kw)
        self.window = window
        self.factor = "momentum{}".format(window) if window != 20 else "momentum20"

    def generate_weights(self, date, factors, panel):
        if not self._is_rebalance():
            return None
        s = self._snapshot(factors, date, self.factor)
        if s is None or s.empty:
            return {}
        scores = rank_snapshot(s, ascending=False)
        codes = scores.sort_values(ascending=False).head(self.topk).index
        return {c: min(1.0 / max(len(codes), 1) * 0.9, self.max_total) for c in codes}


class MeanReversionStrategy(Strategy):
    """均值回归：乖离率越低(超卖)越看好，取 TopK。"""
    name = "mean_reversion"

    def __init__(self, topk=3, factor="bias20", **kw):
        super().__init__(topk=topk, **kw)
        self.factor = factor

    def generate_weights(self, date, factors, panel):
        if not self._is_rebalance():
            return None
        s = self._snapshot(factors, date, self.factor)
        if s is None or s.empty:
            return {}
        scores = rank_snapshot(s, ascending=True)  # 越小越好
        codes = scores.sort_values(ascending=False).head(self.topk).index
        return {c: min(1.0 / max(len(codes), 1) * 0.9, self.max_total) for c in codes}


class CrossMovingStrategy(Strategy):
    """双均线趋势：短均线与长均线差(sma_gap)越强越看好(顺势)。"""
    name = "cross_moving"

    def __init__(self, topk=3, factor="sma_gap", **kw):
        super().__init__(topk=topk, **kw)
        self.factor = factor

    def generate_weights(self, date, factors, panel):
        if not self._is_rebalance():
            return None
        s = self._snapshot(factors, date, self.factor)
        if s is None or s.empty:
            return {}
        scores = rank_snapshot(s, ascending=False)
        codes = scores.sort_values(ascending=False).head(self.topk).index
        return {c: min(1.0 / max(len(codes), 1) * 0.9, self.max_total) for c in codes}


class MultiFactorStrategy(Strategy):
    """多因子打分：加权横截面得分取 TopK（方向×权重可配置）。"""
    name = "multifactor"

    DEFAULT_SPECS = [
        ("momentum20", 1, 1.0),   # 动量越大越好
        ("sma_gap", 1, 1.0),      # 趋势强度
        ("macd_hist", 1, 1.0),    # MACD 动能
        ("bias20", -1, 0.5),      # 乖离不宜过高
    ]

    def __init__(self, topk=3, specs=None, **kw):
        super().__init__(topk=topk, **kw)
        self.specs = specs or list(self.DEFAULT_SPECS)

    def generate_weights(self, date, factors, panel):
        if not self._is_rebalance():
            return None
        score = weighted_score(factors, date, self.specs)
        if score is None or score.empty:
            return {}
        codes = score.sort_values(ascending=False).head(self.topk).index
        w = min(1.0 / max(len(codes), 1) * 0.9, self.max_total)
        return {c: w for c in codes}