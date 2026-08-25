"""券商交易接口抽象。

设计目的：让策略/回测的调仓信号可以映射到真实交易通道，
为对接 easytrader、vnpy 或自有券商 API 预留统一接口。
"""
import abc
from dataclasses import dataclass, field


@dataclass
class Order:
    code: str
    direction: str          # buy / sell
    price: float = 0.0
    amount: int = 0         # 股数
    volume: int = 0
    entrust_prop: str = "limit"

    def to_dict(self):
        return asdict_filtered(self)


def asdict_filtered(order) -> dict:
    d = {
        "code": order.code,
        "direction": order.direction,
        "price": order.price,
        "amount": order.amount,
        "volume": order.volume,
    }
    return d


@dataclass
class Balance:
    total_asset: float
    cash: float
    market_value: float
    available: float = 0.0


@dataclass
class Position:
    code: str
    price: float = 0.0
    amount: int = 0
    available: int = 0
    value: float = 0.0


class Broker(abc.ABC):
    """券商抽象基类：买卖、查询资金、持仓、委托。"""

    @abc.abstractmethod
    def buy(self, code, price=0.0, amount=0, volume=0, entrust_prop="limit"):
        raise NotImplementedError

    @abc.abstractmethod
    def sell(self, code, price=0.0, amount=0, volume=0, entrust_prop="limit"):
        raise NotImplementedError

    @abc.abstractmethod
    def get_balance(self):
        raise NotImplementedError

    @abc.abstractmethod
    def get_position(self):
        raise NotImplementedError

    def submit(self, order: Order):
        if order.direction == "buy":
            return self.buy(order.code, order.price, order.amount, order.volume,
                            order.entrust_prop)
        return self.sell(order.code, order.price, order.amount, order.volume,
                         order.entrust_prop)