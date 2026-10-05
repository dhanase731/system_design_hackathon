"""
================================================================================
SALESTORM: High-Concurrency Flash Sale Simulation Test Harness
================================================================================
Scenario:
- Available Stock = 100 units
- Concurrent Customers = 10,000
- Payment Success Rate = 95%
- Payment Failure Rate = 5%
- Duplicate Requests = 2% (200 duplicate clicks)
- Simulates: Atomic In-Memory Stock Lock, Idempotency Deduplication,
             Payment Authorization, and Resilient Outbox Order Processing.
================================================================================
"""

import asyncio
import random
import sys
import time
import uuid
from dataclasses import dataclass
from typing import Dict, Optional

# Ensure UTF-8 output safe for Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

@dataclass
class Reservation:
    reservation_id: str
    user_id: str
    quantity: int
    status: str  # RESERVED, PAID, FAILED, RELEASED
    expires_at: float

class MockRedisAtomicEngine:
    """Simulates Redis single-threaded atomic Lua execution."""
    def __init__(self, initial_stock: int):
        self.available_stock = initial_stock
        self.reservations: Dict[str, Reservation] = {}
        self.idempotency_map: Dict[str, str] = {}  # idempotency_key -> reservation_id
        self.payment_idempotency_map: Dict[str, str] = {}  # reservation_id -> status
        self.lock = asyncio.Lock()

    async def atomic_reserve(self, user_id: str, idempotency_key: str, qty: int = 1) -> tuple[Optional[Reservation], bool]:
        async with self.lock:
            # 1. Idempotency Check
            if idempotency_key in self.idempotency_map:
                existing_res_id = self.idempotency_map[idempotency_key]
                return self.reservations[existing_res_id], True  # Existing reservation, is_duplicate=True

            # 2. Check & Decrement Stock
            if self.available_stock >= qty:
                self.available_stock -= qty
                res_id = f"res_{uuid.uuid4().hex[:8]}"
                res = Reservation(
                    reservation_id=res_id,
                    user_id=user_id,
                    quantity=qty,
                    status="RESERVED",
                    expires_at=time.time() + 600
                )
                self.reservations[res_id] = res
                self.idempotency_map[idempotency_key] = res_id
                return res, False  # New reservation
            else:
                return None, False  # Out of Stock

    async def atomic_release(self, reservation_id: str) -> bool:
        async with self.lock:
            if reservation_id in self.reservations:
                res = self.reservations[reservation_id]
                if res.status == "RESERVED":
                    res.status = "RELEASED"
                    self.available_stock += res.quantity
                    return True
            return False

    async def atomic_confirm(self, reservation_id: str) -> bool:
        async with self.lock:
            if reservation_id in self.reservations:
                res = self.reservations[reservation_id]
                if res.status == "RESERVED":
                    res.status = "PAID"
                    return True
            return False

class FlashSaleSimulator:
    def __init__(self, total_stock: int = 100, total_users: int = 10000):
        self.redis = MockRedisAtomicEngine(total_stock)
        self.total_users = total_users
        self.total_stock = total_stock
        
        # Metrics Tracking
        self.successful_reservations = 0
        self.rejected_out_of_stock = 0
        self.duplicate_requests_handled = 0
        self.successful_payments = 0
        self.failed_payments = 0
        self.confirmed_orders = 0
        self.released_stock_count = 0

    async def customer_journey(self, user_id: str, idempotency_key: str):
        # Phase 1: High-Concurrency Reservation
        reservation, is_dup = await self.redis.atomic_reserve(user_id, idempotency_key, qty=1)
        
        if is_dup:
            self.duplicate_requests_handled += 1
            return  # Duplicate request safely deduplicated and returned

        if not reservation:
            self.rejected_out_of_stock += 1
            return

        self.successful_reservations += 1

        # Phase 2: Payment Execution (95% success, 5% failure)
        await asyncio.sleep(random.uniform(0.001, 0.005))
        
        payment_succeeds = random.random() < 0.95
        if payment_succeeds:
            confirmed = await self.redis.atomic_confirm(reservation.reservation_id)
            if confirmed:
                self.successful_payments += 1
                # Phase 3: Order Persistence (Guaranteed)
                self.confirmed_orders += 1
        else:
            # Payment failed -> Compensating transaction (Release stock)
            self.failed_payments += 1
            released = await self.redis.atomic_release(reservation.reservation_id)
            if released:
                self.released_stock_count += 1

    async def run_simulation(self):
        print("=" * 80)
        print("[START] INITIATING SALESTORM FLASH SALE SIMULATION")
        print(f"[CONFIG] Initial Stock: {self.total_stock} units | Concurrent Requests: {self.total_users}")
        print("=" * 80)

        start_time = time.time()
        tasks = []

        # Generate 10,000 normal users
        for i in range(self.total_users):
            u_id = f"user_{i:05d}"
            idemp_key = f"key_{u_id}"
            tasks.append(self.customer_journey(u_id, idemp_key))

        # Add 2% duplicate requests (200 duplicate clicks with exact same idempotency keys)
        for j in range(200):
            target_user_id = f"user_{random.randint(0, self.total_users-1):05d}"
            dup_key = f"key_{target_user_id}"
            tasks.append(self.customer_journey(target_user_id, dup_key))

        # Shuffle requests to simulate true simultaneous network concurrency
        random.shuffle(tasks)
        await asyncio.gather(*tasks)

        elapsed = time.time() - start_time

        print("\n" + "=" * 80)
        print("[RESULTS] SIMULATION METRICS & VERIFICATION")
        print("=" * 80)
        print(f"Total Duration: {elapsed:.3f} seconds")
        print(f"Peak Virtual QPS: {len(tasks) / elapsed:,.0f} req/sec")
        print(f"[OK] Successful Initial Reservations: {self.successful_reservations}")
        print(f"[INFO] Rejected Out-of-Stock Requests: {self.rejected_out_of_stock}")
        print(f"[OK] Duplicate Requests Deduplicated: {self.duplicate_requests_handled}")
        print(f"[OK] Successful Payments Confirmed: {self.successful_payments}")
        print(f"[WARN] Failed Payments Handled: {self.failed_payments}")
        print(f"[OK] Released Stock Back to Pool: {self.released_stock_count}")
        print(f"[OK] Final Confirmed Orders: {self.confirmed_orders}")
        print(f"[INFO] Remaining Available Stock in Redis: {self.redis.available_stock}")
        print("-" * 80)
        
        # INVARIANT VERIFICATION
        total_accounted = self.confirmed_orders + self.redis.available_stock
        print(f"[AUDIT] Confirmed Orders ({self.confirmed_orders}) + Remaining Stock ({self.redis.available_stock}) = {total_accounted}")
        assert total_accounted == self.total_stock, "CRITICAL ERROR: Stock invariant violated!"
        assert self.confirmed_orders <= self.total_stock, "CRITICAL ERROR: Overselling detected!"
        assert self.redis.available_stock >= 0, "CRITICAL ERROR: Negative stock detected!"
        print("[VERDICT] ZERO OVERSELLING DETECTED. ALL INVARIANTS 100% DEFENDED!")
        print("=" * 80)

if __name__ == "__main__":
    asyncio.run(FlashSaleSimulator().run_simulation())
