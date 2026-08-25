"""组合账户：管理现金与持仓市值，支持再平衡并计入手续费、滑点与印花税。"""
import pandas as pd


class PortfolioAccount:
    """多头组合账户（权重式），按市值记账。

    - positions: {code: 市值}
    - cash: 剩余现金
    - 交易成本: 佣金(双边)+滑点(按换手)+卖出印花税
    """

    def __init__(self, init_cash=1_000_000.0, cost: dict = None):
        cost = cost or {}
        self.init_cash = float(init_cash)
        self.commission = float(cost.get("commission_rate", 0.0003))
        self.min_commission = float(cost.get("min_commission", 5.0))
        self.sell_tax = float(cost.get("sell_tax_rate", 0.001))
        self.slippage = float(cost.get("slippage_rate", 0.0005))

        self.cash = self.init_cash
        self.positions = {}  # code -> 市值
        self.date = None

        self._equity_dates = []
        self._equity = []

    # ---- 每日：按拦截 rel rates 更新持仓市值 ----
    def _total_mv(self) -> float:
        return sum(self.positions.values())

    def total(self) -> float:
        return self._total_mv() + self.cash

    def update(self, date, rates: dict):
        """按当日各持仓标的的收益率更新市值。rates: {code: rate}"""
        new_pos = {}
        for code, mv in self.positions.items():
            r = rates.get(code, 0.0)
            new_pos[code] = mv * (1 + r)
        self.positions = new_pos
        self.date = date
        self._equity_dates.append(date)
        self._equity.append(self.total())

    def _trade_cost(self, notional: float, is_sell: bool) -> float:
        fee = notional * (self.commission + self.slippage)
        fee = max(fee, self.min_commission)
        fee += notional * self.sell_tax if is_sell else 0.0
        return fee

    def rebalance(self, weights: dict):
        """调整到目标权重。weights: {code: 权重}，权重和为 <=1（其余为现金）。"""
        total = self.total()
        if total <= 0:
            self.positions = {}
            self.cash = 0
            return

        target = {c: total * w for c, w in weights.items() if w > 0}
        current = dict(self.positions)

        cost = 0.0
        # 先卖：对需减仓的标的，按减仓换手收卖出成本(佣金+滑点+印花税)
        for code, mv in current.items():
            tgt = target.get(code, 0.0)
            if mv > tgt:
                cost += self._trade_cost(mv - tgt, is_sell=True)
        # 再买：对需加仓的标的，按加仓换手收买入成本(佣金+滑点)
        for code, tgt in target.items():
            have = current.get(code, 0.0)
            if tgt > have:
                cost += self._trade_cost(tgt - have, is_sell=False)

        self.positions = target
        self.cash = max(total - sum(target.values()) - cost, 0.0)

    # ---- 结果 ----
    def results(self) -> pd.DataFrame:
        df = pd.DataFrame({"date": self._equity_dates, "value": self._equity})
        df["value"] = df["value"].astype(float)
        rate = df["value"].pct_change().fillna(0.0)
        equity = (rate + 1).cumprod()
        if len(df):
            equity.iloc[0] = 1.0
        df = pd.DataFrame({"date": df["date"], "value": df["value"],
                           "rate": rate, "equity": equity})
        df.set_index("date", inplace=True)
        return df

    def holding(self):
        return list(self.positions.keys())