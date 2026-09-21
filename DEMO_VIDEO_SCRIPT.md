# CrossContext - 3-Minute Live Pitch & Demo Script (Action-Sync Format)

**Target Duration**: 3:00 (180 seconds)  
**Format**: `Spoken (Before Action)` -> `Action (What To Do)` -> `Spoken (After Action)`  
**Subject Repositories**: `ruxailab` ecosystem (`RUXAILAB`, `eye-tracker-api`, `web-eye-tracker-front`)  

---

## Complete Step-by-Step Script

---

### Part 1: The Relatable Hook (0:00 - 0:25)

* **Spoken (Before Action)**:
  > "Have you ever made a small, innocent change to a backend API, merged your code, and accidentally took down the frontend without realizing it until production broke?"

* **Action**:
  > Open browser at `https://d2kn4upmh6y31q.cloudfront.net/` in crisp Light Mode. Show the clean workspace and top metrics bar.

* **Spoken (After Action)**:
  > "Almost every modern engineering team builds across dozens of separate repositories. But today's AI coding tools are repository-blind: they only look at one repo at a time, stuff thousands of irrelevant files into context, and guess how services connect. That is why we built **CrossContext**: an intelligent engine that maps all your repositories together into a single living dependency web."

---

### Part 2: Dynamic Multi-Repo Ingestion (0:25 - 0:50)

* **Spoken (Before Action)**:
  > "Let's see this in action on a real-world multi-repository codebase from the `ruxailab` organization."

* **Action**:
  > 1. Click the **+ Ingest Repos** button in the top navigation.
  > 2. Type `ruxailab` in the organization field and click **Discover Repos**.
  > 3. Check the 3 repositories: `RUXAILAB`, `eye-tracker-api`, and `web-eye-tracker-front`.
  > 4. Click **Ingest Selected (3) Repositories**.

* **Spoken (After Action)**:
  > "In just seconds, CrossContext parses the abstract syntax trees of our Python backend, Vue frontend, and core libraries, extracting symbols and discovering cross-repository API contracts automatically."

---

### Part 3: 2D Semantic Graph & Dynamic Blast Radius (0:50 - 1:15)

* **Spoken (Before Action)**:
  > "Let's close the summary modal and look at the interactive 2D code graph."

* **Action**:
  > 1. Click **Close & View Graph**.
  > 2. Pan across the swimlanes to show `eye-tracker-api` (backend) connecting to `web-eye-tracker-front` (frontend).
  > 3. Click the node **`calib_validation`** in the `eye-tracker-api` lane.

* **Spoken (After Action)**:
  > "Look at the red banner at the top: it dynamically warns us that modifying `calib_validation` in `eye-tracker-api` has a blast radius impacting 1 cross-repo caller in `web-eye-tracker-front`. Before touching a single line of code, we know the exact downstream files that could break."

---

### Part 4: Architecture Blueprint (1:15 - 1:35)

* **Spoken (Before Action)**:
  > "Now let's see how CrossContext synthesizes these contracts for the whole team."

* **Action**:
  > Click on the **Architecture Blueprint** tab in the top navigation bar. Scroll through the Inter-Repository API Contract Matrix.

* **Spoken (After Action)**:
  > "Here is our live contract matrix: frontend Vue components in `web-eye-tracker-front` mapped directly to backend Python endpoints in `eye-tracker-api`. CrossContext also generates an ultra-compressed AI prompt ready for external IDEs."

---

### Part 5: Autonomous Multi-Repo Agent (1:35 - 2:05)

* **Spoken (Before Action)**:
  > "Let's switch back to the Agent panel and put our autonomous agent, ContextBot, to work."

* **Action**:
  > 1. Click the **Agent Task & Graph** tab.
  > 2. Paste into the chat input:  
  >    `Analyze the blast radius if we modify the calibration validation endpoint in eye-tracker-api`
  > 3. Hit **Send** (or press Enter).

* **Spoken (After Action)**:
  > "ContextBot doesn't guess or flood the prompt with random text. It queries the deterministic AST graph, traces callers into `web-eye-tracker-front`, and outputs a safety report with synchronized code patches across both repositories in a single pass."

---

### Part 6: Native MCP Server in Antigravity IDE (2:05 - 2:40)

* **Spoken (Before Action)**:
  > "Developers don't even have to leave their editor. CrossContext runs as a native Model Context Protocol (MCP) server directly inside Antigravity."

* **Action**:
  > Switch to the Antigravity chat window and enter:  
  > `Using the CrossContext MCP server, trace the call graph for symbol calib_validation and find all cross-repository consumers across ruxailab.`

* **Spoken (After Action)**:
  > "The MCP server executes `traverse_call_graph` and returns only the exact verified call chain. Instead of feeding entire repositories into the prompt, CrossContext extracts only the exact connected functions needed, cutting AI token usage by **over 95%**."

---

### Part 7: Live Benchmarks & Closing Pitch (2:40 - 3:00)

* **Spoken (Before Action)**:
  > "Let's verify the empirical performance in our live Benchmarks suite."

* **Action**:
  > Switch back to the browser and click the **Benchmarks** tab. Point to the comparative evaluation matrix.

* **Spoken (After Action)**:
  > "Against standard vector RAG, CrossContext delivers **over 95% token savings**, **100% cross-repository recall**, and **zero hallucinated file paths**. Powered by AWS Bedrock, OpenSearch Serverless, and deterministic AST graphs, CrossContext brings true multi-repository intelligence to every developer. Thank you!"

---

## Quick Copy-Paste Prompts for the Demo

### ContextBot UI Prompt:
```text
Analyze the blast radius if we modify the calibration validation endpoint in eye-tracker-api
```

### Antigravity MCP Prompt:
```text
Using the CrossContext MCP server, trace the call graph for symbol calib_validation and find all cross-repository consumers across ruxailab.
```
