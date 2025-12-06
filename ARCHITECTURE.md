# ContextLoom Architecture Specification

## 1. System Identity
ContextLoom is a state-management middleware that decouples **Memory (Redis)** from **Compute (LLM Agents)**. It allows frameworks like DSPy, CrewAI, and Agno to share a unified context.

## 2. Core Design Patterns (Strict Enforcement)
* **Repository Pattern:** All database interactions (Postgres/Mongo) must go through `connectors/` abstractions.
* **Singleton Pattern:** The `RedisManager` must be a singleton to manage connection pools efficiently.
* **Factory Pattern:** Use `ConnectorFactory` to instantiate the correct database connector based on the connection string.
* **Async First:** All I/O operations must use `asyncio`. No blocking calls allowed.

## 3. Tech Stack Constraints
* **Python:** 3.11+
* **Type Hinting:** Strict `typing` required.
* **Style:** Google Docstrings for all methods.
* **Libraries:** `pydantic` (Schema), `redis` (Async), `sqlalchemy` (Async), `motor` (Mongo Async).

## 4. Smart Feature Requirements
### A. The "Cycle Hash" (Loop Detection)
The system must prevent agents from looping.
- **Logic:** Compute a SHA256 hash of the `dynamic_state` at every turn.
- **Storage:** Store the last 5 hashes in a Redis List (`Loom:CycleHistory:{session_id}`).
- **Action:** If a new state matches a recent hash, raise `CycleDetectedError`.

### B. "Cold Start" Hydration
- Agents should not query SQL directly.
- On initialization, `Loom` checks if Redis is empty.
- If empty, it triggers `connector.fetch_context(entity_id)` and populates Redis.

### C. The "ContextLoom" Object
The main entry point must be intuitive:
```python
loom = ContextLoom(memory="redis://...", storage="postgres://...")
context = await loom.sync(session_id="user_123")
```
