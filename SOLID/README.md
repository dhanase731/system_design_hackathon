# 10. SOLID Principles Applied to SALESTORM

## 1. Executive Summary
SALESTORM adheres strictly to the **SOLID** design principles to ensure maintainability, testability, and zero regression when introducing new payment methods, delivery couriers, or inventory persistence backends.

---

## 2. SOLID Mapping Matrix

| Principle | Core Definition | Concrete Demonstration in SALESTORM |
|---|---|---|
| **S - Single Responsibility** | A class should have one, and only one, reason to change. | `PaymentProcessor` handles transaction math; `PaymentNotificationService` handles customer alerts; `OrderLedger` persists orders. Neither touches the other's domain. |
| **O - Open / Closed** | Open for extension, closed for modification. | `PaymentGatewayAdapter` interface allows adding Apple Pay, PayPal, or Crypto without modifying core `PaymentManager` logic. |
| **L - Liskov Substitution** | Subtypes must be substitutable for their base types without altering program correctness. | `StripeAdapter` and `RazorpayAdapter` both implement `IPaymentGateway` conforming to standard exceptions, timeouts, and return contracts. |
| **I - Interface Segregation** | Clients should not be forced to depend on interfaces they do not use. | Separate focused interfaces (`IStockReservable`, `IStockQueryable`, `IStockReplenishable`) instead of a single bloated `IInventoryGodObject`. |
| **D - Dependency Inversion** | High-level modules should depend on abstractions, not low-level concrete implementations. | `CheckoutService` injects `IPaymentGateway` and `IInventoryRepository` abstractions via constructor DI rather than instantiating `StripeClient` or `PostgresDriver`. |

---

## 3. Code Implementations & Architectural Proof

### 3.1 Single Responsibility Principle (SRP)
```python
# GOOD: Each class has a single distinct responsibility
class InventoryReservationService:
    """Responsible ONLY for stock hold allocation and TTL management"""
    def reserve_stock(self, product_id: str, qty: int) -> ReservationToken:
        ...

class PaymentChargeService:
    """Responsible ONLY for monetary transactions and PSP authorization"""
    def execute_charge(self, token: ReservationToken, payment_info: dict) -> PaymentReceipt:
        ...

class OrderFulfillmentDispatcher:
    """Responsible ONLY for dispatching confirmed orders to warehouse queues"""
    def dispatch_to_warehouse(self, order_id: str) -> None:
        ...
```

---

### 3.2 Open/Closed Principle (OCP) & Liskov Substitution (LSP)
```python
from abc import ABC, abstractmethod

class IPaymentGateway(ABC):
    """Abstract contract open for extension"""
    @abstractmethod
    def charge(self, amount: float, token: str, idempotency_key: str) -> dict:
        pass

class StripeGatewayAdapter(IPaymentGateway):
    def charge(self, amount: float, token: str, idempotency_key: str) -> dict:
        # Calls Stripe SDK with idempotency key
        return {"status": "SUCCESS", "gateway_txn_id": "ch_stripe_123"}

class RazorpayGatewayAdapter(IPaymentGateway):
    def charge(self, amount: float, token: str, idempotency_key: str) -> dict:
        # Calls Razorpay SDK with idempotency key
        return {"status": "SUCCESS", "gateway_txn_id": "pay_razor_456"}

# High-level Checkout Coordinator is completely CLOSED to modification
class PaymentCoordinator:
    def __init__(self, gateway: IPaymentGateway):
        self.gateway = gateway # Fully substitutable (LSP)

    def process_checkout(self, amount: float, token: str, idemp_key: str):
        return self.gateway.charge(amount, token, idemp_key)
```

---

### 3.3 Interface Segregation Principle (ISP)
```python
# Segregated, lightweight interfaces tailored to specific consumer needs
class IStockReader(ABC):
    @abstractmethod
    def get_available_count(self, product_id: str) -> int:
        pass

class IStockReservable(ABC):
    @abstractmethod
    def atomic_reserve(self, product_id: str, qty: int, ttl: int) -> bool:
        pass

class IStockAdmin(ABC):
    @abstractmethod
    def replenish_stock(self, product_id: str, qty: int) -> None:
        pass
```

---

### 3.4 Dependency Inversion Principle (DIP)
```python
class OrderManager:
    # Depends entirely on abstract interfaces, injected at runtime
    def __init__(
        self,
        inventory_repo: IStockReservable,
        payment_gateway: IPaymentGateway,
        event_bus: IEventPublisher
    ):
        self._inventory = inventory_repo
        self._payment = payment_gateway
        self._events = event_bus
```
