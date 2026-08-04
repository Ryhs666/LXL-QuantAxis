# -*- coding: utf-8 -*-
"""
Broker Interface — 券商交易适配器抽象基类

定义统一交易接口，所有券商适配器必须继承。
当前实现: PaperBroker (模拟盘), QMTAdapter (迅投QMT真实券商)

集成方式:
    from src.execution.brokers import BrokerFactory
    broker = BrokerFactory.create("paper", config)
    broker.connect()
    order = broker.place_order(Order(...))
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import uuid
import logging

logger = logging.getLogger("execution.brokers")


# ═══════════════════════════════════════════
# 枚举
# ═══════════════════════════════════════════

class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderStatus(Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


# ═══════════════════════════════════════════
# 数据结构
# ═══════════════════════════════════════════

@dataclass
class Order:
    order_id: str = ""
    symbol: str = ""
    side: OrderSide = OrderSide.BUY
    quantity: int = 0
    price: Optional[float] = None
    order_type: OrderType = OrderType.LIMIT
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: int = 0
    filled_price: float = 0.0
    broker_order_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    error_msg: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "order_id": self.order_id,
            "symbol": self.symbol,
            "side": self.side.value,
            "quantity": self.quantity,
            "price": self.price,
            "order_type": self.order_type.value,
            "status": self.status.value,
            "filled_quantity": self.filled_quantity,
            "filled_price": self.filled_price,
            "broker_order_id": self.broker_order_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "error_msg": self.error_msg,
        }


@dataclass
class Position:
    symbol: str
    quantity: int = 0
    available_quantity: int = 0
    avg_cost: float = 0.0
    market_value: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0


@dataclass
class Account:
    account_id: str
    total_assets: float = 0.0
    cash: float = 0.0
    frozen_cash: float = 0.0
    positions: List[Position] = field(default_factory=list)
    buying_power: float = 0.0


# ═══════════════════════════════════════════
# 抽象基类
# ═══════════════════════════════════════════

class BrokerInterface(ABC):
    """券商交易适配器抽象基类"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.account_id = config.get("account_id", "default")
        self._orders: Dict[str, Order] = {}
        self._order_callbacks: List[Callable] = []
        self._is_connected = False
        self._heartbeat_interval = config.get("heartbeat_interval", 30)
        logger.info(f"[Broker] 初始化: {self.__class__.__name__}, 账户: {self.account_id}")

    @abstractmethod
    def connect(self) -> bool: ...

    @abstractmethod
    def disconnect(self) -> bool: ...

    @abstractmethod
    def place_order(self, order: Order) -> Order: ...

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool: ...

    @abstractmethod
    def query_order(self, order_id: str) -> Optional[Order]: ...

    @abstractmethod
    def query_positions(self) -> List[Position]: ...

    @abstractmethod
    def query_account(self) -> Account: ...

    def heartbeat(self) -> bool:
        if not self._is_connected:
            logger.warning(f"[{self.account_id}] 连接断开, 重连...")
            return self.connect()
        return True

    def on_order_update(self, callback: Callable):
        self._order_callbacks.append(callback)

    def _notify_order_update(self, order: Order):
        for cb in self._order_callbacks:
            try: cb(order)
            except Exception as e: logger.error(f"回调失败: {e}")

    def _generate_order_id(self) -> str:
        return f"ORD_{self.account_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"

    def _update_order(self, order: Order) -> Order:
        self._orders[order.order_id] = order
        self._notify_order_update(order)
        return order


# ═══════════════════════════════════════════
# PaperBroker — 模拟盘
# ═══════════════════════════════════════════

