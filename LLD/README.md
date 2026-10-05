# 04. Low-Level Design (LLD) & UML Specifications

## 1. Overview
This module details the Low-Level Design (LLD) of the three core critical microservices in SALESTORM:
1. **Inventory & Reservation Service**
2. **Payment Service**
3. **Order Management Service**

---

## 2. Component Architecture

![Component Diagram](component%20diagram.jpeg)

```mermaid
graph TB
    subgraph Client_Boundary [Client]
        App[React Web / Mobile App]
    end

    subgraph Inventory_Module [Inventory & Reservation Service]
        ResvCtrl[ReservationController]
        IdempFilter[IdempotencyFilter]
        ResvMgr[ReservationManager]
        RedisStockRepo[(RedisStockRepository)]
        DBStockRepo[(PostgresInventoryLedger)]
    end

    subgraph Payment_Module [Payment Service]
        PayCtrl[PaymentController]
        PayProcessor[PaymentProcessor]
        PSPAdapter[PaymentGatewayAdapter]
        PayOutbox[(PaymentOutboxTable)]
    end

    subgraph Order_Module [Order Service]
        OrdConsumer[PaymentEventConsumer]
        OrdMgr[OrderManager]
        OrdRepo[(OrderRepository)]
        StateEngine[OrderStateMachine]
    end

    App --> ResvCtrl
    ResvCtrl --> IdempFilter
    IdempFilter --> ResvMgr
    ResvMgr --> RedisStockRepo
    ResvMgr --> DBStockRepo

    App --> PayCtrl
    PayCtrl --> PayProcessor
    PayProcessor --> PSPAdapter
    PayProcessor --> PayOutbox

    PayOutbox -.->|Kafka: payment.completed| OrdConsumer
    OrdConsumer --> OrdMgr
    OrdMgr --> StateEngine
    OrdMgr --> OrdRepo
```

---

## 3. Class Diagrams for Critical Modules

### 3.1 Inventory & Reservation Class Diagram
![Inventory & Reservation Class Diagram](Inventory%20&%20Reservation%20class%20diagram.png)

```mermaid
classDiagram
    class InventoryController {
        +reserveStock(ReservationRequest request) ResponseEntity~ReservationResponse~
        +releaseStock(String reservationId) ResponseEntity~Void~
        +getAvailability(String productId) AvailabilityDTO
    }

    class IInventoryService {
        <<interface>>
        +reserve(String productId, String userId, int qty, String idempotencyKey) ReservationResult
        +confirm(String reservationId) boolean
        +release(String reservationId, String reason) boolean
    }

    class RedisInventoryService {
        -RedisTemplate redisTemplate
        -KafkaProducer kafkaProducer
        +reserve(String productId, String userId, int qty, String idempotencyKey) ReservationResult
        +confirm(String reservationId) boolean
        +release(String reservationId, String reason) boolean
    }

    class InventoryEntity {
        -String inventoryId
        -String productId
        -int availableQuantity
        -int reservedQuantity
        -int soldQuantity
        -long version
        -Timestamp updatedAt
        +reserve(int qty) boolean
        +confirm(int qty) void
        +release(int qty) void
    }

    class InventoryReservationEntity {
        -String reservationId
        -String productId
        -String userId
        -int quantity
        -ReservationStatus status
        -Timestamp expiresAt
        -String idempotencyKey
        +isExpired() boolean
    }

    class ReservationStatus {
        <<enumeration>>
        AVAILABLE
        RESERVED
        PAYMENT_PENDING
        CONFIRMED
        RELEASED
        SOLD
    }

    InventoryController --> IInventoryService
    IInventoryService <|.. RedisInventoryService
    RedisInventoryService --> InventoryEntity
    RedisInventoryService --> InventoryReservationEntity
    InventoryReservationEntity --> ReservationStatus
```

---

### 3.2 Payment Service Class Diagram
![Payment Class Diagram](../payment_class_diagram.png)

