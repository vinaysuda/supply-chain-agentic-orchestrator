# Enterprise Supply Chain Agentic Orchestrator

A production-ready, multi-agent AI system designed to autonomously ingest, assess, and mitigate supply chain disruptions. 

This system uses a **CrewAI** pod for deep cognitive reasoning (analyzing contracts, SLAs, and risk impacts) and relies on **LangGraph** as a deterministic, stateful orchestrator to handle routing, human-in-the-loop governance, and immutable audit logging.

---

## 🏢 Business Context

Modern supply chains generate thousands of telemetry events daily, ranging from minor EDI ping timeouts to critical metallurgical stress test failures. Human operators suffer from alert fatigue, often missing critical disruptions buried in the noise.

This system acts as a **Level-1 and Level-2 autonomous triage unit**:

1. **The Gateway (Noise Reduction):** A LangGraph Supervisor instantly analyzes incoming telemetry. If it identifies standard system noise, it resolves the ticket autonomously, saving human bandwidth.
2. **The Investigation Pod (Risk Assessment):** For valid anomalies, a multi-agent CrewAI pod is deployed. A *Supplier Data Analyst* decodes the raw logs to find the root cause, while an *Enterprise Risk Mitigation Specialist* calculates the global financial severity and SLA consequences.
3. **The Governance Boundary (Execution):** The AI drafts a mitigation strategy (e.g., "Halt Production") but is strictly prevented from executing external API calls to the ERP system until a human operator reviews and approves the immutable audit trail.

---

### System Flow Diagram

```mermaid
graph TD
    %% Nodes
    Ingest[Manufacturing Telemetry Ingestion]
    Supervisor{Supervisor Node<br/>LangGraph}
    EndNoise[Drop: Classified as Noise]

    subgraph CrewAI_Pod [CrewAI Reasoning Pod]
        Analyst(Data Analyst Agent)
        Scout(Risk Mitigation Agent)
        Analyst <--> Scout
    end

    Draft[Draft Escalation Node<br/>LangGraph]
    Gate{Governance Checkpoint<br/>Human-in-the-Loop}
    Archive[Archive State & Log]
    Execute[Execute Escalation<br/>Azure Service Bus / ERP API]

    %% Routing
    Ingest --> Supervisor
    Supervisor -->|Invalid/Noise| EndNoise
    Supervisor -->|Valid Anomaly| CrewAI_Pod

    CrewAI_Pod -->|Pydantic RiskAssessment Schema| Draft

    Draft -.->|interrupt_before| Gate
    Gate -->|Reject| Archive
    Gate -->|Approve| Execute

    %% Styling
    classDef lgNode fill:#2d3748,stroke:#4a5568,stroke-width:2px,color:#fff
    classDef aiNode fill:#2b6cb0,stroke:#3182ce,stroke-width:2px,color:#fff
    classDef human fill:#c53030,stroke:#e53e3e,stroke-width:2px,color:#fff

    class Ingest,Supervisor,Draft,EndNoise,Archive,Execute lgNode
    class CrewAI_Pod,Analyst,Scout aiNode
    class Gate human
```



---

## 🛡️ Enterprise Governance Features

This system was built with strict "zero-trust" AI principles:

- **Human-in-the-Loop (HITL) Boundary:** Utilizing LangGraph's `interrupt_before=["execute"]` mechanics, the AI can reason and draft actions, but the system forcibly pauses and yields terminal control to a human before invoking the `erp_mock.py` integration.
- **Immutable Audit Logging:** Powered by `PostgresSaver`, every node transition, LLM response, and state mutation is permanently serialized to a physical PostgreSQL database, tagged by a unique `thread_id` tied to the specific supply chain event.
- **Provider-Agnostic Failover:** Dynamic configuration toggles allow seamless switching between standard OpenAI (`gpt-4o`), Google Gemini (`gemini-2.5-flash-lite`), and Enterprise Azure OpenAI to prevent vendor lock-in and ensure uptime.
- **Strict Output Enforcement:** Raw LLM strings are strictly forbidden. All state data is cast directly into rigorous Pydantic V2 schemas (`TelemetryEvent`, `RiskAssessment`, `EscalationAction`) ensuring downstream systems never receive hallucinated keys.

