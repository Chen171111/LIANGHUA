"""因子计算引擎：在面板上逐列（逐标的）计算各因子，避免跨标的串线。"""
from typing import Dict, List

import pandas as pd

from .registry import FACTOR_FUNCS

_NEED_FIELDS = {
    "rsi": ["close"],
    "macd_hist": ["close"],
    "bias20": ["close"],
    "sma_gap": ["close"],
    "natr": ["high", "low", "close"],
    "boll_pos": ["close"],
    "momentum20": ["close"],
    "vol_ratio": ["volume"],
    "zt_daily": ["close"],
    "lianban": ["close"],
}


def _field_panel(panel, name: str) -> pd.Series:
    df = panel.get(name)
    if df is None:
        raise KeyError("面板缺少字段: {}".format(name))
    return df


def compute_factors(panel, factor_names: List[str] = None) -> Dict[str, pd.DataFrame]:
    """
    计算一组因子。

    参数
    ----
    panel : Panel(date × code)
    factor_names : 需要计算的因子；None 表示全部内置因子

    返回
    ----
    {factor_name: DataFrame(date × code)}
    """
    factor_names = factor_names or list(FACTOR_FUNCS.keys())
    out = {}
    dates = panel.dates
    for name in factor_names:
        if name not in FACTOR_FUNCS:
            continue
        fn = FACTOR_FUNCS[name]
        # 组装单标的所需的原始序列(纵截取逐列)
        cols = {}
        for f in _NEED_FIELDS.get(name, ["close"]):
            cols[f] = _field_panel(panel, f)
        # 逐 code 计算
        per_code = {}
        for code in panel.codes:
            px = {f: df[code] for f, df in cols.items()}
            per_code[code] = fn(px)
        out[name] = pd.DataFrame(per_code, index=dates).sort_index()
    return out


def factor_panel(panel, factor_names: List[str] = None) -> pd.DataFrame:
    """
    将多因子堆叠为长表，便于横截面分析与可视化。

    返回 index=date, columns 为 (factor, code)。
    """
    factors = compute_factors(panel, factor_names)
    dfs = {}
    for name, df in factors.items():
        dfs[name] = df
    stacked = pd.concat({k: v for k, v in dfs.items()}, axis=1)
    return stacked