# 🌪️ SALESTORM — High-Scale E-Commerce Flash Sale System Design Blueprint

[![System Design Hackathon](https://img.shields.io/badge/SysCrafters%202026-SALESTORM-blue.svg)](file:///d:/SD_hackathon/Requirements/README.md)
[![Status](https://img.shields.io/badge/Architecture-Design--First%20%7C%20Jury--Ready-brightgreen.svg)](file:///d:/SD_hackathon/README.md)
[![Concurrency Verified](https://img.shields.io/badge/Concurrency-10%2C000%20Users%20vs%20100%20Stock%20(Zero%20Oversell)-success.svg)](file:///d:/SD_hackathon/Simulation/README.md)

---

## 🎯 Executive Overview & Problem Statement
**SALESTORM** is an enterprise-grade, high-scale e-commerce platform engineered specifically to withstand extreme flash-sale spikes. 

### The Core Challenge
When **10,000 concurrent customers simultaneously click "Buy Now" for only 100 available units**, the architecture guarantees:
1. **Zero Overselling:** Exactly 100 units sold; inventory never becomes negative ($\text{Stock} \ge 0$).
2. **Sub-50ms Response Latency:** Offloads contention from relational database row locks to an in-memory atomic Redis Lua engine.
3. **10-Minute Hold TTL:** Unpaid or abandoned reservations automatically expire and safely return to the available inventory pool.
4. **Strict Idempotency:** Duplicate clicks, retried payloads, and network jitter never cause duplicate charges or duplicate bookings.
5. **Resilient Order Creation:** Downstream service outages (e.g., Order Service down for 30s) are fully recovered via the Transactional Outbox pattern and Apache Kafka with zero data loss.

---

## 📁 Repository Navigation & Architecture Modules

Every folder in this repository contains a complete, jury-ready technical specification:

| Module / Folder | Description & Key Contents |
|---|---|
| [**`01. Requirements`**](file:///d:/SD_hackathon/Requirements/README.md) | Business context, Functional (FR-01 to FR-07) and Non-Functional Requirements, strict guarantees vs. targets. |
| [**`02. System Context`**](file:///d:/SD_hackathon/System_Context/README.md) | C4 Level 1 context diagram, external boundaries (Payment Gateways, 3PL Couriers, CDNs, Twilio). |
| [**`03. High-Level Design (HLD)`**](file:///d:/SD_hackathon/HLD/README.md) | C4 Container microservices architecture, sync vs. async boundaries, infrastructure justifications. |
| [**`04. Low-Level Design (LLD)`**](file:///d:/SD_hackathon/LLD/README.md) | Component architecture, Class diagrams for Inventory, Payment, and Order modules, and sequence flows. |
| [**`05. Concurrency & Inventory`**](file:///d:/SD_hackathon/Concurrency_Inventory/README.md) | Concurrency trade-offs, Redis atomic Lua script, reservation TTL engine, and negative inventory prevention. |
| [**`06. Payment & Order Workflows`**](file:///d:/SD_hackathon/Payment_Order/README.md) | Payment reliability, state machines, idempotency keys, circuit breakers, and handling Order Service crashes. |
| [**`07. Database Design`**](file:///d:/SD_hackathon/Database/README.md) | Entity Relationship (ER) diagram, complete PostgreSQL DDL schemas, constraints, indexing, and isolation. |
| [**`08. API Specifications`**](file:///d:/SD_hackathon/API/README.md) | REST API endpoints, OpenAPI schemas, headers (`Idempotency-Key`, `X-Correlation-ID`), and error models. |
| [**`09. Event-Driven Architecture`**](file:///d:/SD_hackathon/Events/README.md) | Kafka topic topology, CloudEvents JSON schemas, partition key strategy, and Dead Letter Queue (DLQ). |
| [**`10. SOLID Principles`**](file:///d:/SD_hackathon/SOLID/README.md) | Concrete mapping of SRP, OCP, LSP, ISP, and DIP to SALESTORM codebase with code examples. |
| [**`11. Design Patterns`**](file:///d:/SD_hackathon/Design_pattern/README.md) | Strategy, Factory, State, Observer, Adapter, Facade, Repository, and Circuit Breaker patterns with trade-offs. |
| [**`12. Capacity Planning`**](file:///d:/SD_hackathon/Capacity_planning/README.md) | Quantitative calculations for 10k baseline to 500k flash QPS, Redis RAM sizing, DB IOPS, and network bandwidth. |
| [**`13. Scalability Architecture`**](file:///d:/SD_hackathon/Scalability/README.md) | Horizontal auto-scaling (HPA), PgBouncer connection pooling, edge caching, and 50x spike playbook. |
| [**`14. Reliability & Fault Tolerance`**](file:///d:/SD_hackathon/Reliability/README.md) | Chaos recovery matrix, Transactional Outbox pattern, circuit breakers, retries with exponential backoff & jitter. |
| [**`15. Security Architecture`**](file:///d:/SD_hackathon/Security/README.md) | OAuth2/JWT auth, Cloudflare WAF bot mitigation, distributed Token Bucket rate limiting, and PCI-DSS tokenization. |
| [**`16. Observability & Telemetry`**](file:///d:/SD_hackathon/Observability/README.md) | Golden signals, Prometheus SLIs/SLOs, OpenTelemetry distributed tracing, Grafana dashboards, and PagerDuty alerts. |
| [**`17. Architecture Decisions (ADR)`**](file:///d:/SD_hackathon/ADR/README.md) | ADR-001 to ADR-005: PostgreSQL vs NoSQL, Redis Lua vs DB locking, SAGA vs 2PC, Outbox vs Dual Writes. |
| [**`18. Concurrency Simulation`**](file:///d:/SD_hackathon/Simulation/README.md) | Runnable Python test harness (`flash_sale_simulation.py`) validating 10,000 concurrent requests against 100 stock. |
| [**`AI Usage Disclosure`**](file:///d:/SD_hackathon/AI_USAGE.md) | Compliance declaration documenting AI tool usage, prompts, and engineering review validation. |

---

## ⏱️ 5-Minute Final Pitch Script for the Jury

| Time | Section | Key Points to Present |
|---|---|---|
| **0:00 - 0:30** | **1. The Problem** | Explain the flash sale dilemma: 10,000 customers colliding for 100 units at $T_0$. Traditional SQL databases choke on row-locks, leading to overselling or 504 gateway timeouts. |
| **0:30 - 1:00** | **2. Requirements & Guarantees** | Highlight strict linearizable consistency (never sell >100 units), 10-minute hold TTL, exactly-once payment idempotency, and sub-50ms reservation latency. |
| **1:00 - 2:00** | **3. High-Level Architecture** | Walk through the C4 container design: Cloudflare edge WAF filters bots $\to$ API Gateway rate limits $\to$ Redis Cluster processes atomic reservations $\to$ Kafka + Transactional Outbox guarantees decoupled asynchronous order creation. |
| **2:00 - 3:00** | **4. Critical Concurrency Mechanism** | **The Core Defense:** Explain why we rejected DB `SELECT FOR UPDATE` (connection starvation) and chose **Redis single-threaded atomic Lua scripts**. Explain the two-phase reservation and hybrid TTL sweeper. |
| **3:00 - 3:45** | **5. Payment & Order Workflows** | Walk through the state machine: Payment Success $\to$ Outbox emit $\to$ Order created; Payment Failure $\to$ Compensating event $\to$ Instant inventory release; Order Service down $\to$ Kafka persistent log prevents any lost orders. |
| **3:45 - 4:30** | **6. LLD, SOLID & Patterns** | Showcase Strategy pattern for multi-PSP support (Stripe/Razorpay), State pattern for Order lifecycle, and Interface Segregation (`IStockReservable` vs `IStockReader`). |
| **4:30 - 5:00** | **7. Scalability & Simulation Proof** | Highlight our Python test harness results: 10,000 async requests, 107,000 peak QPS, **exactly 100 items accounted for with zero overselling**! |

---

## 🏆 Final Jury Challenge Defense Cheat Sheet

### ❓ Question 1: *"Your architecture has 100 units remaining and 10,000 customers are simultaneously clicking Buy Now. Walk us through exactly what happens from request arrival until final valid orders are confirmed."*
> **Answer:**
> 1. **Ingress & Edge:** 10,000 HTTPS requests hit the Cloudflare CDN/WAF. WAF checks TLS fingerprints and bot scores; rate limiting ensures non-abusive client behavior.
> 2. **API Gateway:** Gateway validates JWT authentication and extracts the client-supplied `Idempotency-Key`.
> 3. **Atomic Contention Control:** Requests hit the Reservation Service, which executes an **Atomic Lua script on Redis**. The single-threaded Redis engine decrements the stock counter from 100 down to 0 sequentially in $\approx 12\text{ms}$.
> 4. **Reservation Token:** The first 100 requests receive a `201 Created` with a unique `reservation_id` and a 10-minute TTL hold (`SETEX resv_ttl:id 600`).
> 5. **Instant Fast-Rejection:** Requests 101 through 10,000 see `stock <= 0` and are immediately returned `409 Conflict (Sold Out)` without touching the PostgreSQL database.
> 6. **Payment & Order:** The 100 reserved users proceed to payment. Upon PSP authorization, the Payment Service writes to PostgreSQL and emits `payment.completed` via the Transactional Outbox to Kafka. The Order Service consumes the event and transitions the order to `CONFIRMED`.
> 7. **Failure Compensation:** If 5 users experience payment decline or close their browser, the compensating transaction (or 10-minute TTL expiry) releases those 5 units back into Redis, enabling waiting customers to purchase them.

---

### ❓ Question 2: *"Why is this the correct service boundary and why is inventory reservation synchronous while order processing is asynchronous?"*
> **Answer:**
> * **Synchronous Inventory Reservation:** The customer requires immediate, deterministic feedback on whether they secured an item. Redis Lua delivers this in $< 5\text{ms}$.
> * **Asynchronous Order Processing:** Once payment is confirmed, creating the invoice, allocating warehouse logistics, and sending SMS alerts do not need to block the user. Using Kafka decouples write throughput, buffers traffic spikes, and ensures zero order loss even if the Order Service is temporarily down.

---

### ❓ Question 3: *"What happens if the Order Service crashes for 30 seconds right after a user pays?"*
> **Answer:**
> * Because of the **Transactional Outbox Pattern**, the Payment Service atomically commits the payment to PostgreSQL and enqueues the `payment.completed` event to Kafka.
> * Kafka persists the message with replication factor 3.
> * When the Order Service restarts, it reconnects to Kafka, reads from its uncommitted offset, and safely generates the orders. No financial transactions are lost and no manual intervention is needed.
