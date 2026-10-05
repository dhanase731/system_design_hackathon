# 12. Capacity Planning & Quantitative Estimation

## 1. Traffic & Throughput Model

| Parameter | Baseline / Normal Traffic | Flash Sale Peak Traffic | Peak Multiplier |
|---|---|---|---|
| **Read Requests (Catalog Browse)** | $8,000\text{ QPS}$ | **$450,000\text{ QPS}$** | $56.2\times$ |
| **Write Requests (Cart / Reserve / Buy)** | $2,000\text{ QPS}$ | **$50,000\text{ QPS}$** | $25\times$ |
| **Total System Throughput** | $10,000\text{ QPS}$ | **$500,000\text{ QPS}$** | $50\times$ |

---

## 2. Bandwidth & Network Calculations

* **Average Catalog Page Payload:** $100\text{ KB}$ (JSON + image metadata).
* **Read Bandwidth (Origin offloaded by CDN at 95% hit ratio):**
  $$\text{Origin Peak Read Bandwidth} = 450,000 \times 100\text{ KB} \times (1 - 0.95) = 2,250,000\text{ KB/s} \approx 2.25\text{ GB/s} = 18\text{ Gbps}$$
* **Write Payload Size (Reservation / Checkout):** $2\text{ KB}$ per request.
  $$\text{Peak Ingress Write Bandwidth} = 50,000 \times 2\text{ KB} = 100,000\text{ KB/s} = 100\text{ MB/s} = 800\text{ Mbps}$$

---

## 3. In-Memory Cache (Redis) RAM Sizing

* **Flash Sale Items:** 10,000 active SKUs on sale.
* **Metadata per Product:** $1\text{ KB}$.
* **Active Concurrent Reservations:** 50,000 in-flight reservations at peak.
* **Reservation Record Size:** $500\text{ Bytes}$ (User ID, Timestamp, TTL token).
* **Calculations:**
  * Catalog Cache: $10,000 \times 1\text{ KB} = 10\text{ MB}$.
  * Reservation Hash Maps & TTL Keys: $50,000 \times 500\text{ Bytes} \times 2 = 50\text{ MB}$.
  * Idempotency Deduplication Keys (1 hr retention): $500,000 \times 200\text{ Bytes} = 100\text{ MB}$.
  * Total Working Set: $< 500\text{ MB}$.
* **Cluster Provisioning:** Provision a **3-node Primary + 3-node Replica Redis Cluster (AWS `cache.r6g.xlarge` with 26 GB RAM each)**, providing 99.99% memory headroom and $>250,000\text{ OPS}$ per node.

---

## 4. Database (PostgreSQL) Storage & IOPS Sizing

* **Order Record Size:** $1.5\text{ KB}$ (Order, Items, Addresses).
* **Orders Per Day (Normal):** $2,000,000\text{ orders/day}$.
* **Flash Sale Confirmed Orders:** $100\text{ units per flash sale}$, up to $50,000\text{ orders/day}$ overall.
* **Annual Storage Growth:**
  $$\text{Annual DB Volume} = 2,000,000 \times 365 \times 1.5\text{ KB} \approx 1.095\text{ TB/year}$$
* **IOPS Requirement:**
  * Peak Write IOPS handled via Kafka queue buffering: Peak DB writes smoothed to $2,500\text{ writes/sec}$.
  * Provision AWS RDS PostgreSQL with **10,000 Provisioned IOPS (gp3/io2)** and 3 Read Replicas.

---

## 5. Summary Hardware Provisioning Bill of Materials

| Tier | Technology | Instances / Sizing | Target Capacity |
|---|---|---|---|
| **Edge / CDN** | Cloudflare Enterprise | Global Anycast | $500,000\text{ QPS}$ (95% cache hit) |
| **API Gateway** | Kong Gateway | 8 Nodes (4 vCPU, 8 GB RAM) | $65,000\text{ QPS}$ origin throughput |
| **Microservices** | EKS Kubernetes Pods | 30 Pods per Core Service | Autoscales from 10 to 60 Pods |
| **In-Memory Cache**| Redis Cluster | 6 Nodes (3 Primary, 3 Replica) | $> 500,000\text{ ops/sec}$ |
| **Message Broker**| Apache Kafka | 5 Broker Nodes (i3en.xlarge) | $150,000\text{ msgs/sec}$ write throughput |
| **Database** | Aurora PostgreSQL | 1 Primary (r6g.2xlarge) + 3 Replicas | $15,000\text{ Read QPS}, 3,000\text{ Write QPS}$ |
