# 03. High-Level Architecture Design (HLD)

## 1. High-Level Architecture Overview
SALESTORM is designed as a **hybrid event-driven microservices architecture** optimized for flash-sale peak loads. It decouples synchronous, low-latency user reservation paths from asynchronous, resilient order processing workflows.

---

## 2. Visual Architecture Diagrams

### 2.1 Service Architecture Diagram
![Service Architecture Diagram](../LLD/service_architecture%20diagram.jpeg)

### 2.2 Deployment Diagram
![Deployment Diagram](../LLD/deployment_diagram.jpeg)

---

## 3. End-to-End System Architecture (C4 Container View)

```mermaid
flowchart TD
    subgraph Client_Layer [Client & Edge Layer]
        User[Users: 10,000 Concurrent]
        CDN[CDN / WAF: Cloudflare Edge Caching & Bot Mitigation]
        LB[Layer 7 Load Balancer: NGINX / AWS ALB]
    end

    subgraph Gateway_Layer [API Gateway & Auth]
        APIGW[Kong / Envoy API Gateway\n- JWT Validation\n- Rate Limiting: 100 req/min/IP\n- SSL Termination]
    end

    subgraph Core_Services [Microservices Tier]
        ProdSvc[Product Catalog Service]
        CartSvc[Cart Service]
        ResvSvc[Inventory Reservation Service]
        PaySvc[Payment Service]
        OrdSvc[Order Service]
        FmtSvc[Fulfilment & Shipping Service]
        NotifSvc[Notification Service]
    end

    subgraph Data_Tier [Distributed Data & Cache Tier]
        RedisStock[(Redis Cluster: Master-Replica\n- Atomic Stock Decrement via Lua\n- Reservation TTL Keys)]
        PostgresDB[(PostgreSQL Primary-Replica Cluster\n- Orders, Inventory Ledger, Payments\n- Read Replicas for Analytics)]
        KafkaBroker[[Apache Kafka Message Bus\n- Topics: inventory.reserved, payment.completed,\n  order.created, notification.send]]
    end

    subgraph External_Tier [External Gateways]
        PSP[External Payment Gateway: Stripe/Razorpay]
        Courier[Logistics Partner: FedEx/3PL]
        SMS[Notification Gateway: Twilio/SendGrid]
    end

    User -->|1. HTTPS Request| CDN
    CDN -->|2. Filtered Traffic| LB
    LB -->|3. Load Balanced| APIGW

    APIGW -->|Browse Catalog| ProdSvc
    APIGW -->|Add to Cart| CartSvc
    APIGW -->|Buy Now / Reserve| ResvSvc
    APIGW -->|Execute Payment| PaySvc
    APIGW -->|Get Order Status| OrdSvc

    ProdSvc -.->|Read Cached Catalog| RedisStock
    ResvSvc ==>|Atomic Lua Script| RedisStock
    ResvSvc -->|Publish Event / Outbox| KafkaBroker
    
    PaySvc -->|Mutual TLS| PSP
    PaySvc -->|Store Transaction| PostgresDB
    PaySvc -->|Publish payment.completed| KafkaBroker

    KafkaBroker ==>|Consume payment.completed| OrdSvc
    OrdSvc -->|Write Order Record| PostgresDB
    OrdSvc -->|Publish order.created| KafkaBroker

    KafkaBroker ==>|Consume order.created| FmtSvc
    KafkaBroker ==>|Consume order.created| NotifSvc
    
    FmtSvc -->|Dispatch API| Courier
    NotifSvc -->|Send Push/SMS| SMS
```

---

## 4. Synchronous vs. Asynchronous Communication Boundaries

```
[SYNCHRONOUS PATH (Ultra Low Latency < 50ms)]
Client ──► API GW ──► Reservation Service ──► Redis (Lua Atomic Decr) ──► 201 Created (Token)

[ASYNCHRONOUS WORKFLOW (High Resiliency & Eventual Consistency)]
Payment Success ──► Kafka Topic (payment.completed) ──► Order Service ──► DB Persist ──► Notification
```

| Path | Protocol | Justification |
|---|---|---|
| **Catalog Browsing** | HTTP/2 (Sync) | Read-heavy, heavily cached in CDN & Redis. Sub-10ms response time. |
| **Inventory Reservation** | HTTP/2 $\to$ In-Memory Redis (Sync) | Immediate feedback is mandatory for the user experience. |
| **Payment Gateway Interaction** | HTTPS (Sync with Circuit Breaker) | Client requires immediate payment authorization status. |
| **Order Creation & Invoicing** | Event-Driven / Kafka (Async) | Protects Order DB from write starvation; decouples order creation from payment latency. |
| **Shipping & Notifications** | Event-Driven / Kafka (Async) | Third-party latency (FedEx/Twilio) must never block user checkout flow. |

---

## 5. Architectural Component Justification & Bottleneck Elimination

| Component | Why it Exists | Bottleneck Mitigated |
|---|---|---|
| **CDN / Edge WAF** | Terminates TLS, caches static assets & catalog reads, filters malicious bot traffic. | Prevents DDoS attacks and offloads 90% of read traffic from origin servers. |
| **API Gateway (Kong/Envoy)** | Centralized routing, JWT authentication, and distributed token bucket rate limiting. | Protects backend microservices from connection exhaustion and unauthenticated floods. |
| **Redis In-Memory Engine** | Single-threaded atomic script execution for inventory counter and TTL expiration keys. | Eliminates relational DB row-lock contention where 10,000 concurrent writes choke 1 row. |
| **Transactional Outbox + Kafka** | Guaranteed at-least-once message delivery without distributed two-phase commits (2PC). | Prevents dual-write inconsistencies between PostgreSQL database and Kafka broker. |
| **PostgreSQL Primary/Replica** | ACID persistence for immutable ledgers, order history, audit trails, and financial records. | Relieved of flash-sale write spikes; handles confirmed orders smoothly via queue consumers. |
