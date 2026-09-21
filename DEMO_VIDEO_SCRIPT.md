# CrossContext - 3-Minute Pitch & Live Demo Script

**Target Duration**: 3:00 (180 seconds)  
**Tone**: High-energy, relatable, pitch-driven, clear, and non-academic  
**Subject Repositories**: `ruxailab` ecosystem (`RUXAILAB`, `eye-tracker-api`, `web-eye-tracker-front`)  
**Core Value Proposition**: Connects isolated repositories into a living dependency map, eliminating cross-repo breaking changes while saving over 95% in AI token costs.

---

## Pitch Timing Breakdown

| Timestamp | Section | Visual Scene | Pitch Goal |
|---|---|---|---|
| **0:00 - 0:25** (25s) | **The Relatable Hook** | Clean UI in Light Mode (`https://d2kn4upmh6y31q.cloudfront.net/`) | Hook the judges with a painful, everyday engineering problem: breaking downstream apps on API changes. |
| **0:25 - 1:15** (50s) | **Live UI & Real-World Map** | Ingest `ruxailab` repos -> 2D Graph -> Architecture Blueprint | Show instant discovery, live cross-repo linking between Python API and Vue frontend, and blast radius. |
| **1:15 - 1:50** (35s) | **Autonomous Agent** | ContextBot chat panel & synchronized diffs | Show AI diagnosing cross-repo breaking changes and generating synchronized fixes in one go. |
| **1:50 - 2:35** (45s) | **Antigravity IDE & MCP Server** | Antigravity IDE chat window | Show direct MCP tool invocation in the editor, saving over 95% of prompt tokens. |
| **2:35 - 3:00** (25s) | **Business Impact & Wrap-Up** | Benchmarks tab -> Closing pitch | Summarize cost savings, zero downtime, and massive developer productivity. |

---

## Scene-by-Scene Pitch Script

### Scene 1: The Relatable Hook (0:00 - 0:25)
**Screen**: Open browser at `https://d2kn4upmh6y31q.cloudfront.net/` in crisp Light Mode.  
**Action**: Point to the clean workspace and top metrics bar.

**Spoken Script**:
> "Have you ever made a small, innocent change to a backend API, merged your code, and accidentally took down the frontend without realizing it until production broke?
> 
> Almost every engineering team builds across multiple repositories. But today's AI coding tools are repository-blind: they only look at one repo at a time, dump thousands of irrelevant files into context, and guess how services connect.
> 
> That is why we built **CrossContext**: an intelligent engine that maps all your repositories together into a single living dependency web, so developers can refactor and ship across services with complete confidence."

---

### Scene 2: Live Ingestion & The Living Code Map (0:25 - 1:15)
**Screen**: Click **+ Ingest Repos** button. Enter `ruxailab` in the Organization field.  
**Action**:
1. Click **Discover Repositories** -> select `RUXAILAB`, `eye-tracker-api`, and `web-eye-tracker-front`.
2. Click **Ingest Selected (3) Repositories** -> watch the parsing bar complete in real-time.
3. On the **Ingestion Summary** modal, point out the discovered contracts (`health_check`, `calib_validation`, `realtime_validation`). Click **Close & View Graph**.
4. Show the **Interactive 2D Graph**:
   - Pan between the backend `eye-tracker-api` and the frontend `web-eye-tracker-front`.
   - Click node `calib_validation` to highlight its blast radius and see connected lines light up.
5. Click **Architecture Blueprint** tab -> show the Inter-Repository Contract Matrix linking Vue components directly to Python endpoints.

**Spoken Script**:
> "Let's see this on a real-world multi-repo system from `ruxailab`: our backend `eye-tracker-api`, frontend `web-eye-tracker-front`, and the core `RUXAILAB` repo.
> 
> In just seconds, CrossContext parses the codebases and reconstructs the real relationships between them.
> 
> On this visual map, our Python backend endpoints connect directly to the Vue frontend components calling them. 
> 
> If I click any endpoint, like calibration validation, CrossContext instantly shows me its **blast radius**: every single screen, function, and UI component that depends on it. If a backend engineer touches this signature, they immediately see every frontend component that could break."

---

### Scene 3: Autonomous Multi-Repo Agent (1:15 - 1:50)
**Screen**: Switch back to **Agent Task & Graph** tab.  
**Action**:
1. In the ContextBot chat input, paste:
   ```text
   Analyze the blast radius if we modify the calibration validation endpoint in eye-tracker-api
   ```
2. Hit **Send** (or Enter).
3. Show ContextBot executing reasoning steps (`reasoning_turn`, `traverse_call_graph`, `get_symbol_definition`).
4. Highlight the structured safety report and synchronized cross-repo diffs.

**Spoken Script**:
> "Now let's ask our AI agent, ContextBot: *'What is the blast radius if we modify the calibration validation endpoint in eye-tracker-api?'*
> 
> Notice how ContextBot does not guess or hallucinate. It traces the live AST map, pinpoints the exact frontend files in `web-eye-tracker-front` calling that route, and provides synchronized code patches for both repositories at once. No more silent contract breakages."

---

### Scene 4: Native MCP Server in Antigravity IDE (1:50 - 2:35)
**Screen**: Switch to Antigravity IDE chat window.  
**Action**: In the chat prompt, run the MCP tool commands.

**Prompt 1 (Diagnostics & Status)**:
```text
Check CrossContext graph diagnostics and show total indexed symbols and repositories.
```
*(Model invokes `get_graph_diagnostics` and returns total symbol count and indexed repositories).*

**Prompt 2 (Cross-Repo Dependency Links & AST Traversal)**:
```text
Using the CrossContext MCP server, trace the call graph for symbol calib_validation and find all cross-repository consumers across ruxailab.
```
*(Model invokes `traverse_call_graph` and `get_usage_dependency_links`, showing callers in `web-eye-tracker-front` consuming `eye-tracker-api`).*

**Prompt 3 (Targeted Semantic Search)**:
```text
Search for calibration symbols across the ruxailab repositories using CrossContext semantic code search.
```
*(Model invokes `semantic_code_search` with exact AST line spans).*

**Spoken Script**:
> "Best of all, developers do not need to leave their editor. CrossContext runs as a native Model Context Protocol (MCP) server directly inside Antigravity.
> 
> Right from the IDE chat, we can ask the assistant to query the graph and trace cross-repository call chains.
> 
> Instead of dumping entire codebases into the prompt, CrossContext extracts only the exact connected functions needed for the task. This cuts AI token usage by **over 95%**, making coding assistants dramatically faster, cheaper, and more accurate."

---

### Scene 5: Business Impact & Conclusion (2:35 - 3:00)
**Screen**: Switch back to browser, click **Benchmarks** tab.  
**Action**: Point out the live comparative evaluation matrix comparing deterministic AST graphs against standard vector RAG.

**Spoken Script**:
> "By turning multi-repo chaos into deterministic context, CrossContext eliminates production downtime from breaking API changes, saves **over 95% on AI token costs**, and gives engineering teams 100% cross-repository recall.
> 
> Powered by AWS Bedrock, OpenSearch Serverless, and deterministic AST graphs, CrossContext brings true cross-repository intelligence to every developer. Thank you!"

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
