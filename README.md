# machine-learning-and-gen-ai
Repository for my experiments with machine learning and AI

---

## 📂 Projects

### 🏗️ [Self-Correcting Multi-Agent SQL System](Self%20Correction%20Multi%20Agent%20System/README.md)

A **production-ready**, self-correcting SQL agent built with **LangGraph**, **LangChain**, and **SQLAlchemy 2.x**.

Ask questions in **natural language** → the agent generates SQL, executes it, validates the results, and auto-corrects on failure — all through a multi-node state machine with human-in-the-loop approval for sensitive queries.

**Key Features:**

| Feature | Description |
|---------|-------------|
| 🧠 LLM-powered SQL generation | Natural language → SQL via Groq / OpenAI (`llama-3.3-70b-versatile`) |
| 🔁 Self-correction loop | Debugger analyses failures, rewrites SQL, retries up to 3× |
| ✅ Two-stage validation | Quick programmatic checks + LLM semantic validation |
| ⚠️ Human approval gate | Sensitive DML/DDL queries require explicit user consent |
| 📦 LRU query cache | SHA-256 keyed, 100 MB memory-bounded, auto-evicting |
| 🗄️ Multi-dialect support | MySQL, PostgreSQL, SQLite, SQL Server, Oracle |
| 🖥️ Streamlit UI | Web interface with DB selector, tabular results, cache stats |
| 💬 Interactive CLI | REPL with `cache` stats and `q` to quit |

**Tech stack:** Python · LangGraph · LangChain · Groq · Pydantic 2 · SQLAlchemy 2.x · Streamlit

👉 [View full README & architecture diagram →](Self%20Correction%20Multi%20Agent%20System/README.md)

---

### 📄 [Document Parser](document-parser/README.md)

An LLM-based Word document content extractor.
