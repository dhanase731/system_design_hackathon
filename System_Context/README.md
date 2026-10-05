# 02. System Context Design (C4 Level 1)

## 1. System Overview
The **SALESTORM Platform** acts as the core transactional engine coordinating high-velocity customer interactions, distributed payment gateways, shipping logistics partners, and communication providers.

---

## 2. Visual Architecture: System Context

![System Context Diagram](../LLD/system_context%20diagram.jpeg)

```mermaid
C4Context
    title System Context Diagram (Level 1) - SALESTORM Flash Sale Platform

    Person(customer, "Online Customer", "High-concurrency buyer browsing flash sales & purchasing limited stock")
    Person(admin, "Warehouse / Admin", "Manages catalog, inventory replenishment, and operational monitoring")

    System(salestorm, "SALESTORM Core Platform", "Handles high-concurrency requests, atomic inventory reservations, idempotent checkout, payment coordination, and order lifecycle")

    System_Ext(psp, "Payment Gateway / PSP", "Stripe / Razorpay / Adyen for card & UPI authorizations")
    System_Ext(logistics, "3PL Logistics Partner", "FedEx / BlueDart / ShipStation for dispatch & real-time parcel tracking")
    System_Ext(comms, "Notification Service", "Twilio / SendGrid / Firebase for transactional SMS, Email & Push alerts")
    System_Ext(cdn, "Cloudflare / Akamai CDN & WAF", "Edge caching for static catalog and DDoS/Bot shield")

    Rel(customer, cdn, "Browses products & initiates Buy Now", "HTTPS / WSS")
    Rel(cdn, salestorm, "Routes authenticated & rate-limited traffic", "HTTPS / REST")
    Rel(admin, salestorm, "Updates inventory & views telemetry", "HTTPS / Admin UI")
    
    Rel(salestorm, psp, "Processes payment transactions & webhook callbacks", "HTTPS / Mutual TLS")
    Rel(salestorm, logistics, "Dispatches manifest & pulls tracking updates", "HTTPS / Webhooks")
    Rel(salestorm, comms, "Triggers transactional SMS/Email notifications", "gRPC / REST")
```

---

## 3. External System Boundaries & Interfaces

| External Entity | Integration Protocol | Failure Recovery Strategy |
|---|---|---|
| **Customer Clients (Web/Mobile)** | HTTPS / REST / SSE | Exponential backoff retry, cached product catalog, optimistic UI updates. |
| **CDN & WAF (Cloudflare/Akamai)** | Anycast DNS / Edge Caching | Edge rate-limiting (Token bucket), WAF bot detection, static page failover. |
| **Payment Gateways (PSP)** | HTTPS / Webhooks / mTLS | Circuit Breaker (Polly/Resilience4j), Async Webhook reconciliation, Idempotency keys. |
| **3PL Logistics Partners** | REST APIs / Webhooks | Asynchronous message queues (Kafka `order-confirmed`), dead-letter queues. |
| **Notification Services** | gRPC / REST | Fire-and-forget async event consumption (`notification-events` topic). |

---

## 4. Key Responsibilities & System Boundaries

* **Inside System Boundary:**
  * Rate limiting & bot filtering.
  * In-memory atomic inventory reservation (Redis Cluster).
  * Transactional persistence & strict data consistency (PostgreSQL).
  * Saga orchestration & state machine execution.
  * Distributed event streaming & Outbox pattern (Kafka).
* **Outside System Boundary:**
  * Banking / card network authorization (handled entirely by external PSPs).
  * Physical packaging and courier transportation (handled by 3PL partners).
  * Cellular SMS & SMTP deliverability (handled by Twilio/SendGrid).
