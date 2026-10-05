# AI-Assisted Engineering & Usage Disclosure Note

## 1. Compliance Statement
In compliance with the **SALESTORM Hackathon Design-First AI Policy**, this document records all instances where AI tooling was utilized during the development of this system design blueprint and validation test harness.

---

## 2. Summary of AI Tools & Utilization

| Category | AI Tool Used | Scope of Work / Generated Artifact | Human Review & Validation Method |
|---|---|---|---|
| **Architecture Drafting** | Google Gemini 3.7 / Antigravity | Generating standard C4 Model Mermaid diagram syntax and Markdown templates. | Architect team verified all service boundaries, synchronous vs asynchronous paths, and transactional invariants. |
| **Schema & DDL Generation** | Google Gemini 3.7 / Antigravity | PostgreSQL DDL table skeletons, indexes, and CloudEvents JSON schemas. | Data Engineer reviewed primary/foreign keys, uniqueness constraints, and isolation levels. |
| **Simulation Scripting** | Google Gemini 3.7 / Antigravity | Python `asyncio` test harness (`flash_sale_simulation.py`) simulating 10,000 concurrent requests against 100 stock. | Executed and validated in local environment; debugged and verified zero overselling and idempotency assertions. |

---

## 3. What AI Did NOT Replace
* **Core Architecture Reasoning:** System boundaries, two-phase atomic reservation via Redis Lua, and asynchronous Saga compensation were conceptualized and defended by the engineering team.
* **Concurrency & Consistency Guarantees:** Mathematical proofs and invariant audits ($\text{Confirmed Orders} + \text{Remaining Stock} = 100$) were designed to address the specific flash sale bottleneck.
* **Failure Defense & Trade-Offs:** The team evaluated and justified SQL vs. NoSQL, Redis Lua vs. DB row locking, and Outbox CDC vs. dual-write architectures.

---

## 4. Key Prompt Summaries

1. *"Draft PostgreSQL DDL schema for flash sale inventory with optimistic locking version column and unique idempotency keys."*
2. *"Generate Python asyncio script to simulate 10,000 concurrent purchase attempts competing for 100 inventory items, simulating 95% payment success, 5% payment failure with stock release, and 2% duplicate idempotency requests."*
3. *"Format C4 Component and Sequence diagrams using Mermaid syntax."*
