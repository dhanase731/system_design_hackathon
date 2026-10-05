# 13. Scalability Architecture & 50x Surge Playbook

## 1. Multi-Tier Scaling Strategy

```mermaid
flowchart TD
    subgraph Tier1 [1. Edge Tier: 500,000 QPS]
        CDN[CDN Edge Caching] --> WAF[WAF DDoS & Bot Filtering]
    end

    subgraph Tier2 [2. Compute Tier: 50,000 QPS Ingress]
        ALB[Application Load Balancers] --> HPA[Kubernetes HPA Auto-scaler\n(10 -> 60 Pods via CPU/Queue Depth)]
    end

    subgraph Tier3 [3. In-Memory Tier: 80,000 QPS]
        RedisPrimary[(Redis Sharded Cluster\nPrimary-Replica Master)]
    end

    subgraph Tier4 [4. Async Queue Tier]
        Kafka[(Kafka Distributed Partitions)]
    end

    subgraph Tier5 [5. Storage Tier: 2,500 Writes/sec]
        PgBouncer[PgBouncer Connection Pooler] --> PostgresPrimary[(PostgreSQL Primary)]
        PostgresPrimary --> PostgresReplica[(PostgreSQL Read Replicas)]
    end

    WAF --> ALB
    HPA --> RedisPrimary
    HPA --> Kafka
    Kafka --> PgBouncer
```

---

## 2. Horizontal Scaling Mechanisms

### 2.1 Kubernetes Horizontal Pod Autoscaler (HPA)
Microservices scale horizontally using a dual metric policy:
1. **CPU / Memory Threshold:** Scale out when average pod CPU $> 65\%$.
2. **Custom Kafka Lag Metric:** Scale consumer worker pods when Kafka topic lag exceeds 5,000 unread messages.

### 2.2 Database Scaling & Connection Pooling (PgBouncer)
* Direct connections to PostgreSQL are capped at 500 max connections.
* **PgBouncer** operates in `Transaction Pooling` mode, allowing 5,000+ stateless worker threads to share 150 physical database server connections with zero connection handshake latency.
* **Read-Write Splitting:** All `SELECT` queries for product browsing and order history route to read replicas; only financial commits touch the Primary master.

---

## 3. Flash Sale 50x Traffic Spike Playbook

When traffic spikes from $10,000\text{ QPS}$ to $500,000\text{ QPS}$ at $T_0$:

```mermaid
sequenceDiagram
    autonumber
    Note over CDN: 1. CDN Edge turns on Stale-While-Revalidate caching for static catalog (95% offloaded)
    Note over API GW: 2. Token Bucket Rate Limiting throttles aggressive bot IPs (>50 req/sec)
    Note over Redis: 3. In-memory Atomic Lua handles all 10,000 Buy Now hits in 12 milliseconds
    Note over Redis: 4. Item 100 sold; Redis flips flag `prod_1001:sold_out = true`
    Note over API GW: 5. Subsequent 490,000 requests are rejected immediately at Gateway with HTTP 409 (Zero DB impact)
```

1. **Pre-Warming:** Redis cluster keys and CDN edges are pre-warmed 15 minutes before the sale begins.
2. **Edge Rejection:** Once stock hits 0 in Redis, a lightweight distributed flag broadcast turns on fast-rejection at the API Gateway level, protecting all internal services from processing fruitless checkout requests.
3. **Queue Asynchronous Buffering:** Payment confirmations are ingested into Kafka at burst speed and drained to the database at a controlled, sustainable rate.