class PaperBroker(BrokerInterface):
    """模拟盘适配器 — 即时成交, 无延迟, 无滑点"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self._positions: Dict[str, Position] = {}
        self._cash = config.get("initial_cash", 1_000_000.0)
        self._total_assets = self._cash
        self._last_prices: Dict[str, float] = {}

    def connect(self) -> bool:
        self._is_connected = True
        return True

    def disconnect(self) -> bool:
        self._is_connected = False
        return True

    def place_order(self, order: Order) -> Order:
        if not self._is_connected:
            order.status = OrderStatus.REJECTED
            order.error_msg = "未连接"
            return self._update_order(order)

        price = order.price or self._last_prices.get(order.symbol, 100.0)

        if order.side == OrderSide.BUY:
            required = order.quantity * price
            if required > self._cash:
                order.status = OrderStatus.REJECTED
                order.error_msg = f"现金不足: 需要{required:,.0f}, 可用{self._cash:,.0f}"
                return self._update_order(order)

            self._cash -= required
            if order.symbol in self._positions:
                pos = self._positions[order.symbol]
                total_cost = pos.avg_cost * pos.quantity + required
                pos.quantity += order.quantity
                pos.avg_cost = total_cost / max(pos.quantity, 1)
                pos.available_quantity = pos.quantity
            else:
                self._positions[order.symbol] = Position(
                    symbol=order.symbol, quantity=order.quantity,
                    available_quantity=order.quantity,
                    avg_cost=price, market_value=order.quantity * price,
                )
        else:
            pos = self._positions.get(order.symbol)
            if not pos or pos.available_quantity < order.quantity:
                order.status = OrderStatus.REJECTED
                order.error_msg = f"持仓不足"
                return self._update_order(order)

            self._cash += order.quantity * price
            pos.quantity -= order.quantity
            pos.available_quantity = pos.quantity
            if pos.quantity == 0:
                del self._positions[order.symbol]

        order.status = OrderStatus.FILLED
        order.filled_quantity = order.quantity
        order.filled_price = price
        order.broker_order_id = f"PAPER_{order.order_id}"
        self._update_total_assets()
        return self._update_order(order)

    def cancel_order(self, order_id: str) -> bool:
        order = self._orders.get(order_id)
        if order and order.status in (OrderStatus.PENDING, OrderStatus.SUBMITTED):
            order.status = OrderStatus.CANCELLED
            self._update_order(order)
            return True
        return False

    def query_order(self, order_id: str) -> Optional[Order]:
        return self._orders.get(order_id)

    def query_positions(self) -> List[Position]:
        return list(self._positions.values())

    def query_account(self) -> Account:
        self._update_total_assets()
        return Account(
            account_id=self.account_id,
            total_assets=self._total_assets,
            cash=self._cash,
            positions=list(self._positions.values()),
            buying_power=self._cash * 0.8,
        )

    def _update_total_assets(self):
        pos_value = sum(p.quantity * p.avg_cost for p in self._positions.values())
        self._total_assets = self._cash + pos_value


# ═══════════════════════════════════════════
# QMTAdapter — 迅投QMT真实券商
# ═══════════════════════════════════════════

class QMTAdapter(BrokerInterface):
    """迅投QMT适配器 — 对接真实券商柜台"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self._xt_trader = None
        self._account_obj = None
        self._session_id = config.get("session_id", 1)

    def connect(self) -> bool:
        try:
            from xtquant import xttrader
            self._xt_trader = xttrader.XtTrader()

            # 连接 QMT 客户端
            result = self._xt_trader.connect(
                path=self.config.get("qmt_path", ""),
                session_id=self._session_id,
            )
            if result == 0:
                # 订阅账户
                self._account_obj = self.config.get("account_id", "")
                self._xt_trader.subscribe(self._account_obj)
                self._is_connected = True
                logger.info(f"[QMT] 连接成功: {self._account_obj}")
                return True
            logger.error(f"[QMT] 连接失败, 错误码: {result}")
            return False
        except ImportError:
            logger.error("[QMT] xtquant 未安装: pip install xtquant")
            return False
        except Exception as e:
            logger.error(f"[QMT] 连接异常: {e}")
            return False

    def disconnect(self) -> bool:
        if self._xt_trader:
            try:
                self._xt_trader.disconnect()
            except Exception:
                pass
        self._is_connected = False
        return True

    def place_order(self, order: Order) -> Order:
        if not self._is_connected:
            order.status = OrderStatus.REJECTED
            order.error_msg = "未连接"
            return self._update_order(order)

        try:
            side_code = 0 if order.side == OrderSide.BUY else 1
            price_type = {
                OrderType.LIMIT: 0,
                OrderType.MARKET: 1,
            }.get(order.order_type, 0)

            result = self._xt_trader.order_stock(
                account_id=self._account_obj,
                stock_code=order.symbol,
                order_type=side_code,
                price_type=price_type,
                price=order.price or 0.0,
                volume=order.quantity,
                strategy_name="LXL_QuantAxis",
                order_remark="",
            )

            # result: (order_id, error_code) 或仅 error_code
            if isinstance(result, tuple) and len(result) == 2:
                broker_id, error_code = result
                if error_code == 0:
                    order.status = OrderStatus.SUBMITTED
                    order.broker_order_id = str(broker_id)
                    logger.info(f"[QMT] 下单成功: {order.symbol} {order.side.value} x{order.quantity}")
                else:
                    order.status = OrderStatus.REJECTED
                    order.error_msg = f"QMT错误码: {error_code}"
            else:
                order.status = OrderStatus.REJECTED
                order.error_msg = f"QMT返回异常: {result}"
        except Exception as e:
            order.status = OrderStatus.REJECTED
            order.error_msg = f"{type(e).__name__}: {e}"

        return self._update_order(order)

    def cancel_order(self, order_id: str) -> bool:
        order = self._orders.get(order_id)
        if not order or not order.broker_order_id:
            return False
        try:
            result = self._xt_trader.cancel_order(
                account_id=self._account_obj,
                order_id=int(order.broker_order_id),
            )
            if result == 0:
                order.status = OrderStatus.CANCELLED
                self._update_order(order)
                return True
        except Exception as e:
            logger.error(f"[QMT] 撤单异常: {e}")
        return False

    def query_order(self, order_id: str) -> Optional[Order]:
        """查询订单 — 通过QMT柜台查询订单状态和成交明细"""
        order = self._orders.get(order_id)
        if not order or not order.broker_order_id:
            return None

        try:
            # 调用QMT查询接口
            result = self._xt_trader.query_stock_order(
                account_id=self._account_obj,
                order_id=int(order.broker_order_id),
            )

            if result is None:
                return order  # 返回缓存

            # 映射QMT状态
            status_map = {
                0: OrderStatus.SUBMITTED,
                1: OrderStatus.SUBMITTED,     # 已报
                2: OrderStatus.SUBMITTED,     # 已受理
                3: OrderStatus.PARTIALLY_FILLED,
                4: OrderStatus.FILLED,        # 全部成交
                5: OrderStatus.CANCELLED,     # 已撤
                6: OrderStatus.REJECTED,      # 废单
            }

            if hasattr(result, 'order_status'):
                order.status = status_map.get(
                    result.order_status, OrderStatus.SUBMITTED
                )
            if hasattr(result, 'filled_volume'):
                order.filled_quantity = result.filled_volume
            if hasattr(result, 'filled_price') and result.filled_volume > 0:
                order.filled_price = result.filled_price

            order.updated_at = datetime.now()
            self._update_order(order)
        except Exception as e:
            logger.warning(f"[QMT] 查询订单异常: {e}")

        return order

    def query_positions(self) -> List[Position]:
        """查询持仓 — 从QMT获取全量持仓"""
        if not self._is_connected:
            return []

        try:
            result = self._xt_trader.query_stock_positions(self._account_obj)
            if result is None:
                return []

            positions = []
            for pos in result:
                positions.append(Position(
                    symbol=getattr(pos, 'stock_code', ''),
                    quantity=getattr(pos, 'volume', 0),
                    available_quantity=getattr(pos, 'can_use_volume', 0),
                    avg_cost=getattr(pos, 'open_price', 0.0),
                    market_value=getattr(pos, 'market_value', 0.0),
                    unrealized_pnl=getattr(pos, 'float_profit', 0.0),
                    realized_pnl=getattr(pos, 'profit', 0.0),
                ))
            return positions
        except Exception as e:
            logger.error(f"[QMT] 查询持仓异常: {e}")
            return []

    def query_account(self) -> Account:
        """查询账户 — 从QMT获取资金和总资产"""
        if not self._is_connected:
            return Account(account_id=self.account_id)

        try:
            asset = self._xt_trader.query_stock_asset(self._account_obj)
            if asset is None:
                return Account(account_id=self.account_id)

            return Account(
                account_id=self.account_id,
                total_assets=getattr(asset, 'total_asset', 0.0),
                cash=getattr(asset, 'cash', 0.0),
                frozen_cash=getattr(asset, 'frozen_cash', 0.0),
                buying_power=getattr(asset, 'buying_power', 0.0),
            )
        except Exception as e:
            logger.error(f"[QMT] 查询账户异常: {e}")
            return Account(account_id=self.account_id)


# ═══════════════════════════════════════════
# BrokerFactory
# ═══════════════════════════════════════════

class BrokerFactory:
    """券商适配器工厂 — 根据配置创建实例"""

    _adapters = {
        "paper": PaperBroker,
        "qmt": QMTAdapter,
    }

    @classmethod
    def register(cls, name: str, adapter_class: type):
        cls._adapters[name] = adapter_class

    @classmethod
    def create(cls, broker_type: str, config: Dict[str, Any] = None) -> BrokerInterface:
        config = config or {}
        adapter_class = cls._adapters.get(broker_type)
        if not adapter_class:
            raise ValueError(
                f"不支持的券商类型: {broker_type}, "
                f"可用: {list(cls._adapters)}"
            )
        return adapter_class(config)

    @classmethod
    def list_types(cls) -> List[str]:
        return list(cls._adapters.keys())
