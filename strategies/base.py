"""策略基类与横截面排名工具。"""
import abc

import pandas as pd


class Strategy(abc.ABC):
    """策略抽象基类。

    子类实现 generate_weights(date, factors, panel) -> {code: weight}。
    - date   : str YYYYMMDD
    - factors: {factor_name: DataFrame(date×code)}
    - panel  : Panel，可访问原始 OHLCV
    """

    name = "base"

    def __init__(self, topk: int = 3, rebalance_every: int = 5, max_weight: float = 0.30,
                 max_total: float = 0.90, **kwargs):
        self.topk = topk
        self.rebalance_every = rebalance_every  # 调仓周期(交易日)
        self.max_weight = max_weight
        self.max_total = max_total
        self._since = 0

    @abc.abstractmethod
    def generate_weights(self, date, factors, panel):
        raise NotImplementedError

    # 供子类：判断是否调仓日
    def _is_rebalance(self) -> bool:
        self._since += 1
        if self._since % self.rebalance_every == 0:
            return True
        return False

    def _snapshot(self, factors, date, factor_name):
        """取某因子在指定日的横截面 Series(index=code)。"""
        df = factors.get(factor_name)
        if df is None or date not in df.index:
            return None
        s = df.loc[date]
        return s.dropna()


def rank_snapshot(series: pd.Series, ascending: bool = False) -> pd.Series:
    """横截面排名归一化到 [0,1]。ascending=True 表示因子越小越好。"""
    r = series.rank(pct=True)
    return (1 - r) if ascending else r


def weighted_score(factors, date, factor_specs) -> pd.Series:
    """
    对一组因子的当日横截面做加权综合打分。

    参数
    ----
    factor_specs : list[(factor_name, direction, weight)]
        direction=1 越大越好，=-1 越小越好
    返回 Series(index=code, value=综合分)。
    """
    score = None
    tw = 0.0
    for fname, direction, w in factor_specs:
        s = factors.get(fname)
        if s is None or date not in s.index:
            continue
        sr = rank_snapshot(s.loc[date].dropna(), ascending=(direction < 0))
        score = sr.mul(w).copy() if score is None else score.add(sr.mul(w), fill_value=0.0)
        tw += w
    if score is None or tw <= 0:
        return pd.Series(dtype=float)
    return score / tw