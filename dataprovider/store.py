"""DataStore：指数/个股行情数据的下载、缓存与读取。

数据源统一走 akshare（免费、无需 token）：
    - 指数：新浪接口 stock_zh_index_daily
    - 个股：东财接口 stock_zh_a_hist，前复权(qfq)消除除权跳档
    - 数据缓存为本地 csv，二次读取离线复用
"""
import os
from pathlib import Path

import pandas as pd

# 已知指数白名单：Qbot 指数代码 -> akshare symbol
_AK_SYMBOL_MAP = {
    "000300.SH": "sh000300",  # 沪深300
    "000905.SH": "sh000905",  # 中证500
    "000852.SH": "sh000852",  # 中证1000
    "000016.SH": "sh000016",  # 上证50
    "000688.SH": "sh000688",  # 科创50
    "000922.SH": "sh000922",  # 中证红利
    "399006.SZ": "sz399006",  # 创业板指
    "399324.SZ": "sz399324",  # 深证红利
    "399997.SZ": "sz399997",  # 中证白酒
    "399989.SZ": "sz399989",  # 中证医疗
    "399967.SZ": "sz399967",  # 中证军工
    "399986.SZ": "sz399986",  # 中证银行
    "399808.SZ": "sz399808",  # 中证新能源
    "399673.SZ": "sz399673",  # 创业板50
    "399005.SZ": "sz399005",  # 中小100
    "399975.SZ": "sz399975",  # 中证全指证券公司
}

_OCCL = {"vol": "volume", "日期": "date", "开盘": "open", "最高": "high",
         "最低": "low", "收盘": "close", "成交量": "volume"}


def classify_code(code: str) -> str:
    """返回 'index' 或 'stock'，按市场标识 + 代码段位识别。"""
    code_up = code.upper()
    if code_up in _AK_SYMBOL_MAP:
        return "index"
    parts = code_up.split(".")
    base, market = parts[0], (parts[1] if len(parts) > 1 else None)
    if market == "SH":
        return "index" if base.startswith(("000", "899")) else "stock"
    if market == "SZ":
        return "index" if base.startswith("399") else "stock"
    return "stock" if base.isdigit() and len(base) == 6 else "index"


def to_ak_symbol(code: str) -> str:
    """指数代码 -> akshare symbol（优先用交易所后缀判定，规避段位歧义）。"""
    code_up = code.upper()
    if code_up in _AK_SYMBOL_MAP:
        return _AK_SYMBOL_MAP[code_up]
    parts = code_up.split(".")
    base, market = parts[0], (parts[1] if len(parts) > 1 else None)
    if market == "SH":
        market_pfx = "sh"
    elif market == "SZ":
        market_pfx = "sz"
    else:
        market_pfx = "sh" if base.startswith(("6", "5", "9", "11", "13", "688", "000")) else "sz"
    return "{}{}".format(market_pfx, base)


# ===== 推荐标的池（高分化，横截面/轮动空间更大） =====
RECOMMENDED_POOLS = {
    # 宽基 + 风格
    "宽基成长": ["000300.SH", "000905.SH", "000852.SH", "000688.SH", "399006.SZ",
                 "399673.SZ", "399005.SZ"],
    # 行业主题（趋势分化大，适合行业轮动）
    "行业轮动": ["399997.SZ", "399989.SZ", "399967.SZ", "399986.SZ",
                 "399808.SZ", "000688.SH", "399673.SZ", "399975.SZ"],
    # 默认温和
    "default": ["000300.SH", "000905.SH", "399006.SZ", "399324.SZ"],
}

# 动态生成型池：值为 (生成函数名, 参数)
_DYNAMIC_POOLS = {"个股动量": ("index_stock_cons_sample", 20)}


def _z6(c) -> str:
    return str(c).zfill(6)


