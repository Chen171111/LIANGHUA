"""回测流水线：数据→因子→策略→回测→绩效→报告，供 CLI 与 API 复用。"""
from typing import List, Optional

from .config import backtest_config, DEFAULT_CONFIG
from .dataprovider.store import DataStore
from .dataprovider.panel import build_panel
from .factors.engine import compute_factors
from .strategies.registry import create_strategy
from .backtest.engine import BacktestEngine
from .analysis.report import run_report, render_dashboard

DEFAULT_FACTORS = ["rsi", "macd_hist", "bias20", "sma_gap", "momentum20", "vol_ratio"]


def run_backtest(
    codes: List[str],
    strategy: str = "multifactor",
    start: Optional[str] = None,
    end: Optional[str] = None,
    init_cash: float = 1_000_000.0,
    cost: Optional[dict] = None,
    strategy_params: Optional[dict] = None,
    benchmark: Optional[str] = None,
    data_root=None,
) -> dict:
    """
    一键回测：数据下载/缓存 → 构建面板 → 计算因子 → 策略 → 回测 → 绩效 → 报告。

    参数
    ----
    codes          : 标的代码（指数/个股混合）
    strategy       : 策略名（momentum/mean_reversion/cross_moving/multifactor）
    start, end     : YYYYMMDD 区间
    init_cash      : 初始资金
    cost           : 交易成本参数，见 backtest_config()
    benchmark      : 基准代码（默认取 codes[0]）
    data_root      : 数据根目录，默认平台内置目录

    返回
    ----
    dict: {result(BacktestResult), metrics, equity, html, meta}
    """
    cost = cost or backtest_config(init_cash=init_cash)
    store = DataStore(
        index_dir=str(DEFAULT_CONFIG.index_dir) if data_root is None else str(data_root / "indexes"),
        stock_dir=str(DEFAULT_CONFIG.stock_dir) if data_root is None else str(data_root / "stocks"),
    )
    store.ensure(codes)

    # 面板（以公共交易日为准，过滤 NaN）
    panel = build_panel(store, codes, start=start, end=end)
    if len(panel.dates) < 30:
        raise ValueError("有效交易日过少，请检查标的代码或区间（{} 天）".format(len(panel.dates)))

    # 因子
    factors = compute_factors(panel, DEFAULT_FACTORS)

    # 策略
    kw = dict(strategy_params or {})
    strat = create_strategy(strategy, **kw)

    # 基准
    bench_code = benchmark or codes[0]
    bench_df = store.read(bench_code, start=start, end=end)
    bench_close = bench_df["close"].reindex(panel.dates)

    engine = BacktestEngine(
        panel, factors, strat, cost=cost, init_cash=init_cash,
        benchmark=bench_close,
    )
    result = engine.run()

    rep = run_report(result, benchmark_nav=result.benchmark)
    html = render_dashboard(
        result, rep["metrics"],
        title="{} 策略回测（{}）".format(strategy, ", ".join(str(c) for c in codes)),
        subtitle="{} ~ {}".format(panel.dates[0], panel.dates[-1]),
    )
    return {
        "result": result,
        "metrics": rep["metrics"],
        "equity": rep["equity"],
        "html": html,
        "meta": {
            "strategy": strategy,
            "codes": codes,
            "start": panel.dates[0],
            "end": panel.dates[-1],
            "factors": DEFAULT_FACTORS,
        },
    }