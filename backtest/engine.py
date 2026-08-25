"""回测引擎：在面板上逐日推进，调用策略产出目标权重并再平衡。"""
from typing import Callable, Dict, Optional

import pandas as pd

from .account import PortfolioAccount


class BacktestResult:
    """回测结果容器：净值、持仓历史、成交记录。"""

    def __init__(self, equity: pd.DataFrame, holdings: Dict[str, list],
                 benchmark: Optional[pd.Series] = None):
        self.equity = equity          # index=date, 列 value/rate/equity
        self.holdings = holdings      # {date: [codes]}
        self.benchmark = benchmark    # Series(index=date, value=基准净值)

    def to_dict(self) -> dict:
        eq = self.equity.reset_index()
        payload = {
            "dates": eq["date"].astype(str).tolist(),
            "value": eq["value"].round(2).tolist(),
            "equity": eq["equity"].round(6).tolist(),
            "rate": eq["rate"].round(6).tolist(),
        }
        if self.benchmark is not None:
            payload["benchmark"] = self.benchmark.round(6).tolist()
        hold = [{"date": str(d), "codes": c} for d, c in self.holdings.items()]
        payload["holdings"] = hold
        return payload


class BacktestEngine:
    """权重轮动回测引擎。

    策略契约: strategy.generate_weights(date, factor_snapshots) -> {code: weight}
    其中 factor_snapshots 为 dict {factor_name: Series(index=code)}。
    """

    def __init__(self, panel, factors: Dict[str, pd.DataFrame],
                 strategy, cost: dict = None, init_cash=1_000_000.0,
                 benchmark=None, benchmark_yoy=0.0):
        self.panel = panel
        self.factors = factors
        self.strategy = strategy
        self.acc = PortfolioAccount(init_cash, cost or {})
        self.benchmark = benchmark    # Series(date→close) 基准收盘
        self.benchmark_yoy = benchmark_yoy

    def run(self) -> BacktestResult:
        dates = self.panel.dates
        close = self.panel.get("close")
        rate = self.panel.get("rate")
        bench_nav = None
        if self.benchmark is not None:
            bc = self.benchmark
            b0 = bc.loc[dates].dropna()
            bench_nav = (b0 / b0.iloc[0])

        holdings = {}
        for i, date in enumerate(dates):
            # 1) 按 rate 更新账户市值（NaN 视为 0 收益）
            rates_series = rate.loc[date] if date in rate.index else pd.Series(
                0.0, index=self.panel.codes)
            rates = {c: (r if r == r else 0.0) for c, r in rates_series.items()}
            self.acc.update(date, rates)

            # 2) 生成信号并再平衡
            weights = self.strategy.generate_weights(date, self.factors, self.panel)
            if weights is not None and weights:
                self.acc.rebalance(weights)

            holdings[date] = self.acc.holding()

        return BacktestResult(self.acc.results(), holdings, bench_nav)


# 供 CLI/分析复用：把权重生成器包装为策略对象
class StrategyAdapter:
    """将策略函数适配为策略对象。"""

    def __init__(self, fn: Callable):
        self.fn = fn

    def generate_weights(self, date, factors, panel):
        return self.fn(date, factors, panel)