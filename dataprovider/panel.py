"""Panel：将多标的标准行情构建成横截面面板(date × code)，供回测引擎直接使用。"""
from typing import Dict, List, Optional

import pandas as pd

from .store import DataStore, classify_code

_OCCL_FIELDS = ["open", "high", "low", "close", "volume", "rate"]


class Panel:
    """多标的面板容器。

    每个字段一张宽表：index=date(YYYYMMDD, 排序), columns=code。
    dates 仅含所有标的同时有数据的公共交易日。
    """

    def __init__(self, fields: Dict[str, pd.DataFrame], codes, categories):
        self.fields = fields
        self.codes = list(codes)
        self.categories = categories  # {code: 'index'|'stock'}

    def get(self, field: str) -> Optional[pd.DataFrame]:
        return self.fields.get(field)

    @property
    def dates(self) -> List[str]:
        return list(self.fields["close"].index)

    def __len__(self):
        return len(self.codes)


def build_panel(
    store: DataStore,
    codes,
    start=None,
    end=None,
    fields: List[str] = None,
    align="close",
) -> Panel:
    """
    构建面板。

    参数
    ----
    store : DataStore
    codes : 标的代码列表（指数/个股均可）
    start, end : 日期 YYYYMMDD，区间过滤
    fields : 保留字段，默认 OHLCV+rate
    align : 对齐方式，'close' 表示按所有标的最长? 否则全字段无NA对齐
    """
    fields = fields or _OCCL_FIELDS

    # 逐标的加载
    frames = {}
    for code in codes:
        df = store.read(code, start=start, end=end)
        frames[code] = df

    # 以 close 为锚对齐公共交易日（所有标的那天都有 close）
    anchor = pd.DataFrame({c: f["close"] for c, f in frames.items()})
    anchor = anchor.dropna().sort_index()
    common_dates = anchor.index

    tables = {}
    for f in fields:
        t = pd.DataFrame({c: frames[c][f] for c in codes if f in frames[c].columns})
        if t.empty:
            continue
        t = t.loc[common_dates]        # 只保留公共交易日
        t = t.apply(pd.to_numeric, errors="coerce")
        tables[f] = t

    categories = {c: classify_code(c) for c in codes}
    return Panel(tables, codes, categories)