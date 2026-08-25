"""回测引擎：在面板上逐日推进，调用策略产出目标权重并再平衡。"""
from typing import Callable, Dict, Optional

import numpy as np
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
                 benchmark=None, benchmark_yoy=0.0,
                 timing=None, timing_window=20, timing_scale_off=0.3,
                 benchmark_high=None, benchmark_low=None):
        self.panel = panel
        self.factors = factors
        self.strategy = strategy
        self.acc = PortfolioAccount(init_cash, cost or {})
        self.benchmark = benchmark    # Series(date→close) 基准收盘
        self.benchmark_yoy = benchmark_yoy
        # 大盘择时：None 关闭；"ma20"/"abs_mom"/"rsrs"（RSRS 需基准高低价）
        self.timing = timing
        self.timing_window = timing_window
        self.timing_scale_off = timing_scale_off
        self._timing_ma = None
        self._timing_mom = None
        self._timing_rsrs = None
        if timing and benchmark is not None and len(benchmark) > timing_window:
            bc = benchmark.dropna()
            if timing == "ma20":
                self._timing_ma = bc.rolling(timing_window).mean()
            elif timing == "abs_mom":
                self._timing_mom = bc / bc.shift(timing_window) - 1
            elif timing == "rsrs":
                self._timing_rsrs = self._build_rsrs(
                    benchmark, benchmark_high, benchmark_low, timing_window)

    def _build_rsrs(self, close, high, low, window):
        """构建 RSRS 标准分（光大经典）：N日高低价 OLS 斜率 → z-score。"""
        if high is None or low is None:
            return None
        bh = high.dropna()
        bl = low.dropna()
        if len(bh) < window + 2:
            return None
        hi = bh.values
        lo = bl.values
        N = max(5, min(window, len(bh) - 2))
        beta = [np.nan] * len(bh)
        for i in range(N, len(bh)):
            beta[i] = np.polyfit(lo[i - N: i], hi[i - N: i], 1)[0]
        alpha = pd.Series(beta, index=bh.index)
        M = max(N * 2, 20)
        z = (alpha - alpha.rolling(M).mean()) / alpha.rolling(M).std()
        return z

    def _timing_scale(self, date) -> float:
        """大盘择时仓位系数：满仓 1.0；弱势按 timing_scale_off 减仓。"""
        if (self._timing_ma is None and self._timing_mom is None
                and self._timing_rsrs is None):
            return 1.0
        if self._timing_rsrs is not None:
            z = self._timing_rsrs.get(date)
            if z is None or z != z:
                return 1.0
            # RSRS 标准分 > 0 视为趋势健康，满仓；否则减仓
            return 1.0 if z > 0 else self.timing_scale_off
        if self._timing_ma is not None:
            c = self._timing_ma.get(date)
            if c is None or c != c:      # 无数据/NA 不择时
                return 1.0
            return 1.0 if self.benchmark.get(date, 0) > c else self.timing_scale_off
        if self._timing_mom is not None:
            c = self._timing_mom.get(date)
            if c is None or c != c:
                return 1.0
            return 1.0 if c > 0 else self.timing_scale_off
        return 1.0

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

            # 2) 生成信号并再平衡（叠加可选的大盘择时仓位）
            weights = self.strategy.generate_weights(date, self.factors, self.panel)
            if weights is not None and weights:
                scale = self._timing_scale(date)
                if scale < 1.0:
                    weights = {c: w * scale for c, w in weights.items()}
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