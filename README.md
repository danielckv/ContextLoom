# ContextLoom 🧶

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Redis](https://img.shields.io/badge/redis-%23DD0031.svg?&logo=redis&logoColor=white)](https://redis.io/)

**High-performance, persistence-layer agnostic memory context awareness for Multi-Agent Systems.**

ContextLoom is an open-source framework designed to decouple **Memory** from **Compute**. It creates a shared, persistent "Context State" residing in Redis that allows disparate LLM frameworks (DSPy, CrewAI, Agno, Google ADK) to share awareness, maintain continuity, and handle "Cold Start" data pulls from traditional databases.

<img width="949" height="552" alt="image" src="https://github.com/user-attachments/assets/0e408458-fd71-462e-b7a9-bb51e092c1c0" />

---

## 🚀 Why ContextLoom?

Building multi-agent systems often results in "amnesic" architectures where:
1.  **Context is siloed:** An agent in CrewAI doesn't know what a DSPy module just optimized.
2.  **Cold starts are hard:** Injecting historical customer data from Postgres into a fresh agent session is manual and brittle.
3.  **Cycles are broken:** Long-running conversation flows lose coherence as context windows fill up or sessions time out.

ContextLoom acts as the **cerebral cortex** for your agents—a centralized, high-speed memory store that persists the *state* of the conversation cycle, not just the logs.

## ✨ Key Features

* **⚡ Redis-First Architecture:** Leverages Redis for sub-millisecond context retrieval and state updates, ensuring agents don't lag.
* **🔌 Universal Connectors:** "Cold Start" your context by pulling initial state automatically from **PostgreSQL**, **MySQL**, or **MongoDB**.
* **🤝 Framework Agnostic:** Native wrappers for:
    * **DSPy** (Signatures & Modules)
    * **CrewAI** (Agent Memory & Task Output)
    * **Agno** (Workflow State)
    * **Google GenAI SDK (ADK)**
* **🔄 Cycle Management:** Intelligent handling of communication loops to prevent repetition and ensure goal progression.

---

## 🧠 The "Cycle" of Communication

ContextLoom introduces the concept of **Communication Cycles** to maintain smarter agents.

In standard LLM interactions, context is linear. In ContextLoom, context is **Cyclic and State-Aware**:

1.  **Ingest (Cold Start):** The framework hydrates the Redis session with relevant entities from your SQL/NoSQL source (e.g., User Profile, last 5 orders).
2.  **Interaction Phase:** Agents read the `GlobalContext`. A CrewAI researcher adds findings; a DSPy optimizer refines the prompt based on that finding.
3.  **State Snapshotting:** After every interaction turn, ContextLoom calculates a "Cycle Hash".
    * *Why this helps:* If an agent begins looping (repeating logic), ContextLoom detects the duplicate hash and flags the agent to pivot strategies.
4.  **Persistence:** The updated state is pushed back to Redis, ready for the next agent, even if that agent is running on a different server or framework.

## 🛠️ Installation

```bash
pip install contextloom
```

## 💻 Usage Example

1. Initialize with specific Backend

```python
from contextloom import Loom, PostgresConnector

# Connect to Redis (Memory) and Postgres (History)
loom = Loom(
    memory_backend="redis://localhost:6379",
    data_source=PostgresConnector("postgresql://user:pass@localhost:5432/mydb")
)
```

2. Hydrate & Run with DSPy

```python
import dspy

# Create a session ID
session_id = "user_123_cycle_4"

# Pull data from Postgres automatically into Redis Context
context = loom.hydrate(session_id, query="SELECT * FROM users WHERE id=123")

# DSPy Integration
class IntentClassifier(dspy.Signature):
    """Classify user intent based on Loom Context."""
    context_snapshot = dspy.InputField(desc="Current state from Redis")
    user_query = dspy.InputField()
    intent = dspy.OutputField()

# The agent is now "Aware" of the DB data without manual injection
result = dspy.Predict(IntentClassifier)(
    context_snapshot=context.get_current_state(), 
    user_query="Where is my order?"
)

# Update the Loom Cycle
loom.update_cycle(session_id, step="classification", data=result)
```

## Architecture
<img width="634" height="1652" alt="image" src="https://github.com/user-attachments/assets/d08d64fe-79e2-45ac-8dd3-29cc20f3f3c5" />
