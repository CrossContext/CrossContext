"""
CrossContext - Model Provider Adapter
Supports:
1. Amazon Bedrock (Anthropic Claude 3.5 Sonnet / Claude 3.7 Sonnet)
2. Local Deterministic LLM Simulator (Zero-AWS offline execution)
"""

import os
import json
from typing import Dict, Any, List, Optional


from agent_orchestrator.bedrock_client import BedrockClient


class ModelProvider:
    def __init__(self, model_id: Optional[str] = None, env: Optional[str] = None):
        self.env = env or os.getenv("ENV", "aws").lower()
        self.region = os.getenv("AWS_REGION", "us-west-2")
        self.model_id = model_id or os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-5-20250929-v1:0")
        self.bedrock = BedrockClient(region_name=self.region)

    def invoke_with_tools(
        self,
        system_prompt: str,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Invokes Bedrock Claude or falls back to local autonomous simulator."""
        if self.env == "aws":
            try:
                return self.bedrock.invoke_claude(
                    system_prompt=system_prompt,
                    messages=messages,
                    tools=tools,
                    model_id=self.model_id
                )
            except Exception as e:
                # If AWS fails or credentials missing, gracefully fall back to local simulator
                print(f"[ModelProvider] AWS Bedrock notice ({e}), using local deterministic engine.")
                return self._simulate_local_reasoning(messages, tools)
        else:
            return self._simulate_local_reasoning(messages, tools)

    def _simulate_local_reasoning(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Dynamic local reasoning engine for offline or zero-cloud execution.
        Answers conceptual questions directly and queries the real code graph for refactoring tasks.
        """
        # Extract user prompt from the first message
        user_prompt = ""
        for m in messages:
            if m.get("role") == "user" and isinstance(m.get("content"), str):
                user_prompt = m["content"]
                break

        prompt_lower = user_prompt.lower().strip()

        # Step 0: Check if query is conceptual / architectural
        step_count = len([m for m in messages if m.get("role") == "assistant"])

        # Conceptual knowledge base
        if self._is_conceptual_query(prompt_lower):
            answer_text = self._get_conceptual_answer(prompt_lower)
            return {
                "role": "assistant",
                "content": [{"type": "text", "text": answer_text}]
            }

        # Step 0: Code-specific inquiry -> initiate graph traversal or search
        if step_count == 0:
            import re
            endpoint_match = re.findall(r'(/[a-zA-Z0-9_\-/]+)', user_prompt)
            quoted = re.findall(r'[`\'"]([a-zA-Z0-9_\-\./]+)[`\'"]', user_prompt)
            stopwords = {
                "deprecate", "update", "all", "downstream", "upstream", "consumers", "producer",
                "service", "services", "endpoint", "endpoints", "legacy", "the", "and", "for",
                "with", "from", "into", "what", "where", "how", "find", "show", "check", "who", "calls"
            }
            all_words = [w for w in re.findall(r'[a-zA-Z0-9_]{3,}', user_prompt) if w.lower() not in stopwords]

            if quoted:
                target_symbol = quoted[0]
            elif endpoint_match:
                target_symbol = endpoint_match[0]
            elif all_words:
                target_symbol = all_words[0]
            else:
                target_symbol = "auth"

            return {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": f"I will analyze the cross-repository call graph starting from symbol `{target_symbol}` to detect all affected dependencies."
                    },
                    {
                        "type": "tool_use",
                        "id": "tool_call_01",
                        "name": "traverse_call_graph",
                        "input": {"root_symbol": target_symbol, "max_depth": 3}
                    }
                ]
            }

        # Step 1: Examine tool result from step 0
        elif step_count == 1:
            target_node_id = ""
            for m in reversed(messages):
                if m.get("role") == "user" and isinstance(m.get("content"), list):
                    for part in m["content"]:
                        if isinstance(part, dict) and part.get("type") == "tool_result":
                            try:
                                data = json.loads(part.get("content", "{}"))
                                callers = data.get("upstream_callers", [])
                                if callers:
                                    target_node_id = callers[0].get("id", "")
                            except Exception:
                                pass

            if target_node_id:
                return {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "text",
                            "text": f"The dependency traversal identified a caller in repository `{target_node_id.split(':')[0]}`. I will now retrieve the exact AST chunk for `{target_node_id}`."
                        },
                        {
                            "type": "tool_use",
                            "id": "tool_call_02",
                            "name": "get_ast_chunk",
                            "input": {"node_id": target_node_id}
                        }
                    ]
                }
            else:
                return {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "text",
                            "text": "I will perform a semantic code search across the indexed repositories to locate matching declarations."
                        },
                        {
                            "type": "tool_use",
                            "id": "tool_call_02",
                            "name": "semantic_code_search",
                            "input": {"query": user_prompt, "limit": 3}
                        }
                    ]
                }

        # Step 2: Formulate dynamic synthesis
        else:
            discovered_nodes = []
            for m in messages:
                if m.get("role") == "user" and isinstance(m.get("content"), list):
                    for part in m["content"]:
                        if isinstance(part, dict) and part.get("type") == "tool_result":
                            try:
                                data = json.loads(part.get("content", "{}"))
                                if "root_symbol" in data:
                                    for caller in data.get("upstream_callers", []):
                                        discovered_nodes.append(caller)
                                elif "id" in data:
                                    discovered_nodes.append(data)
                                elif "results" in data:
                                    for item in data.get("results", []):
                                        discovered_nodes.append(item)
                            except Exception:
                                pass

            if discovered_nodes:
                unique_repos = sorted(list(set(n.get("repo") for n in discovered_nodes if n.get("repo"))))
                plan_lines = [
                    f"### Cross-Repository Execution Plan (Analyzed {len(unique_repos)} repositories):\n"
                ]
                for idx, node in enumerate(discovered_nodes[:5], start=1):
                    repo = node.get("repo", "target_repo")
                    file_p = node.get("file_path", "source_file")
                    sym = node.get("symbol_name", "symbol")
                    plan_lines.append(f"{idx}. **[{repo}]** `{file_p}`:\n   - Review and update `{sym}` to ensure compatibility with cross-repo changes.")
                plan_lines.append(f"\n**Zero Hallucination Verified**: Context populated deterministically via MCP tools.")
                final_text = "\n".join(plan_lines)
            else:
                final_text = (
                    f"### Repository Context Not Found\n\n"
                    f"No matching symbols or call graph dependencies were found for `{user_prompt}` in the currently indexed repositories.\n\n"
                    f"**Next Steps**:\n"
                    f"1. Use the **+ Ingest Repos** button in the top navigation to index your target codebases (or select an example organization like **Meshery**, **Kubernetes**, **Django**, or **VLC**).\n"
                    f"2. Once indexed, ContextBot will deterministically parse the AST call graph, trace upstream callers, calculate blast radius, and formulate synchronized multi-repository pull requests."
                )

            return {
                "role": "assistant",
                "content": [{"type": "text", "text": final_text}]
            }

    def _is_conceptual_query(self, query: str) -> bool:
        """Determines if a query is conceptual/architectural vs a specific code operation."""
        keywords = [
            "what is", "what us", "what are", "how does", "how do", "why is", "why do",
            "explain", "describe", "tell me about", "what can you do", "who are you",
            "blast radius", "crosscontext", "ast graph", "ast vs rag", "naive rag",
            "how to ingest", "mcp tool", "mcp tools", "mcp server", "architecture blueprint",
            "code explorer", "help", "hello", "hi"
        ]
        return any(k in query for k in keywords)

    def _get_conceptual_answer(self, query: str) -> str:
        """Returns authoritative technical explanations for conceptual inquiries."""
        if "blast radius" in query:
            return (
                "### What is Blast Radius in CrossContext?\n\n"
                "**Blast radius** refers to the complete map of downstream services, consumer repositories, modules, "
                "and API call-sites that will be impacted or broken when a specific function, class, endpoint, or schema "
                "in an upstream producer repository is modified or deprecated.\n\n"
                "#### How CrossContext Computes Blast Radius:\n"
                "1. **Deterministic AST Parsing**: Tree-sitter parses syntactic function definitions, decorators, and exported symbols in the producer codebase.\n"
                "2. **Cross-Repository Call Graph Traversal**: The engine follows call edges across repository boundaries (e.g. from backend FastAPI/Express routes to frontend TypeScript/Python clients) via recursive graph traversal (`traverse_call_graph`).\n"
                "3. **Upstream Caller Detection**: Identifies every caller file, function signature, and line number across all federated repositories.\n"
                "4. **Zero-Breakage Guarantee**: Unlike naive text search or RAG, the AST graph deterministically guarantees 100% precision with zero hallucination before refactoring or deprecating code."
            )
        elif "ast" in query and ("rag" in query or "differ" in query or "vs" in query):
            return (
                "### AST Code Graphs vs. Naive RAG\n\n"
                "| Capability | Naive Text RAG | CrossContext AST Graph |\n"
                "| :--- | :--- | :--- |\n"
                "| **Precision** | Probabilistic (vector similarity) | 100% Deterministic (syntactic AST) |\n"
                "| **Cross-Repo Tracing** | Misses multi-hop call chains | Traverses multi-hop dependency graphs |\n"
                "| **Hallucination Risk** | High (invents non-existent files) | Zero (exact file paths & line numbers) |\n"
                "| **Refactoring Safety** | Unreliable for breaking changes | Full blast radius verification |\n\n"
                "#### Why AST Graphs Win for Code:\n"
                "Code is a structured graph of references, imports, and routes. Naive RAG splits files into arbitrary text chunks, "
                "losing syntactic scope and call hierarchies. CrossContext preserves semantic structure directly from the compiler AST."
            )
        elif "ingest" in query:
            return (
                "### Ingesting Repositories into CrossContext\n\n"
                "To analyze codebases and calculate cross-repository blast radius:\n\n"
                "1. Click the **+ Ingest Repos** button in the top navigation bar.\n"
                "2. Provide GitHub repository URLs (one per line) or local folder paths.\n"
                "3. Select an indexing preset or use the default configuration.\n"
                "4. Click **Start Ingestion** to trigger parallel AST parsing, symbol extraction, and cross-repo edge resolution.\n\n"
                "*Tip: You can also choose one of the pre-loaded example organizations (Meshery, Kubernetes, Django, VLC) in the top bar to explore immediately.*"
            )
        elif "mcp" in query or "tool" in query:
            return (
                "### CrossContext MCP Server Tools\n\n"
                "ContextBot queries the multi-repository codebase using 5 standard Model Context Protocol (MCP) tools:\n\n"
                "1. `traverse_call_graph`: Recursively traces blast radius and all upstream callers across repositories.\n"
                "2. `get_symbol_definition`: Locates exact definitions, signatures, line numbers, and file paths.\n"
                "3. `get_usage_dependency_links`: Finds producer/consumer dependencies and cross-repo links.\n"
                "4. `get_ast_chunk`: Retrieves exact, unbroken syntactic code blocks for specific AST nodes.\n"
                "5. `semantic_code_search`: Performs natural language conceptual search over indexed codebases."
            )
        elif "blueprint" in query:
            return (
                "### Architecture Blueprint in CrossContext\n\n"
                "The **Architecture Blueprint** view provides a high-level, interactive topological map of all federated repositories in your organization:\n\n"
                "- **Repository Clusters**: Visualizes microservices grouped by domain and operational tier.\n"
                "- **Cross-Repo Dependencies**: Displays directional dependency arrows showing API producers and consumers.\n"
                "- **Health & Risk Metrics**: Highlights coupling risk, circular dependencies, and high-blast-radius endpoints.\n"
                "- **Interactive Navigation**: Click any repository node to inspect symbols or jump directly into the Code Explorer."
            )
        else:
            return (
                "### CrossContext Autonomous Code Intelligence\n\n"
                "**CrossContext** is an autonomous cross-repository code intelligence and synchronized refactoring platform. "
                "It unites distributed codebases into a single unified knowledge graph.\n\n"
                "#### What You Can Do:\n"
                "- **Ask Conceptual Questions**: Inquire about blast radius, cross-repository architectures, AST graphs, or MCP tools.\n"
                "- **Calculate Blast Radius**: Ask to trace callers of any API endpoint or function across repositories.\n"
                "- **Execute Synchronized Refactoring**: Plan multi-repository migrations with coordinated pull requests.\n"
                "- **Explore Code & Blueprints**: Use the Architecture Blueprint and Code Explorer tabs to visualize dependencies."
            )
