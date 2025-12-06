# ContextLoom Agent Definitions

This project defines specific "Connector Agents" that interface with external LLM frameworks.

## 1. The DSPy Adapter
* **Role:** Intercepts DSPy `forward` calls.
* **Input:** Receives a DSPy Signature.
* **Output:** Injects `context_snapshot` into the signature inputs.

## 2. The CrewAI Memory Handler
* **Role:** Overrides standard CrewAI memory.
* **Behavior:** Instead of saving to local JSON, it pushes "Task Output" to the Redis `dynamic_state` key.

## 3. The Cycle Watchdog
* **Role:** Background logic.
* **Behavior:** Monitors state updates. If `CycleDetectedError` is raised, it modifies the system prompt to force a strategy pivot.