```mermaid
classDiagram
    class PaymentController {
        +initiatePayment(PaymentRequest request) ResponseEntity~PaymentResponse~
        +handleWebhook(String payload, String signature) ResponseEntity~Void~
    }

    class IPaymentProcessor {
        <<interface>>
        +processPayment(PaymentIntent intent) PaymentResult
        +verifySignature(String payload, String signature) boolean
        +refund(String paymentId, double amount) RefundResult
    }

    class StripePaymentAdapter {
        -StripeClient stripeClient
        -CircuitBreaker circuitBreaker
        +processPayment(PaymentIntent intent) PaymentResult
    }

    class RazorpayPaymentAdapter {
        -RazorpayClient razorpayClient
        -CircuitBreaker circuitBreaker
        +processPayment(PaymentIntent intent) PaymentResult
    }

    class PaymentFactory {
        +getAdapter(PaymentProvider provider) IPaymentProcessor
    }

    class PaymentTransactionEntity {
        -String transactionId
        -String reservationId
        -String orderId
        -String userId
        -double amount
        -String currency
        -PaymentStatus status
        -String idempotencyKey
        -Timestamp createdAt
    }

    PaymentController --> PaymentFactory
    PaymentFactory --> IPaymentProcessor
    IPaymentProcessor <|.. StripePaymentAdapter
    IPaymentProcessor <|.. RazorpayPaymentAdapter
    PaymentController --> PaymentTransactionEntity
```

---

### 3.3 Order Management Class Diagram
![Order Class Diagram](oder%20class_diagram.png)

```mermaid
classDiagram
    class OrderController {
        +getOrder(String orderId) OrderDTO
        +getUserOrders(String userId) List~OrderDTO~
    }

    class OrderManager {
        -IOrderRepository orderRepository
        -OrderStateMachine stateMachine
        -IEventPublisher eventPublisher
        +createOrderFromPayment(PaymentCompletedEvent event) OrderEntity
        +updateStatus(String orderId, OrderStatus newStatus) boolean
        +cancelOrder(String orderId, String reason) boolean
    }

    class OrderEntity {
        -String orderId
        -String userId
        -String reservationId
        -List~OrderItem~ items
        -double totalAmount
        -OrderStatus status
        -ShippingAddress shippingAddress
        -Timestamp createdAt
        -Timestamp updatedAt
        +transitionTo(OrderStatus nextState) void
    }

    class OrderStatus {
        <<enumeration>>
        CREATED
        PAYMENT_PENDING
        CONFIRMED
        PROCESSING
        SHIPPED
        OUT_FOR_DELIVERY
        DELIVERED
        CANCELLED
    }

    OrderController --> OrderManager
    OrderManager --> OrderEntity
    OrderEntity --> OrderStatus
```

---

## 4. Sequence Diagrams

### 4.1 Purchase & Inventory Reservation Sequence
![Purchase Sequence](Purchase+inverntory_reservation%20sequence_diagram.jpeg)

```mermaid
sequenceDiagram
    autonumber
    actor Customer
    participant Gateway as API Gateway
    participant ResvSvc as Reservation Service
    participant Redis as Redis Stock Cluster
    participant Kafka as Kafka Event Bus

    Customer->>Gateway: POST /api/v1/reservations (productId, userId, idempotencyKey)
    Gateway->>Gateway: Rate Limit & Auth Validation
    Gateway->>ResvSvc: Forward Reserve Request
    ResvSvc->>Redis: Execute Atomic Lua Script (check & decr stock, set TTL 10m)
    
    alt Stock Available (<= 100 sold)
        Redis-->>ResvSvc: 1 (Success, reservation_id, expires_at)
        ResvSvc->>Kafka: Publish `inventory.reserved` Event
        ResvSvc-->>Gateway: 201 Created (reservationId, lockExpiresIn: 600s)
        Gateway-->>Customer: 201 Created (Proceed to Payment)
    else Stock Depleted (0 units left)
        Redis-->>ResvSvc: 0 (Sold Out)
        ResvSvc-->>Gateway: 409 Conflict ("Item Sold Out")
        Gateway-->>Customer: 409 Conflict ("Flash Sale Sold Out")
    else Duplicate Idempotency Key
        Redis-->>ResvSvc: Return Existing Reservation Token
        ResvSvc-->>Gateway: 200 OK (Existing reservationId)
        Gateway-->>Customer: 200 OK (Resume Checkout)
    end
```

