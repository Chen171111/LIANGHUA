"""平台统一配置。"""
import os
from pathlib import Path


def _pkg_dir() -> Path:
    return Path(__file__).resolve().parent


def _project_root() -> Path:
    # quantplatform 位于 pytrader 下
    return _pkg_dir().parent.parent


class PlatformConfig:
    """全局路径与数据目录配置。"""

    def __init__(self, root: Path = None):
        self.root = Path(root) if root else _project_root()
        # 数据缓存根目录：<root>/pytrader/data
        self.data_dir = self.root / "pytrader" / "data"
        self.index_dir = self.data_dir / "indexes"
        self.stock_dir = self.data_dir / "stocks"
        # 结果输出目录
        self.results_dir = self._pkg_rel("results")
        # Dashboard /
        self.dashboard_dir = self._pkg_rel("dashboard")

    def _pkg_rel(self, name: str) -> Path:
        p = _pkg_dir() / name
        p.mkdir(parents=True, exist_ok=True)
        return p

    def ensure_dirs(self):
        for d in (self.index_dir, self.stock_dir):
            d.mkdir(parents=True, exist_ok=True)
        return self

    def cache_dir_for(self, kind: str) -> Path:
        return self.index_dir if kind == "index" else self.stock_dir


# 默认回测参数（手续费/滑点等，按沪深 A 股典型水平）
def backtest_config(
    init_cash: float = 1_000_000.0,
    commission_rate: float = 0.0003,
    min_commission: float = 5.0,
    sell_tax_rate: float = 0.001,      # 印花税(卖出)
    slippage_rate: float = 0.0005,     # 单边滑点比例
    price_field: str = "close",        # 成交价基准列
) -> dict:
    """
    生成标准回测交易成本参数。

    参数
    ----
    init_cash      : 初始资金
    commission_rate: 券商佣金比例(双边) 万3
    min_commission : 单笔最低佣金
    sell_tax_rate  : 卖出印花税 0.1%
    slippage_rate  : 滑点比例，模拟成交价偏移(卖=基准*(1-滑点)，买=基准*(1+滑点))
    """
    return {
        "init_cash": float(init_cash),
        "commission_rate": float(commission_rate),
        "min_commission": float(min_commission),
        "sell_tax_rate": float(sell_tax_rate),
        "slippage_rate": float(slippage_rate),
        "price_field": price_field,
    }


DEFAULT_CONFIG = PlatformConfig()