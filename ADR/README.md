# 17. Architecture Decision Records (ADR)

## Index of Architectural Decisions

* [ADR-001: Relational PostgreSQL vs. NoSQL (MongoDB/DynamoDB) for Order & Financial Ledgers](#adr-001-relational-postgresql-vs-nosql-for-ledgers)
* [ADR-002: In-Memory Redis Lua Atomic Decrement vs. DB Row-Level Locking for Inventory](#adr-002-redis-lua-vs-db-locking-for-inventory)
* [ADR-003: Asynchronous Event-Driven Saga vs. Synchronous Two-Phase Commit (2PC)](#adr-003-event-driven-saga-vs-two-phase-commit)
* [ADR-004: Transactional Outbox Pattern with Kafka vs. Direct Dual Writes](#adr-004-transactional-outbox-pattern-vs-dual-writes)
* [ADR-005: Hybrid TTL Expiry Engine (Redis Keyspace Events + Scheduled SQL Poller)](#adr-005-hybrid-reservation-ttl-expiry-engine)

---

### ADR-001: Relational PostgreSQL vs. NoSQL for Ledgers
* **Status:** **Accepted**
* **Context:** SALESTORM requires strict ACID compliance for financial audit trails, order consistency, and zero lost data.
* **Decision:** Use PostgreSQL as the primary system of record for Orders, Payments, and Inventory Ledgers.
* **Alternatives Considered:** MongoDB, DynamoDB.
* **Consequences & Trade-offs:** Relational DB writes scale vertically rather than natively horizontally. We mitigate this by buffering writes through Apache Kafka and offloading catalog read traffic to CDN and Redis read-replicas.

---

### ADR-002: Redis Lua vs. DB Locking for Inventory
* **Status:** **Accepted**
* **Context:** 10,000 concurrent users clicking "Buy Now" for 100 stock units at the exact same millisecond will saturate DB connection pools and cause row-lock deadlock timeouts under traditional `SELECT ... FOR UPDATE`.
* **Decision:** Execute inventory reservation atomically in **Redis using single-threaded Lua scripts**.
* **Alternatives Considered:** DB Pessimistic Lock (`SELECT FOR UPDATE`), DB Optimistic Concurrency Control (`version = version + 1`).
* **Consequences & Trade-offs:** Introduces memory state into Redis. Mitigated by persisting confirmed reservations to PostgreSQL and backing Redis with AOF persistence and multi-AZ replication.

---

### ADR-003: Event-Driven Saga vs. Two-Phase Commit (2PC)
* **Status:** **Accepted**
* **Context:** Flash sales require high throughput across distributed microservices (Reservation $\to$ Payment $\to$ Order $\to$ Fulfillment).
* **Decision:** Implement an **Asynchronous Orchestrated Saga** using Kafka domain events rather than synchronous distributed transactions.
* **Alternatives Considered:** Distributed 2PC / WS-AtomicTransaction.
* **Consequences & Trade-offs:** 2PC blocks locks across all services, severely degrading availability. Saga guarantees high availability through compensating transactions (e.g. `ReleaseInventory` on payment failure) at the cost of temporary eventual consistency.

---

### ADR-004: Transactional Outbox Pattern vs. Dual Writes
* **Status:** **Accepted**
* **Context:** Writing to PostgreSQL and publishing to Kafka simultaneously in application code causes partial failures ("dual-write problem") where a DB commit succeeds but Kafka publish fails.
* **Decision:** Implement the **Transactional Outbox Pattern** with Debezium CDC to read Postgres WAL logs and publish events to Kafka with at-least-once durability.
* **Alternatives Considered:** Direct inline REST calls, synchronous Kafka producer in web controller.
* **Consequences & Trade-offs:** Adds CDC infrastructure (Debezium/Kafka Connect), but completely guarantees zero lost messages.

---

### ADR-005: Hybrid Reservation TTL Expiry Engine
* **Status:** **Accepted**
* **Context:** If a user reserves stock and abandons checkout, the item must be released back to the flash sale in exactly 10 minutes (600s).
* **Decision:** Use a **Hybrid Expiry Architecture**: Redis Key Expiry notifications provide sub-second reactive release, while a background PostgreSQL batch worker running `SELECT ... FOR UPDATE SKIP LOCKED` runs every 30 seconds as a failsafe sweeper.
* **Alternatives Considered:** RabbitMQ TTL with dead-letter routing, pure cron polling.
* **Consequences & Trade-offs:** Requires maintaining dual expiry channels, but eliminates any single point of failure for stock leaks.