def fetch_index_cons_sample(index_code: str = "000300", n: int = 20) -> list:
    """拉取指数成分股并等距抽样生成个股池（用于横截面个股动量等策略）。"""
    import akshare as ak
    symbol = index_code.split(".")[0]
    cons = ak.index_stock_cons_csindex(symbol=symbol)
    raw = list(cons["成分券代码"])
    step = max(1, len(raw) // max(n, 1))
    sel = raw[::step][:max(n, 1)]
    out = []
    for c in sel:
        c6 = _z6(c)
        suffix = ".SH" if c6.startswith(("6", "9", "68")) else ".SZ"
        out.append(c6 + suffix)
    return out


def _normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    """统一为 date/open/high/low/close/volume 标准列。"""
    df = df.rename(columns=_OCCL)
    if "date" not in df.columns:
        raise ValueError("数据缺少 date 列: {}".format(list(df.columns)))
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y%m%d")
    df = df[[c for c in ["date", "open", "high", "low", "close", "volume"]
             if c in df.columns]]
    df.sort_values("date", inplace=True)
    return df.reset_index(drop=True)


def _download_one(ak, code: str, kind: str) -> pd.DataFrame:
    """下载单个标的行情。

    个股优先东财前复权(qfq)，若接口被限流/风控断连则自动回退到新浪(不复权)。
    """
    if kind == "index":
        df = ak.stock_zh_index_daily(symbol=to_ak_symbol(code))
        if df is None or df.empty:
            raise RuntimeError("{} 无数据返回".format(code))
        return _normalize_ohlcv(df)

    base = code.split(".")[0]
    # 1) 东财前复权
    for adj in ("qfq", ""):
        try:
            df = ak.stock_zh_a_hist(symbol=base, period="daily",
                                    start_date="19900101", end_date="22240101",
                                    adjust=adj)
            if df is not None and not df.empty:
                return _normalize_ohlcv(df)
        except Exception:
            continue  # 东财不可用，尝试下一个
    # 2) 新浪（不复权）兜底
    try:
        df = ak.stock_zh_a_daily(symbol=to_ak_symbol(code),
                                 start_date="19900101", end_date="22240101")
        if df is not None and not df.empty:
            print("[DataStore] {} 使用新浪数据源(不复权)".format(code))
            return _normalize_ohlcv(df)
    except Exception as e:
        raise RuntimeError("{} 数据下载失败: {}".format(code, e)) from e
    raise RuntimeError("{} 无数据".format(code))


class DataStore:
    """行情数据仓库（下载 + 缓存 + 读取）。"""

    def __init__(self, index_dir=None, stock_dir=None, force_download=False):
        self.index_dir = Path(index_dir) if index_dir else Path("data/indexes")
        self.stock_dir = Path(stock_dir) if stock_dir else Path("data/stocks")
        self.force_download = force_download
        self._cache = {}  # code -> DataFrame(单标的OHLCV+rate)，进程内缓存

    def dir_for(self, kind: str) -> Path:
        return self.index_dir if kind == "index" else self.stock_dir

    def path_for(self, code: str) -> Path:
        return self.dir_for(classify_code(code)) / (code + ".csv")

    def ensure(self, codes):
        """确保数据在本地；缺失则下载。返回缺失/新增列表。"""
        try:
            import akshare as ak
        except ImportError as e:
            raise ImportError("请先安装 akshare: pip install akshare") from e
        added = []
        for code in codes:
            self.dir_for(classify_code(code)).mkdir(parents=True, exist_ok=True)
            p = self.path_for(code)
            if p.exists() and not self.force_download:
                continue
            try:
                df = _download_one(ak, code, classify_code(code))
                df.to_csv(p, index=False)
                added.append(code)
                print("[DataStore] 已下载 {} 条 -> {}".format(len(df), code))
            except Exception as e:  # 单条失败不中断
                print("[DataStore] 下载失败 {}: {}".format(code, e))
        return added

    def read(self, code: str, start=None, end=None):
        """读取单个标的标准行情 DataFrame(index=YYYYMMDD, 含 rate)。"""
        if code in self._cache:
            df = self._cache[code].copy()
        else:
            p = self.path_for(code)
            if not p.exists() and not self.force_download:
                self.ensure([code])
            if not p.exists():
                raise FileNotFoundError(p)
            df = pd.read_csv(p)
            df["date"] = df["date"].astype(str)
            df.index = df["date"]
            df.sort_index(inplace=True)
            df["rate"] = df["close"].pct_change()
            self._cache[code] = df.copy()
        if start:
            df = df[df.index >= str(start)]
        if end:
            df = df[df.index <= str(end)]
        return df

    def file_path(self, code: str) -> str:
        return str(self.path_for(code))