---

### 4.2 Payment Execution Sequence
![Payment Sequence](Payment_sequence_diagram.jpeg)

```mermaid
sequenceDiagram
    autonumber
    actor Customer
    participant Gateway as API Gateway
    participant PaySvc as Payment Service
    participant PSP as External PSP (Stripe/Razorpay)
    participant DB as Postgres (Transactional Outbox)
    participant Kafka as Kafka Broker

    Customer->>Gateway: POST /api/v1/payments (reservationId, token, idempotencyKey)
    Gateway->>PaySvc: Validate & Forward Payment
    PaySvc->>DB: Check Idempotency Key in `payments` Table

    alt Payment Key Already Exists
        DB-->>PaySvc: Return Cached Status (SUCCESS/FAILED)
        PaySvc-->>Gateway: 200 OK (Cached Result)
        Gateway-->>Customer: 200 OK
    else New Payment Request
        PaySvc->>PSP: Authorize & Capture Charge (mTLS + Timeout 3s)
        alt PSP Success
            PSP-->>PaySvc: 200 OK (charge_id: "ch_98432")
            PaySvc->>DB: BEGIN TX: Insert `payment_transaction` + Outbox Event; COMMIT
            PaySvc->>Kafka: Publish `payment.completed` Event
            PaySvc-->>Gateway: 200 OK (Payment Confirmed)
            Gateway-->>Customer: 200 OK (Payment Confirmed)
        else PSP Failed / Declined
            PSP-->>PaySvc: 402 Card Declined
            PaySvc->>DB: Save Payment Status: FAILED
            PaySvc->>Kafka: Publish `payment.failed` Event (Triggers Inventory Release)
            PaySvc-->>Gateway: 402 Payment Required ("Declined")
            Gateway-->>Customer: 402 Error ("Card Declined, Reservation Released")
        else PSP Timeout (Network Drop)
            PaySvc->>PaySvc: Trigger Async PSP Reconciliation Query
            PaySvc-->>Gateway: 202 Accepted ("Processing, result via webhook/polling")
            Gateway-->>Customer: 202 Accepted ("Payment Verification in Progress")
        end
    end
```

---

### 4.3 Order Creation & Resilient Recovery Sequence
![Order Creation Sequence](order_creation_sequence_diagram.jpeg)

```mermaid
sequenceDiagram
    autonumber
    participant Kafka as Kafka Broker
    participant OrdSvc as Order Service
    participant OrdDB as Postgres DB
    participant DLQ as Dead Letter Queue (DLQ)
    participant NotifSvc as Notification Service

    Kafka->>OrdSvc: Consume `payment.completed` (Event ID: evt_501)
    
    critical Order DB Transaction
        OrdSvc->>OrdDB: Check if Order with paymentId exists (Idempotency)
        alt Order Does Not Exist
            OrdSvc->>OrdDB: INSERT INTO orders (id, user_id, status='CONFIRMED')
            OrdSvc->>OrdDB: INSERT INTO order_items (...)
            OrdSvc->>OrdDB: UPDATE inventory_ledger (status='SOLD')
            OrdSvc->>Kafka: Publish `order.created` Event
        else Already Processed
            OrdSvc->>OrdSvc: Acknowledge & Skip (No duplicate insert)
        end
    option Order Service Down / DB Error (Retries Exceeded)
        OrdSvc-->>DLQ: Route to DLQ `payment.completed.dlq`
        Note over DLQ: Background Reconciliation Worker reprocesses DLQ every 60s
    end

    Kafka->>NotifSvc: Consume `order.created`
    NotifSvc->>Customer: Send SMS / Email Order Confirmation with Tracking ID
```
