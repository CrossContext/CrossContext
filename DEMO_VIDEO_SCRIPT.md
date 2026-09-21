# CrossContext - 3-Minute Live Demo Video Script

**Target Duration**: 3:00 (180 seconds)  
**Subject Repositories**: `ruxailab` ecosystem (`RUXAILAB`, `eye-tracker-api`, `web-eye-tracker-front`)  
**Core Features Covered**: Dynamic Multi-Repo Ingestion, 2D AST Semantic Graph, Blast Radius Analysis, Architecture Blueprint, Live Benchmarks, Autonomous Multi-Repo Agent, and Native MCP Server in Antigravity.

---

## Timing Breakdown

| Timestamp | Section | Visual Scene | Core Message / Goal |
|---|---|---|---|
| **0:00 - 0:25** (25s) | **The Problem & Intro** | Intro slides / Clean UI in Light Mode | Modern microservices break silently at API boundaries; RAG fails across multi-repo codebases. |
| **0:25 - 1:15** (50s) | **Live UI & Ingestion** | Ingestion modal -> 2D AST Graph -> Blueprint | Dynamic GitHub ingestion of `ruxailab` repos, instant cross-repo call graph, blast radius detection. |
| **1:15 - 1:55** (40s) | **Autonomous Agent** | ContextBot chat panel & diff viewer | ContextBot detects cross-repo breaking changes and generates synchronized multi-repo diffs. |
| **1:55 - 2:40** (45s) | **Antigravity MCP Demo** | Antigravity IDE chat window | Direct MCP tool invocation for AST traversal, symbol resolution, and blast radius calculation. |
| **2:40 - 3:00** (20s) | **Impact & Conclusion** | Benchmarks tab -> Closing screen | Dramatic token reduction, 100% cross-repo recall, zero hallucinated paths. |

---

## Detailed Scene-by-Scene Script

### Scene 1: The Problem & Introduction (0:00 - 0:25)
**Screen**: Open browser at `https://d2kn4upmh6y31q.cloudfront.net/` in crisp Light Mode.  
**Action**: Point out the clean workspace and top metrics bar.

**Spoken Script**:
> "Modern software engineering lives across multiple repositories, but AI coding assistants only see one file or one repo at a time. When an API contract changes in a backend service, client applications break silently. Naive RAG dumps massive amounts of irrelevant tokens and hallucinates dependencies.
> 
> Meet **CrossContext**: a deterministic cross-repository code context engine powered by AST graphs, SCIP symbol linkers, AWS Bedrock, and an autonomous agent reasoning loop."

---

### Scene 2: Live Ingestion & 2D Semantic Graph (0:25 - 1:15)
**Screen**: Click **+ Ingest Repos** button. Enter `ruxailab` in the Organization field.  
**Action**:
1. Click **Discover Repositories** -> select `RUXAILAB`, `eye-tracker-api`, and `web-eye-tracker-front`.
2. Click **Ingest Selected (3) Repositories** -> watch the parsing bar complete.
3. Review the **Ingestion & Indexing Summary** modal showing indexed symbols and discovered cross-repo API contracts (`health_check`, `calib_validation`, `realtime_validation`). Click **Close & View Graph**.
4. Show the **Interactive 2D Graph** rendered in swimlanes:
   - Pan and zoom across `RUXAILAB`, `eye-tracker-api`, and `web-eye-tracker-front`.
   - Click quick directive `health_check` or `calib_validation`.
   - Toggle **API Directive** filters (`API`, `CLS`, `FN`).
   - Click node `calib_validation` to highlight its blast radius and inbound callers.
5. Click **Architecture Blueprint** tab -> show the Inter-Repository API Contract Matrix linking Vue components in `web-eye-tracker-front` directly to Python endpoints in `eye-tracker-api`.
6. Click **Code Explorer** tab -> highlight cross-repo file trees.

