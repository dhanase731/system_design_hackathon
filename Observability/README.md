# 16. Observability, Telemetry & Real-Time Alerting

## 1. Observability Architecture (Metrics, Logs, Traces)

```mermaid
flowchart LR
    subgraph Microservices [Microservice Fleet]
        Svc1[Reservation Service]
        Svc2[Payment Service]
        Svc3[Order Service]
    end

    subgraph Telemetry_Pipelines [Telemetry Ingestion]
        OTel[OpenTelemetry Collector]
        Prom[Prometheus Time-Series DB]
        Loki[Grafana Loki / Elasticsearch]
    end

    subgraph Visualization_Alerts [Monitoring & Operations]
        Grafana[Grafana Unified Dashboards]
        PagerDuty[PagerDuty On-Call Alerts]
    end

    Svc1 & Svc2 & Svc3 -->|Push Traces: OTLP/gRPC| OTel
    Svc1 & Svc2 & Svc3 -->|Expose /metrics: Prometheus| Prom
    Svc1 & Svc2 & Svc3 -->|Structured JSON Logs: FluentBit| Loki

    OTel --> Grafana
    Prom --> Grafana
    Loki --> Grafana

    Prom -->|Threshold Breached| PagerDuty
```

---

## 2. Service Level Objectives (SLOs) & Golden Signals

| Golden Signal | Metric Name | Target SLO | Warning Alert Threshold | Critical Alert Threshold |
|---|---|---|---|---|
| **Latency** | `http_request_duration_seconds{quantile="0.99"}` | $< 100\text{ms}$ | $> 150\text{ms}$ for 2m | $> 300\text{ms}$ for 1m |
| **Traffic** | `http_requests_total` | $500,000\text{ QPS}$ | Rate drop $> 50\%$ | Sudden drop $> 90\%$ |
| **Errors** | `http_requests_5xx_ratio` | $< 0.05\%$ | $> 1\%$ for 1m | $> 5\%$ for 30s |
| **Saturation** | `container_cpu_utilization` | $< 70\%$ | $> 75\%$ | $> 90\%$ (Triggers HPA) |
| **Kafka Lag** | `kafka_consumergroup_lag` | $< 1,000\text{ msgs}$ | $> 5,000\text{ msgs}$ | $> 20,000\text{ msgs}$ |
| **Inventory Invariant** | `inventory_consistency_check_violations` | **Strictly 0** | $> 0$ (Immediate SEV-1) | $> 0$ (Automatic Safe-Halt) |

---

## 3. Distributed Tracing Flow with OpenTelemetry

Every user request is tagged with an immutable `X-Correlation-ID` injected at the Edge:

```mermaid
sequenceDiagram
    autonumber
    participant Client
    participant GW as API Gateway [Trace: tr_101]
    participant Resv as Reservation Svc [Span: sp_resv]
    participant Redis as Redis [Span: sp_redis]
    participant Kafka as Kafka [Span: sp_kafka]
    participant Pay as Payment Svc [Span: sp_pay]

    Client->>GW: POST /reservations (Trace-ID: tr_101)
    GW->>Resv: Forward with Trace-Context (tr_101, span_parent: sp_gw)
    Resv->>Redis: Lua atomic decrement (Span: sp_redis, Duration: 2.1ms)
    Resv->>Kafka: Inject trace into Kafka headers (Span: sp_kafka)
    Kafka->>Pay: Propagate trace context to payment processor
```

---

## 4. Structured JSON Logging Contract

```json
{
  "@timestamp": "2026-10-05T12:00:01.450Z",
  "level": "INFO",
  "service": "salestorm-payment-service",
  "trace_id": "tr_101a88b901",
  "span_id": "sp_pay_3321",
  "event": "PAYMENT_CAPTURED",
  "user_id": "usr_550291",
  "reservation_id": "res_88291a-f732-4d11-82e1",
  "amount": 499.99,
  "currency": "USD",
  "duration_ms": 312.4,
  "gateway_response_code": "200_OK"
}
```
