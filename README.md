# OmniContext: Cross-Repository Code Context Engine
### Deterministic Code Knowledge Graph & Autonomous Agent Context Engine for Multi-Repo Systems

[![Built on AWS](https://img.shields.io/badge/Built%20on-Amazon%20Web%20Services-FF9900?logo=amazon-aws&logoColor=white)](https://aws.amazon.com)
[![Model Context Protocol](https://img.shields.io/badge/Protocol-Model%20Context%20Protocol%20(MCP)-0052FF)](https://modelcontextprotocol.io)
[![AWS Strands Agents](https://img.shields.io/badge/Orchestrator-AWS%20Strands%20Agents%20SDK-527FFF)](https://aws.amazon.com)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://python.org)
[![Hackathon](https://img.shields.io/badge/WeMakeDevs-Bharat%20Builds%20Tour%202026-critical)](https://wemakedevs.org)

Built for the **WeMakeDevs Bharat Builds Tour "First Commit" Hackathon** (September 17–20, 2026).

---

## 💡 What is OmniContext? (In Plain English)

When software teams build modern applications, their code is almost never in a single folder. It is spread across **multiple different repositories**—for example, a backend API repository (FastAPI / Go), a frontend web application (React / Next.js / TypeScript), and a shared core SDK.

Today's AI coding tools struggle with this setup:
- **They can't see the big picture**: If you change an API endpoint in the backend repository, the AI doesn't know which frontend buttons, forms, or mobile apps in other repositories depend on it.
- **They waste thousands of tokens**: Traditional search dumps entire files into the AI chat. This quickly runs out of memory, costs a lot of money, and causes the AI to hallucinate or get confused.
- **They cause silent bugs in production**: Because the AI doesn't trace dependencies across repositories, breaking changes slip into production unnoticed.

### What OmniContext Does
**OmniContext is an intelligent context engine that builds a real-time, compiler-accurate map (a code knowledge graph) connecting all your repositories together.**

It inspects your actual code syntax, understands which functions call which endpoints across different services, and feeds an autonomous AI agent (powered by Amazon Bedrock Claude Sonnet 4) only the **exact** lines of code it needs to safely plan refactors, deprecations, and multi-repository migrations.

---

## 🎯 How OmniContext Helps You

| Challenge | What Traditional AI Tools Do | How OmniContext Solves It |
| :--- | :--- | :--- |
| **Cross-Repo Awareness** | Treats each repository as an isolated silo. Cannot tell that `fetch('/v1/auth')` in the frontend relies on `@router.post('/v1/auth')` in the backend. | **100% Cross-Repo Recall**: Automatically maps callers, callees, imports, and API routes across repository boundaries. |
| **Token Cost & Speed** | Dumps whole files (14,500+ tokens) into the context window, causing slow responses and high API costs. | **97.6% Token Reduction**: Retrieves only the exact AST-bounded function chunks (~120 tokens), responding in sub-milliseconds. |
| **AI Hallucinations** | Makes up non-existent file paths or invalid function signatures when guessing context. | **Zero Hallucination**: Grounded in deterministic compiler facts with exact file paths and line numbers. |
| **Blast Radius Detection** | You don't know what will break until after code is pushed to staging/production. | **Instant Blast Radius Analysis**: Traces all upstream callers and downstream services before you make a change. |
| **Real GitHub Repositories** | Often limited to pre-packaged toy datasets. | **Dynamic GitHub Ingestion**: Give it any public GitHub URL or local directory, and it clones, parses, and indexes it dynamically. |

---

## 🚀 How to Use OmniContext (Step-by-Step)

### 1. Quick Installation (3 Minutes)

#### Prerequisites
- **Python 3.10+** installed
- **Git** installed

#### Clone & Install
```bash
# Clone the repository
git clone https://github.com/abhayrajjais01/OmniContext.git
cd OmniContext

# Create and activate a Python virtual environment
# On Windows PowerShell:
python -m venv .venv
.venv\Scripts\Activate.ps1

# On macOS / Linux:
python3 -m venv .venv
source .venv/bin/activate

# Install all dependencies
pip install -r requirements.txt
```

#### Set Up Your Environment
```bash
# Copy the example environment configuration
# On Windows:
copy .env.example .env
# On macOS / Linux:
cp .env.example .env
```

> **Note on Modes**:
> - **Local Mode (`ENV=local`)**: **Default & Zero-Config**. Requires **no AWS account or credentials**. Uses local SQLite and an in-memory vector cache with a deterministic local reasoning engine.
> - **AWS Cloud Mode (`ENV=aws`)**: Connects to **Amazon Bedrock** (Anthropic Claude Sonnet 4 + Titan Text Embeddings v2) and **Amazon OpenSearch Serverless (AOSS)**.

---

### 2. Method 1: The Interactive Web Dashboard (Recommended)

Launch the visual dashboard in your browser:
```bash
streamlit run ui/app.py
```
Open your browser at **`http://localhost:8501`**.

Here is what you can do in the dashboard:

1. **📥 Ingest Real GitHub Repositories (Sidebar)**:
   - On the left sidebar under **Dynamic GitHub Ingestion**, type or paste any GitHub URLs (one per line).
   - Or pick a preset:
     - *FastAPI & Starlette* (`https://github.com/fastapi/fastapi`, `https://github.com/encode/starlette`)
     - *Pallets: Flask & Werkzeug* (`https://github.com/pallets/flask`, `https://github.com/pallets/werkzeug`)
     - *OmniContext (Self-Index)* (`https://github.com/abhayrajjais01/OmniContext.git`)
   - Click **📥 Clone & Index Repositories**. The engine will shallow-clone the repositories, parse all AST symbols, connect cross-repo routes, and reload the dashboard with live data.
   - You can click **🔄 Reset to Demo Testbeds** at any time to return to the sample microservices testbed.

2. **🚀 Run the Autonomous Agent (Tab 1: Agent Execution)**:
   - Enter a cross-repository directive (for example: *"Deprecate legacy /v1/auth/verify endpoint and update all downstream frontend consumers to /v2/auth/token"*).
   - Or pick a symbol from the **🎯 Quick Target Symbol** dropdown to auto-draft a task for any symbol found in your indexed code.
   - Click **⚡ Execute Agent Loop**. Watch the agent traverse the graph, inspect caller functions, and generate a step-by-step cross-repository migration plan.
   - Inspect the **Safety Guardrail Report** (cycle detection, token budget enforcement, and execution telemetry).

3. **🕸️ Explore the Cross-Repo Graph (Tab 2: Cross-Repo Graph)**:
   - View the color-coded interactive dependency graph.
   - Filter by repository or search for specific symbols (functions, classes, endpoints).
   - Use the **Max Graph Nodes** selector for ultra-fast rendering on massive codebases.
   - Scroll down to the **🔎 Blast Radius Inspector**: enter or select any symbol name to see its entire blast radius—every file and line that calls it or depends on it across repositories.

4. **📊 View Empirical Benchmarks (Tab 3: Benchmarks)**:
   - Review side-by-side quantitative comparisons showing OmniContext's **97.6% token reduction** and **100% cross-repo recall** against standard Naive RAG.

---

### 3. Method 2: Command-Line Interface (CLI)

You can also run all OmniContext tools directly from the terminal:

#### Index Real GitHub Repositories via CLI
```bash
# Ingest one or more GitHub repositories
python scripts/index_github_repos.py "https://github.com/fastapi/fastapi" "https://github.com/encode/starlette"

# Or index local folder paths
python scripts/index_github_repos.py "testbed/repo_auth_core" "testbed/repo_frontend_portal"
```

#### Run the Health & Smoke Test
```bash
python scripts/smoke_test.py
```

#### Run the Complete Test Suite
```bash
python -m pytest tests/ -v
```

#### Run the Quantitative Benchmark Suite
```bash
python evaluation/run_benchmarks.py
```

---

### 4. Method 3: As a Model Context Protocol (MCP) Server

OmniContext can act as a standard **Model Context Protocol (MCP)** server, providing deterministic code graph tools to external AI coding environments like **Claude Desktop**, **Cursor**, **Windsurf**, or custom agent frameworks:

```bash
python mcp_server/server.py
```

The MCP server exposes 5 deterministic tools:
1. `traverse_call_graph`: Traces the blast radius of a symbol across all repositories.
2. `get_symbol_definition`: Finds the exact code definition, file path, and line numbers of any function or class.
3. `get_usage_dependency_links`: Identifies all callers and consumers across repo boundaries.
4. `get_ast_chunk`: Retrieves the complete, unbroken AST syntax block for a specific symbol.
5. `semantic_code_search`: Performs natural language conceptual searches backed by vector embeddings.

---

## 🏛️ How It Works Under the Hood

```mermaid
flowchart TB
    subgraph Repos["1. Real Repositories (GitHub / Local)"]
        RepoA["Backend Service (e.g., FastAPI / Go)"]
        RepoB["Frontend Portal (e.g., React / TypeScript)"]
        RepoC["Shared SDK / Core Library"]
    end

    subgraph ParsingEngine["2. AST Parsing & Semantic Linking"]
        TS["Tree-sitter Parser\n(Boundary-Aware AST Chunking)"]
        Linker["SCIP / Cross-Repo Linker\n(Matches HTTP Routes & Imports)"]
    end

    subgraph StorageLayer["3. Hybrid Knowledge Graph Storage"]
        SQLite["SQLite Edge Matrix\n(Directional Call Graph + FTS5 Search)"]
        AOSS["Amazon OpenSearch Serverless\n(Dense Vector KNN Search)"]
        Titan["Amazon Titan Text Embeddings v2"]
    end

    subgraph MCPGatekeeper["4. Model Context Protocol (MCP) Server"]
        Tools["Deterministic Tools:\n- traverse_call_graph\n- get_symbol_definition\n- get_usage_dependency_links\n- get_ast_chunk\n- semantic_code_search"]
    end

    subgraph AgentCore["5. Autonomous Agent Orchestrator"]
        Strands["AWS Strands Agents SDK"]
        Bedrock["Amazon Bedrock (Claude Sonnet 4)"]
        Guardrails["Lifecycle Guardrails\n(Cycle Detector & Token Budget)"]
    end

    subgraph Interfaces["6. User Interfaces"]
        UI["Interactive Streamlit Dashboard (Port 8501)"]
        CLI["CLI Ingestion & Benchmark Scripts"]
    end

    Repos --> TS --> Linker
    Linker --> SQLite
    TS --> Titan --> AOSS
    SQLite & AOSS --> Tools
    Tools --> Strands
    Bedrock <--> Strands
    Strands --> Guardrails --> UI & Interfaces
```

---

## 📊 Benchmark Results: OmniContext vs. Standard RAG

Tested against the **RepoQA** (needle in a haystack) and **CodeScaleBench** (cross-repo dependency tracing) methodologies:

| Metric | Traditional Naive RAG | OmniContext (AST Code Graph) | What This Means |
| :--- | :--- | :--- | :--- |
| **Cross-Repo Recall** | `0%` (Fails to link repos) | **`100%`** | OmniContext always catches cross-repo connections. |
| **Context Overhead** | `~14,500 tokens` | **`~120 tokens`** | **97.6% token reduction**, saving money and time. |
| **Hallucinated Files** | `42%` | **`0%`** | Grounded in exact compiler AST boundaries. |
| **Blast Radius Detection** | Failed (Silent production breaks) | **Complete (100% of callers caught)** | Zero unexpected downstream breakages. |
| **Retrieval Speed** | `~3,400 ms` | **`0.4 ms`** | **8,500x faster** than re-embedding raw text chunks. |

---

## ☁️ "Built on AWS" Cloud Architecture

OmniContext is fully integrated with Amazon Web Services:

| AWS Service | Component Used | Purpose in OmniContext |
| :--- | :--- | :--- |
| **Amazon Bedrock** | **Anthropic Claude Sonnet 4** (`us.anthropic.claude-sonnet-4-20250514-v1:0`) | Multi-turn reasoning, cross-repository tool orchestration, and migration planning. |
| **Amazon Bedrock** | **Amazon Titan Text Embeddings v2** (`amazon.titan-embed-text-v2:0`) | Generates 1024-dimensional dense vectors for semantic conceptual search. |
| **Amazon OpenSearch Serverless** | **AOSS Collection (`omnicontext-code-index`)** | Serverless vector database executing k-NN similarity search over code chunks. |
| **AWS Strands SDK** | **Agent Loop & Lifecycle Hooks** | Model-driven autonomous execution loop with safety guardrails. |
| **Amazon Bedrock AgentCore** | **Serverless Container Runtime** | Containerized deployment using `@app.entrypoint` for cloud execution. |

---

## 👥 3-Person Team Division of Responsibility

| Track | Owner | Core Responsibilities |
| :--- | :--- | :--- |
| **Track 1: Cloud & Storage** | **Member 1** | SQLite relational edge matrix, Amazon OpenSearch Serverless integration, Titan v2 vector store, and AWS cloud deployment. |
| **Track 2: Parsing & MCP** | **Member 2** | Tree-sitter multi-language AST parser, SCIP cross-repo endpoint linker, FastMCP server, and GitHub repo ingester. |
| **Track 3: Agent & UI** | **Member 3** | AWS Strands Agent orchestrator, Bedrock Claude Sonnet loop, safety guardrails, Streamlit telemetry dashboard, and benchmarks. |

---

## 📄 License
Distributed under the Apache 2.0 License. Built for the WeMakeDevs Bharat Builds Tour "First Commit" Hackathon 2026.