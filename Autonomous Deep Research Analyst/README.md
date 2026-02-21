# 🔬 Autonomous Deep Research Analyst

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![LangGraph](https://img.shields.io/badge/built%20with-LangGraph-orange.svg)](https://github.com/langchain-ai/langgraph)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

> **An autonomous multi-agent system that researches any topic, synthesises findings, and produces a polished HTML report — powered by LangGraph, Groq, and Tavily.**

<p align="center">
  <img src="docs/assets/demo_report.png" alt="Sample report screenshot" width="700">
</p>

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🎯 **Multi-Agent Orchestration** | LangGraph `Send()` API dispatches N research agents in parallel |
| 🔍 **Recursive Web Search** | Multi-round Tavily search with LLM-generated follow-up queries |
| 🧪 **Executive Synthesis** | Cross-section analysis with strategic recommendations |
| 📊 **Auto Charts** | Matplotlib bar/pie charts from structured `chart_data` |
| 📄 **Self-Contained HTML Reports** | Professional reports with base64-embedded images — zero dependencies to view |
| ⚡ **Resilient LLM Calls** | Exponential back-off retry + automatic model fallback on rate limits |
| ⚙️ **YAML Configuration** | All tuneable params in one file — models, retry, search depth, report settings |
| 🧩 **Modular Architecture** | Clean `src/` package layout — easy to extend, test, and maintain |

---

## 🏗️ Architecture

```
                        ┌─────────────────────────┐
                        │      User / CLI          │
                        └────────────┬────────────┘
                                     │
                                     ▼
                        ┌─────────────────────────┐
                        │     Orchestrator         │
                        │  (plan + Send() × N)     │
                        └─────┬──────┬──────┬─────┘
                              │      │      │
                    ┌─────────┘      │      └─────────┐
                    ▼                ▼                  ▼
           ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
           │ Research Agent│ │ Research Agent│ │ Research Agent│
           │ Market Trends │ │  Competitor  │ │     SWOT     │
           └──────┬───────┘ └──────┬───────┘ └──────┬───────┘
                  │                │                  │
                  │   Tavily Search + LLM Synthesis   │
                  └────────────┬───┴──────────────────┘
                               │  (operator.add)
                               ▼
                  ┌─────────────────────────┐
                  │     Synthesiser          │
                  │  Executive Summary       │
                  └────────────┬────────────┘
                               │
                               ▼
                  ┌─────────────────────────┐
                  │     Report Writer        │
                  │  HTML + Charts           │
                  └────────────┬────────────┘
                               │
                               ▼
                        reports/*.html
```

> See [docs/architecture.md](docs/architecture.md) for the full Mermaid diagram, node descriptions, data-flow, and resilience patterns.

---

## 📁 Project Structure

```
Autonomous Deep Research Analyst/
├── app.py                      # Main entry point (CLI / single-shot)
├── pyproject.toml              # Project metadata & dependencies
├── .env.example                # Template for API keys
├── .gitignore
├── configs/
│   └── settings.yaml           # All tuneable parameters
├── docs/
│   └── architecture.md         # Detailed architecture with Mermaid diagrams
├── reports/                    # Generated reports (git-ignored)
├── src/
│   ├── __init__.py             # Top-level convenience imports
│   ├── config.py               # YAML settings loader
│   ├── cli/
│   │   ├── __init__.py
│   │   └── interactive.py      # REPL + run_research()
│   ├── graph/
│   │   ├── __init__.py
│   │   └── builder.py          # StateGraph wiring + compile
│   ├── llm/
│   │   ├── __init__.py
│   │   └── provider.py         # get_llm() + llm_invoke() with retry
│   ├── models/
│   │   ├── __init__.py
│   │   ├── schemas.py          # SearchResult, AgentResult (Pydantic)
│   │   └── state.py            # ResearchState, SubAgentInput (TypedDict)
│   ├── nodes/
│   │   ├── __init__.py
│   │   ├── orchestrator.py     # Plan + Send() dispatcher
│   │   ├── research_agent.py   # Search → Synthesise → AgentResult
│   │   ├── synthesiser.py      # Executive summary
│   │   └── report_writer.py    # HTML report generation
│   ├── report/
│   │   ├── __init__.py
│   │   ├── charts.py           # Matplotlib chart generation
│   │   └── html_report.py      # HTML template + builder
│   └── search/
│       ├── __init__.py
│       └── tavily_client.py    # Recursive Tavily search
└── tests/
    ├── __init__.py
    └── test_core.py            # Import & compilation smoke tests
```

---

## 🚀 Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/<your-username>/deep-research-analyst.git
cd deep-research-analyst

python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate

pip install -e ".[dev]"
```

### 2. Configure API Keys

```bash
cp .env.example .env
# Edit .env and paste your keys:
#   GROQ_API_KEY=gsk_...
#   TAVILY_API_KEY=tvly-...
```

Get your free API keys:
- **Groq**: [console.groq.com](https://console.groq.com)
- **Tavily**: [app.tavily.com](https://app.tavily.com)

### 3. Run

```bash
# Interactive mode (REPL)
python app.py

# Single-shot
python app.py "Artificial Intelligence in Healthcare 2025"

# Or use the installed entry point
deep-research
```

### 4. View Report

Open the generated `reports/*.html` file in any browser — it's fully self-contained with embedded charts and styled content.

---

## ⚙️ Configuration

All settings live in [`configs/settings.yaml`](configs/settings.yaml):

| Section | Key | Default | Description |
|---------|-----|---------|-------------|
| `llm` | `provider` | `groq` | LLM provider (`groq` or `openai`) |
| `llm` | `primary_model` | `llama-3.3-70b-versatile` | Primary model |
| `llm` | `fallback_model` | `llama-3.1-8b-instant` | Fallback on rate-limit |
| `llm` | `temperature` | `0.4` | Sampling temperature |
| `retry` | `max_attempts` | `3` | Retries per model before fallback |
| `retry` | `base_delay_seconds` | `10` | Initial back-off delay |
| `search` | `max_results_per_query` | `5` | Hits per Tavily query |
| `search` | `search_depth` | `advanced` | `basic` or `advanced` |
| `search` | `max_search_rounds` | `3` | Recursive drill-down rounds |
| `agent` | `num_research_agents` | `3` | Parallel sub-agents |
| `report` | `output_dir` | `reports` | Output folder for HTML reports |

---

## 🧪 Testing

```bash
pytest tests/ -v
```

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| **Orchestration** | [LangGraph](https://github.com/langchain-ai/langgraph) (StateGraph, Send API) |
| **LLM** | [Groq](https://groq.com) (Llama 3.3 70B / Llama 3.1 8B) |
| **Web Search** | [Tavily](https://tavily.com) (recursive multi-round) |
| **Data Models** | [Pydantic v2](https://docs.pydantic.dev) |
| **Charts** | [Matplotlib](https://matplotlib.org) |
| **Reports** | Self-contained HTML via Python [markdown](https://python-markdown.github.io) |
| **Config** | YAML ([PyYAML](https://pyyaml.org)) |
| **Linting** | [Ruff](https://github.com/astral-sh/ruff) |

---

## 📝 How It Works

1. **Orchestrator** receives the topic and plans research sections (Market Trends, Competitor Analysis, SWOT Analysis by default).

2. **Parallel Dispatch** — LangGraph's `Send()` API fans out to N research agents simultaneously.

3. Each **Research Agent**:
   - Performs recursive multi-round Tavily web search
   - LLM generates follow-up queries for deeper drilling
   - Synthesises raw search hits into structured Markdown
   - Extracts optional `chart_data` for visualisation

4. **Synthesiser** receives all agent results (accumulated via `operator.add`) and produces a cross-cutting executive summary.

5. **Report Writer** generates Matplotlib charts, converts Markdown to HTML, embeds images as base64, and writes a self-contained `.html` report.

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgements

- [LangChain](https://github.com/langchain-ai/langchain) & [LangGraph](https://github.com/langchain-ai/langgraph) for the multi-agent orchestration framework
- [Groq](https://groq.com) for blazing-fast LLM inference
- [Tavily](https://tavily.com) for AI-optimised web search