**Spoken Script**:
> "Let's ingest the `ruxailab` ecosystem. CrossContext discovers the public repositories and clones `RUXAILAB`, `eye-tracker-api`, and `web-eye-tracker-front`.
> 
> In seconds, tree-sitter parses the abstract syntax trees, extracts symbols, and reconstructs the cross-repository dependency web. On the 2D graph, backend endpoints link directly to frontend HTTP consumers.
> 
> In the Architecture Blueprint, we immediately see exact contracts: frontend components in `web-eye-tracker-front` consuming endpoints like `calib_validation` and `realtime_validation` in `eye-tracker-api`.
> 
> Clicking any symbol instantly calculates its blast radius across every connected repository, showing exactly which services will break if a signature changes."

---

### Scene 3: Autonomous Multi-Repo Agent (1:15 - 1:55)
**Screen**: Switch back to **Agent Task & Graph** tab.  
**Action**:
1. In the ContextBot chat input, paste:
   ```text
   Analyze the blast radius if we modify the calibration validation endpoint in eye-tracker-api
   ```
2. Hit **Send** (or Enter).
3. Watch ContextBot execute multi-turn reasoning steps (`reasoning_turn`, `traverse_call_graph`, `get_symbol_definition`).
4. View the structured safety report and synthesized cross-repo patch summary.

**Spoken Script**:
> "Now let's ask ContextBot to analyze the blast radius if we update our calibration validation endpoint in `eye-tracker-api`.
> 
> Rather than blindly searching text embeddings, ContextBot queries the deterministic AST graph. It traces callers from the backend controller into the frontend web client, verifies payload schemas, and synthesizes synchronized diffs across both repositories in a single pass."

---

### Scene 4: Native MCP Server in Antigravity IDE (1:55 - 2:40)
**Screen**: Switch to Antigravity IDE chat window.  
**Action**: In the chat prompt, run the MCP tool commands.

**Prompt 1 (Graph Diagnostics & Status)**:
```text
Check CrossContext graph diagnostics and show total indexed symbols and repositories.
```
*(Model invokes `get_graph_diagnostics` and returns total symbol count and indexed repositories).*

**Prompt 2 (Cross-Repo Dependency Links & AST Traversal)**:
```text
Using the CrossContext MCP server, trace the call graph for symbol calib_validation and find all cross-repository consumers across ruxailab.
```
*(Model invokes `traverse_call_graph` and `get_usage_dependency_links`, showing callers in `web-eye-tracker-front` consuming `eye-tracker-api`).*

**Prompt 3 (Targeted Semantic Symbol Search)**:
```text
Search for calibration symbols across the ruxailab repositories using CrossContext semantic code search.
```
*(Model invokes `semantic_code_search` with exact AST line spans).*

**Spoken Script**:
> "CrossContext also runs as a native Model Context Protocol (MCP) server directly inside our IDE.
> 
> In Antigravity, we can ask the assistant to query graph diagnostics, trace cross-repo call graphs, and retrieve exact AST chunks. Instead of feeding entire codebases into the model context window, the MCP server returns only the exact verified call chains needed to solve the task."

---

### Scene 5: Benchmarks, Impact & Conclusion (2:40 - 3:00)
**Screen**: Switch back to browser, click **Benchmarks** tab.  
**Action**: Point out the live comparative evaluation matrix comparing deterministic AST graphs against standard vector RAG.

**Spoken Script**:
> "On real-world benchmarks, CrossContext achieves massive token reductions compared to naive RAG, with complete cross-repository recall, sub-second latency, and zero hallucinated file paths.
> 
> Built on AWS Strands, Bedrock, OpenSearch Serverless, and deterministic AST graphs, CrossContext bridges the multi-repository gap for modern software engineering. Thank you!"

---

## Copy-Paste Demo Cheat Sheet

### Quick Prompts for UI ContextBot:
1. `Trace cross-repo dependencies between eye-tracker-api and web-eye-tracker-front`
2. `What is the blast radius if we change calib_validation signature in eye-tracker-api?`
3. `Generate synchronized cross-repository diffs for updating the health check endpoint`

### Quick Prompts for Antigravity MCP Server:
1. `Check CrossContext graph diagnostics and list all indexed repositories.`
2. `Use crosscontext MCP to traverse the call graph for calib_validation in eye-tracker-api.`
3. `Use semantic_code_search to find calibration endpoints across all indexed repositories.`
