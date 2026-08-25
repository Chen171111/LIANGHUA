"""绩效分析：多周期评定，含年化收益、夏普、索提诺、最大回撤、Calmar、换手等。

输入: 净值 DataFrame(列为各组合/基准)，index=日期。
"""
import numpy as np
import pandas as pd

TRADING_DAYS = 252


def _eq2ret(eq: pd.Series) -> pd.Series:
    return eq.pct_change().dropna()


class PerformanceMetrics:
    def __init__(self, equity: pd.Series, rf=0.0):
        self.equity = equity.dropna()
        self.ret = _eq2ret(self.equity)
        self.rf = rf
        self.n = len(self.ret)

    def _annualize(self) -> float:
        if self.n < 2:
            return 0.0
        total = self.equity.iloc[-1] / self.equity.iloc[0] - 1
        return (1 + total) ** (TRADING_DAYS / max(self.n - 1, 1)) - 1

    def metrics(self) -> dict:
        ann = self._annualize()
        vol = self.ret.std() * np.sqrt(TRADING_DAYS)
        sharpe = ann / vol if vol > 0 else 0.0
        downside = self.ret[self.ret < 0].std() * np.sqrt(TRADING_DAYS)
        sortino = ann / downside if downside > 0 else 0.0
        # 最大回撤
        roll_max = self.equity.cummax()
        mdd = ((self.equity / roll_max) - 1).min() if len(self.equity) else 0.0
        calmar = ann / abs(mdd) if mdd < 0 else 0.0
        # 胜率 & 盈亏比
        wins = self.ret > 0
        win_rate = wins.mean() if len(self.ret) else 0.0
        avg_win = self.ret[wins].mean() if wins.any() else 0.0
        avg_loss = self.ret[~wins].mean() if (~wins).any() else 0.0
        profit_loss = abs(avg_win / avg_loss) if avg_loss != 0 else 0.0
        total_ret = self.equity.iloc[-1] / self.equity.iloc[0] - 1 if len(self.equity) else 0.0
        return {
            "累计收益": float(round(total_ret, 4)),
            "年化收益": float(round(ann, 4)),
            "年化波动率": float(round(vol, 4)),
            "夏普比率": float(round(sharpe, 3)),
            "索提诺比率": float(round(sortino, 3)),
            "最大回撤": float(round(mdd, 4)),
            "Calmar": float(round(calmar, 3)),
            "胜率": float(round(win_rate, 3)),
            "盈亏比": float(round(profit_loss, 3)),
            "交易日数": int(self.n),
        }


def compute_metrics(equities: pd.DataFrame, rf=0.0) -> pd.DataFrame:
    """对净值 DataFrame 的每列计算绩效，返回指标表(index=指标, columns=组合)。"""
    rows = {}
    for col in equities.columns:
        m = PerformanceMetrics(equities[col], rf)
        rows[col] = m.metrics()
    df = pd.DataFrame(rows)
    # 统一转字符串避免 float4 语法保护
    df = df.infer_objects()
    return df