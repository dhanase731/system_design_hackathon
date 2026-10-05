# 08. REST API Specifications & Error Protocols

## 1. Global Request Headers & Contract Conventions

Every transactional request to the SALESTORM API Gateway must supply standard observability, authentication, and idempotency headers:

| Header Name | Type | Description | Mandatory |
|---|---|---|---|
| `Authorization` | String | `Bearer <JWT_TOKEN>` for authenticated user context. | Yes |
| `Idempotency-Key` | UUID v4 | Client-generated unique UUID to prevent double operations on network retries. | **Yes (for all POST/PUT)** |
| `X-Correlation-ID` | UUID v4 | Distributed tracing ID propagated across all microservices & logs. | Yes |
| `Content-Type` | String | `application/json` | Yes |

---

## 2. API Endpoints

### 2.1 Reserve Inventory (`POST /api/v1/reservations`)
* **Purpose:** Atomically holds 1 or more items during flash sale with a 10-minute TTL.
* **Rate Limit:** 5 requests / second / user.

**Request Payload:**
```json
{
  "product_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "quantity": 1
}
```

**Response: 201 Created (Success)**
```json
{
  "status": "SUCCESS",
  "data": {
    "reservation_id": "res_88291a-f732-4d11-82e1",
    "product_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
    "quantity": 1,
    "status": "RESERVED",
    "expires_at": "2026-10-05T12:10:00Z",
    "ttl_seconds": 600
  },
  "message": "Stock reserved successfully. Please complete payment within 10 minutes."
}
```

**Response: 409 Conflict (Flash Sale Sold Out)**
```json
{
  "status": "ERROR",
  "error_code": "INVENTORY_OUT_OF_STOCK",
  "message": "The requested item is currently sold out.",
  "timestamp": "2026-10-05T12:00:01Z"
}
```

---

### 2.2 Execute Payment (`POST /api/v1/payments`)
* **Purpose:** Processes payment for a valid, unexpired reservation.

**Request Payload:**
```json
{
  "reservation_id": "res_88291a-f732-4d11-82e1",
  "payment_method": "STRIPE",
  "payment_token": "tok_1Nq8XYZVisa4242",
  "amount": 499.99,
  "currency": "USD"
}
```

**Response: 200 OK (Payment Confirmed)**
```json
{
  "status": "SUCCESS",
  "data": {
    "payment_id": "pay_30291a92",
    "reservation_id": "res_88291a-f732-4d11-82e1",
    "status": "SUCCESS",
    "gateway_txn_id": "ch_3Nq8XYZ89213",
    "order_status": "CONFIRMED"
  },
  "message": "Payment captured. Order is being processed."
}
```

**Response: 402 Payment Required (Card Declined)**
```json
{
  "status": "ERROR",
  "error_code": "PAYMENT_DECLINED",
  "message": "Your card was declined by the issuing bank. Reservation has been released.",
  "timestamp": "2026-10-05T12:01:15Z"
}
```

---

### 2.3 Order Status Query (`GET /api/v1/orders/{order_id}`)

**Response: 200 OK**
```json
{
  "status": "SUCCESS",
  "data": {
    "order_id": "ord_77189a01",
    "user_id": "usr_550291",
    "status": "CONFIRMED",
    "total_amount": 499.99,
    "items": [
      {
        "product_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
        "title": "SALESTORM Ultra Edition",
        "quantity": 1,
        "price": 499.99
      }
    ],
    "tracking_number": "TRK-FEDEX-992819",
    "created_at": "2026-10-05T12:00:30Z"
  }
}
```

---

## 3. Standard HTTP Error Code Taxonomy

| HTTP Code | Error Code Constant | Cause | Client Action |
|---|---|---|---|
| `400 Bad Request` | `INVALID_INPUT` | Missing required fields or schema violation. | Fix payload and retry. |
| `401 Unauthorized` | `UNAUTHORIZED` | Expired / Invalid JWT Token. | Re-authenticate. |
| `402 Payment Required` | `PAYMENT_DECLINED` | Insufficient funds or fraud block. | Use another payment method. |
| `409 Conflict` | `INVENTORY_OUT_OF_STOCK` | Available inventory is 0. | Display "Sold Out" UI. |
| `409 Conflict` | `RESERVATION_EXPIRED` | 10-minute hold timer expired before payment. | Start new purchase flow. |
| `429 Too Many Requests`| `RATE_LIMIT_EXCEEDED` | Request rate breached (>100 req/min). | Wait for `Retry-After` seconds. |
| `503 Service Unavailable` | `CIRCUIT_BREAKER_OPEN` | External PSP experiencing downtime. | Fall back to alternative payment provider. |
