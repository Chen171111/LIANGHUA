"""模拟券商：内存记账，供模拟交易与自动化测试。"""
from .broker import Broker, Balance, Position


class MockBroker(Broker):
    """零成本/按给定价格的模拟成交，用于把调仓信号做模拟撮合。"""

    def __init__(self, init_cash=1_000_000.0):
        self.cash = float(init_cash)
        self.positions = {}  # code -> {amount, avg_cost}
        self.orders = []

    def _price(self, price, default):
        return price if price and price > 0 else default

    def buy(self, code, price=0.0, amount=0, volume=0, entrust_prop="limit"):
        px = self._price(price, 10.0)
        amt = amount or volume
        cost = px * amt
        self.cash -= cost
        pos = self.positions.setdefault(
            code, {"amount": 0, "avg_cost": 0.0})
        old = pos["avg_cost"]
        new_amount = pos["amount"] + amt
        pos["avg_cost"] = (old * pos["amount"] + cost) / max(new_amount, 1)
        pos["amount"] = new_amount
        self.orders.append({"code": code, "direction": "buy",
                            "price": px, "amount": amt})
        return True

    def sell(self, code, price=0.0, amount=0, volume=0, entrust_prop="limit"):
        if code not in self.positions:
            return False
        px = self._price(price, 10.0)
        amt = amount or volume
        pos = self.positions[code]
        amt = min(amt, pos["amount"])
        self.cash += px * amt
        pos["amount"] -= amt
        if pos["amount"] <= 0:
            del self.positions[code]
        self.orders.append({"code": code, "direction": "sell",
                            "price": px, "amount": amt})
        return True

    def get_balance(self) -> Balance:
        mv = sum(p["amount"] * p["avg_cost"] for p in self.positions.values())
        return Balance(total_asset=self.cash + mv, cash=self.cash, market_value=mv,
                       available=self.cash)

    def get_position(self):
        return [Position(code=c, price=p["avg_cost"], amount=p["amount"],
                         available=p["amount"], value=p["amount"] * p["avg_cost"])
                for c, p in self.positions.items()]