---

## 🏗️ Tech Stack

- **Language:** Python 3.12+ (Strictly Typed)
- **Orchestration & State:** LangGraph
- **Cognitive Pods:** CrewAI
- **Persistence:** PostgreSQL via LangGraph PostgresSaver (Dockerized)
- **Observability:** LangSmith
- **Validation:** Pydantic V2
- **Static Typing:** `mypy` (Strict Mode)
- **Testing:** `pytest` (with class-level monkeypatching)
- **Package Manager:** `uv`

---

## 📂 Project Structure

```text
supply-chain-agentic-orchestrator/
├── data/
│   └── mock_telemetry_main.json   # Batch event payloads (Quality failures, Delays, EDI Noise)
├── src/
│   ├── agents/
│   │   ├── crews/
│   │   │   └── risk_investigator.py # CrewAI multi-agent pod logic
│   │   └── nodes/
│   │       ├── escalation.py        # LangGraph action drafting & execution nodes
│   │       └── supervisor.py        # LangGraph routing gateway
│   ├── core/
│   │   └── config.py              # Centralized settings & fail-fast validation
│   ├── schemas/
│   │   └── telemetry.py           # Strictly typed Pydantic data models
│   ├── state/
│   │   └── graph_state.py         # The TypedDict LangGraph State schema
│   ├── tools/
│   │   └── erp_mock.py            # Simulated SAP/Oracle integration logic
│   └── main.py                    # Core graph compilation and batch processing loop
├── tests/
│   ├── __init__.py
│   └── test_config.py             # Import-time mocking and provider toggle tests
├── .env                           # API keys, LangSmith, & DB URIs (Git-ignored)
├── .gitignore                     # Security boundaries
├── docker-compose.yml             # PostgreSQL Infrastructure-as-Code
├── pyproject.toml                 # uv dependencies
└── README.md
```

---

## 🚀 Quickstart Guide

### 1. Prerequisites

- Install [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- Install [uv](https://github.com/astral-sh/uv) (The fast Python package manager)

### 2. Environment Setup

Create a `.env` file at the root of the project. Leave only **ONE** of the three LLM provider blocks populated to control the toggle:

```env
# --- OPTION 1: Public OpenAI ---
# OPENAI_API_KEY=""

# --- OPTION 2: Google Gemini ---
GEMINI_API_KEY=""

# --- OPTION 3: Enterprise Azure OpenAI ---
# AZURE_OPENAI_API_KEY=""
# AZURE_OPENAI_ENDPOINT="[https://your-resource-name.openai.azure.com/](https://your-resource-name.openai.azure.com/)"
# AZURE_OPENAI_API_VERSION="2024-02-01"
# AZURE_OPENAI_CHAT_DEPLOYMENT_NAME="gpt-4o" # Or whatever you named your deployment in Azure

# LangSmith Observability (The "40% reduction in debugging cycles")
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=""
LANGCHAIN_PROJECT=supply-chain-agentic-orchestrator

# Database Persistence (Matches docker-compose)
DATABASE_URI=postgresql://admin:securepassword@localhost:5432/supply_chain_audit
```

### 3. Spin up the Database

Start the PostgreSQL audit database in the background:

```bash
docker compose up -d
```

### 4. Run the Pipeline

Use `uv` to sync dependencies and execute the orchestrator:

```bash
uv run python -m src.main
```

The system will ingest the batch mock data, auto-resolve the standard noise, and halt on the critical events to prompt you for `APPROVE` or `SKIP` authorization before executing the ERP mock.

### 5. Run Tests & Type Checks

```bash
uv run pytest
uv run mypy .
```

---

## 🛑 Shutting Down

To spin down the local database while preserving your saved LangGraph checkpoints securely on your disk:

```bash
docker compose down
```

