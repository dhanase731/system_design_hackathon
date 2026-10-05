# 06. Payment Reliability & Order Management Workflows

## 1. Overview
In a flash sale, payment processing is the most volatile boundary due to external third-party dependencies (Payment Service Providers / PSPs), banking latencies, network timeouts, and potential downstream microservice crashes.

---

## 2. Order & Payment State Machines

### 2.1 Order State Transition Engine
```mermaid
stateDiagram-v2
    [*] --> CREATED : User Initiates Checkout
    CREATED --> PAYMENT_PENDING : Payment Intent Generated
    
    PAYMENT_PENDING --> CONFIRMED : PSP 200 OK + Payment Capture
    PAYMENT_PENDING --> CANCELLED : PSP 402 Declined / User Cancel
    PAYMENT_PENDING --> CANCELLED : 10-min Reservation Expiry
    
    CONFIRMED --> PROCESSING : Warehouse Allocation & Invoicing
    PROCESSING --> SHIPPED : Manifest Handed to 3PL Courier
    SHIPPED --> OUT_FOR_DELIVERY : Last-mile Hub Dispatch
    OUT_FOR_DELIVERY --> DELIVERED : OTP Verified at Customer Doorstep
    
    CANCELLED --> [*]
    DELIVERED --> [*]
```

### 2.2 Payment State Transition Engine
```mermaid
stateDiagram-v2
    [*] --> INITIALIZED : Request Received
    INITIALIZED --> PROCESSING : Dispatched to PSP via mTLS
    
    PROCESSING --> SUCCESS : Webhook / Synchronous 200 OK
    PROCESSING --> FAILED : Card Declined / Bank Insufficient Funds
    PROCESSING --> TIMED_OUT : Network Drop (> 3.0s Timeout)
    
    TIMED_OUT --> PROCESSING : Idempotent Query Reconciliation
    TIMED_OUT --> REFUNDED : PSP debited money but Order unrecoverable
    
    SUCCESS --> [*]
    FAILED --> [*]
    REFUNDED --> [*]
```

---

## 3. Handling Critical Payment & Order Scenarios

| Scenario | System Response & Mitigation Strategy |
|---|---|
| **Scenario 1: Payment Succeeds** | PSP returns 200 OK. Payment Service atomically writes transaction record and publishes `payment.completed` event to Kafka via Transactional Outbox. Order Service creates `CONFIRMED` order. |
| **Scenario 2: Payment Fails** | PSP returns 402/500 error. Payment Service records `FAILED` status, releases the Redis & DB reservation immediately, and notifies the customer to retry with another card. |
| **Scenario 3: Payment Times Out** | Client connection drops after 3000ms. Payment Service marks payment `PENDING_RECONCILIATION`. A background worker queries PSP endpoint `GET /v1/charges/{idempotency_key}`. If charged $\to$ confirms order; if not charged $\to$ cancels transaction. |
| **Scenario 4: Duplicate Payment Clicks** | Customer rapidly clicks "Pay" 5 times. API Gateway checks `Idempotency-Key` in Redis cache. First request proceeds; subsequent 4 requests receive HTTP 409 / cached response without invoking PSP. |
| **Scenario 5: Payment Succeeds; Order Service Fails (Crash for 30s)** | Payment Service committed transaction and published to Kafka topic `payment.completed`. Kafka retains messages persistently for 7 days. When Order Service recovers, it resumes reading from its last committed offset and reliably creates all orders with zero data loss. |

---

## 4. Idempotency Implementation Architecture

```mermaid
flowchart TD
    Req[Payment Request with Idempotency-Key: 'pay_usr12_txn99'] --> CheckCache{Key in Redis?}
    CheckCache -->|Yes: State = In-Progress| Return409[Return 409 Conflict: Request Already Processing]
    CheckCache -->|Yes: State = Completed| ReturnCached[Return Cached HTTP 200 Response Payload]
    CheckCache -->|No: First Time| AcquireLock[Acquire Redis Lock with 30s TTL]
    
    AcquireLock --> CallPSP[Call External PSP Gateway]
    CallPSP --> StoreDB[Persist in Postgres `payments` with UNIQUE `idempotency_key`]
    StoreDB --> UpdateRedisCache[Store Final Response in Redis with 24h TTL]
    UpdateRedisCache --> ReleaseLock[Release Lock & Return Response]
```

---

## 5. Circuit Breaker & Retry Policies

```mermaid
graph LR
    subgraph Circuit_Breaker_State
        Closed[CLOSED: Normal Traffic] -->|Failure Rate > 50%| Open[OPEN: Fast Fail / Fallback]
        Open -->|Sleep Window 15s| HalfOpen[HALF-OPEN: Probe 5 Requests]
        HalfOpen -->|All Succeed| Closed
        HalfOpen -->|Any Fail| Open
    end
```

### Configured Resilience Rules (Resilience4j / Envoy)
* **Timeout:** Maximum **3000ms** for external PSP calls.
* **Retry Strategy:** Max **3 retries** using **Exponential Backoff with Full Jitter**:
  $$t_{\text{sleep}} = \text{random}(0, \min(M, B \times 2^{\text{attempt}}))$$
  *(where $B = 200\text{ms}$ and $M = 2000\text{ms}$)*.
* **Circuit Breaker Threshold:** If $50\%$ of calls fail in a 20-request sliding window, circuit opens for 15 seconds to prevent cascading thread pool exhaustion.
