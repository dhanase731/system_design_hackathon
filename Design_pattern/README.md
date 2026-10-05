# 11. Design Patterns Applied to SALESTORM

## 1. Design Patterns Architecture Summary

SALESTORM implements established GoF and enterprise microservice patterns to isolate business rules, manage state transitions, and shield the architecture from external volatility.

| Pattern | Architectural Role in SALESTORM | Problem Solved | Trade-off Introduced |
|---|---|---|---|
| **Strategy** | Dynamic checkout payment selection (Stripe vs Razorpay vs Apple Pay). | Eliminates messy `if-else` branching when selecting payment methods. | Slight increase in total class count. |
| **Factory** | `PaymentGatewayFactory` for runtime gateway initialization. | Centralizes credential retrieval and provider instantiation. | Extra abstraction layer. |
| **State** | `OrderStateMachine` & `ReservationStateMachine`. | Prevents invalid state transitions (e.g., cannot ship an unpaid order). | Requires explicit transition boilerplate. |
| **Observer** | Asynchronous Kafka event publisher & listener ecosystem. | Decouples order confirmation from notification and invoice dispatch. | Eventual consistency; requires event tracing. |
| **Adapter** | `StripeAdapter`, `FedExAdapter`. | Converts vendor-specific SDK formats to unified internal domain interfaces. | Maintenance overhead for external schema updates. |
| **Facade** | `CheckoutFacade`. | Unifies stock check, reservation, payment, and order initiation into one clean API. | Risk of becoming a God object if not scoped carefully. |
| **Repository** | `InventoryRepository`, `OrderRepository`. | Decouples domain logic from SQL/Redis persistence drivers. | Mapping overhead between ORM and Domain models. |
| **Circuit Breaker** | Protection around external PSP and Logistics REST calls. | Prevents thread-pool starvation during third-party gateway downtime. | Fast-failing requests when circuit is open. |

---

## 2. Code Pattern Implementations

### 2.1 State Pattern (Order State Management)
```python
class OrderState(ABC):
    @abstractmethod
    def confirm_payment(self, context) -> None: pass
    @abstractmethod
    def dispatch_shipment(self, context) -> None: pass

class CreatedState(OrderState):
    def confirm_payment(self, context):
        print("Payment received. Transitioning to CONFIRMED.")
        context.set_state(ConfirmedState())

    def dispatch_shipment(self, context):
        raise InvalidStateTransitionError("Cannot ship an unpaid order.")

class ConfirmedState(OrderState):
    def confirm_payment(self, context):
        print("Payment already confirmed. Ignoring duplicate.")

    def dispatch_shipment(self, context):
        print("Order dispatched. Transitioning to SHIPPED.")
        context.set_state(ShippedState())
```

---

### 2.2 Strategy & Factory Pattern (Payment Integration)
```python
class PaymentGatewayFactory:
    @staticmethod
    def get_gateway(provider: str) -> IPaymentGateway:
        if provider == "STRIPE":
            return StripeGatewayAdapter(api_key=os.getenv("STRIPE_KEY"))
        elif provider == "RAZORPAY":
            return RazorpayGatewayAdapter(key_id=os.getenv("RAZORPAY_KEY"))
        raise UnsupportedProviderException(f"Provider {provider} not supported.")
```

---

### 2.3 Circuit Breaker Pattern
```python
import time

class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 15):
        self.threshold = failure_threshold
        self.timeout = recovery_timeout
        self.failure_count = 0
        self.state = "CLOSED" # CLOSED, OPEN, HALF_OPEN
        self.last_state_change = time.time()

    def call(self, func, *args, **kwargs):
        if self.state == "OPEN":
            if time.time() - self.last_state_change > self.timeout:
                self.state = "HALF_OPEN"
            else:
                raise CircuitBreakerOpenException("PSP Service unavailable. Fast failing.")

        try:
            result = func(*args, **kwargs)
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            if self.failure_count >= self.threshold:
                self.state = "OPEN"
                self.last_state_change = time.time()
            raise e
```
