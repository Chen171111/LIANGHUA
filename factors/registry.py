"""因子注册表：支持内置技术因子与外部自定义因子。

每个因子是 callable: (close/ohlc Series | DataFrame列) -> Series
为简化，因子函数签名统一为 fn(px: pd.DataFrame, name: str) -> pd.Series，
其中 px 为整个价格面板(date×code)，返回该因子的面板某一列=全标的横截面。
实际 engine 逐列调用标量函数即可。
"""
from typing import Callable, Dict


def _make_series_fn(fn):
    """将"对单条时间序列(带close/high/low/volume)计算因子"包装成面板逐列函数。"""
    return fn


# ---- 内置单标的因子函数：输入单标的时间序列 dict, 输出 Series ----
def rsi(px: dict, period=14):
    import pandas as pd, numpy as np
    close = px["close"]
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - 100 / (1 + rs)


def macd_hist(px: dict, fast=12, slow=26, signal=9):
    close = px["close"]
    ema_f = close.ewm(span=fast, adjust=False).mean()
    ema_s = close.ewm(span=slow, adjust=False).mean()
    return ema_f - ema_s - (ema_f - ema_s).ewm(span=signal, adjust=False).mean()


def bias20(px: dict):
    close = px["close"]
    ma = close.rolling(20).mean()
    return (close - ma) / ma


def sma_gap(px: dict, fast=5, slow=20):
    close = px["close"]
    return (close.rolling(fast).mean() - close.rolling(slow).mean()) / close.rolling(
        slow).mean()


def natr(px: dict, period=14):
    h, l, c = px["high"], px["low"], px["close"]
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(
        axis=1)
    return tr.rolling(period).mean() / c * 100


def boll_pos(px: dict, period=20, n=2):
    close = px["close"]
    ma = close.rolling(period).mean()
    std = close.rolling(period).std()
    upper, lower = ma + n * std, ma - n * std
    return (close - lower) / (upper - lower)


def momentum(px: dict, window=20):
    close = px["close"]
    return close / close.shift(window) - 1


def vol_ratio(px: dict, window=5):
    v = px["volume"]
    return v / v.rolling(window).mean()


def zt_daily(px: dict, thr: float = 0.098):
    """当日是否涨停（近似：较前收盘涨幅 ≥ 阈值）。"""
    return (px["close"].pct_change() >= thr).astype(int)


def lianban(px: dict, thr: float = 0.098):
    """连板数（连续涨停计数，涨停则累加，断板归 0）。"""
    zt = zt_daily(px, thr)
    run = zt.cumsum() - zt.cumsum().where(zt == 0).ffill().fillna(0)
    return run.where(zt > 0, 0)


# ---- 注册表 ----
FACTOR_FUNCS: Dict[str, Callable] = {
    "rsi": lambda px: rsi(px),
    "macd_hist": lambda px: macd_hist(px),
    "bias20": lambda px: bias20(px),
    "sma_gap": lambda px: sma_gap(px),
    "natr": lambda px: natr(px),
    "boll_pos": lambda px: boll_pos(px),
    "momentum20": lambda px: momentum(px, 20),
    "vol_ratio": lambda px: vol_ratio(px),
    "zt_daily": lambda px: zt_daily(px),
    "lianban": lambda px: lianban(px),
}


def register_factor(name: str, fn: Callable) -> None:
    """注册自定义因子。fn(px: dict) -> Series，px 含 close/open/high/low/volume。"""
    FACTOR_FUNCS[name] = fn


def list_factors() -> list:
    return list(FACTOR_FUNCS.keys())