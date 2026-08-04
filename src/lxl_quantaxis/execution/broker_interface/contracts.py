from typing import Protocol

from src.lxl_quantaxis.execution.orders import Order


class Broker(Protocol):
    def submit(self, order: Order) -> Order: ...

    def cancel(self, order_id: str) -> Order: ...
