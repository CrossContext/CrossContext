"""
CrossContext - Autonomous Code Graph Agent Loop
Orchestrates multi-turn cross-repository reasoning using AWS Strands pattern.
"""

import time
import json
from typing import Dict, Any, List, Optional, Callable

from agent_orchestrator.model_provider import ModelProvider
from agent_orchestrator.hooks import LifecycleGuardrails
from agent_orchestrator.session_manager import SessionManager
from mcp_server.tools import CodeGraphToolManager


SYSTEM_PROMPT = """
You are CrossContext Agent, an autonomous platform engineer specialized in cross-repository architectures.
Your objective is to solve multi-repository code deprecation, refactoring, and dependency problems.

You have access to a deterministic Code Graph MCP server with the following capabilities:
1. `traverse_call_graph`: Discover blast radius and upstream callers across repos.
2. `get_symbol_definition`: Find where an endpoint or function is defined.
3. `get_usage_dependency_links`: Identify who imports or calls a symbol across repos.
4. `get_ast_chunk`: Retrieve exact, unbroken syntactic function/class code.
5. `semantic_code_search`: Search code with natural language concepts.

Guidelines:
- Never guess file contents or rely on naive text matching.
- Always verify cross-repository callers before suggesting breaking API changes.
- Formulate a precise, actionable migration plan detailing both producer and consumer repositories.
"""

# Bedrock Claude-compatible tool schemas for all 5 MCP tools
TOOLS_SCHEMA = [
    {
        "name": "traverse_call_graph",
        "description": "Traces the full blast radius of a symbol across all repositories. Returns upstream consumers and downstream dependencies.",
        "input_schema": {
            "type": "object",
            "properties": {
                "root_symbol": {"type": "string", "description": "Starting symbol name (e.g., 'verify_legacy_auth')"},
                "max_depth": {"type": "integer", "description": "Maximum recursion hops (default: 3)", "default": 3}
            },
            "required": ["root_symbol"]
        }
    },
    {
        "name": "get_symbol_definition",
        "description": "Locates the exact definition, line numbers, and code of a function, class, or endpoint across all repositories.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol_name": {"type": "string", "description": "Name of function, class, or endpoint"},
                "repo": {"type": "string", "description": "Optional repository filter"}
            },
            "required": ["symbol_name"]
        }
    },
    {
        "name": "get_usage_dependency_links",
        "description": "Returns all upstream callers and downstream consumers that depend on this symbol across repository boundaries.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol_name_or_id": {"type": "string", "description": "Symbol name or unique node ID"}
            },
            "required": ["symbol_name_or_id"]
        }
    },
    {
        "name": "get_ast_chunk",
        "description": "Retrieves the complete unbroken AST code block for a symbol by node ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "node_id": {"type": "string", "description": "Deterministic node ID (e.g., 'repo_auth_core:src/api/auth.py:verify_legacy_auth:24')"}
            },
            "required": ["node_id"]
        }
    },
    {
        "name": "semantic_code_search",
        "description": "Searches codebases using natural language intent via dense vector embeddings.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Conceptual search query (e.g., 'JWT token verification')"},
                "repo": {"type": "string", "description": "Optional repository filter"},
                "limit": {"type": "integer", "description": "Number of results (default: 5)", "default": 5}
            },
            "required": ["query"]
        }
    }
]


class CrossContextAgent:
    def __init__(self, db_path: str = "data/crosscontext_graph.db"):
        self.model_provider = ModelProvider()
        self.tool_manager = CodeGraphToolManager(db_path=db_path)
        self.session_manager = SessionManager()
        self._tool_dispatch = {
            "traverse_call_graph": lambda args: self.tool_manager.traverse_call_graph(
                args.get("root_symbol", ""), args.get("max_depth", 3)
            ),
            "get_symbol_definition": lambda args: self.tool_manager.get_symbol_definition(
                args.get("symbol_name", ""), args.get("repo")
            ),
            "get_usage_dependency_links": lambda args: self.tool_manager.get_usage_dependency_links(
                args.get("symbol_name_or_id", "")
            ),
            "get_ast_chunk": lambda args: self.tool_manager.get_ast_chunk(
                args.get("node_id", "")
            ),
            "semantic_code_search": lambda args: self.tool_manager.semantic_code_search(
                args.get("query", ""), args.get("repo"), args.get("limit", 5)
            ),
        }

    async def run(
        self,
        prompt: str,
        session_id: Optional[str] = None,
        repos: Optional[List[str]] = None,
        telemetry_callback: Optional[Callable[[str, Any], None]] = None
    ) -> Dict[str, Any]:
        """
        Executes the autonomous reasoning loop over multi-repo code context.
        """
        start_time = time.time()
        guardrails = LifecycleGuardrails(max_tool_calls=8, token_budget=12000)

        if session_id:
            self.session_manager.add_message(session_id, "user", prompt)
            messages = self.session_manager.get_context_for_model(session_id)
        else:
            messages = [
                {"role": "user", "content": prompt}
            ]

        turns_executed = 0
        final_answer = ""
        nodes_touched = set()

        while turns_executed < 6:
            turns_executed += 1
            if telemetry_callback:
                telemetry_callback("thinking", f"Agent reasoning turn #{turns_executed}...")

            # 1. Model inference — pass full tools schema for Bedrock Claude compatibility
            response = self.model_provider.invoke_with_tools(
                system_prompt=SYSTEM_PROMPT,
                messages=messages,
                tools=TOOLS_SCHEMA
            )

            assistant_msg = response
            messages.append(assistant_msg)

            # Check for tool calls
            tool_calls = [
                part for part in assistant_msg.get("content", [])
                if isinstance(part, dict) and part.get("type") == "tool_use"
            ]

            # If no tool calls, model completed reasoning
            if not tool_calls:
                text_parts = [
                    part.get("text", "") for part in assistant_msg.get("content", [])
                    if isinstance(part, dict) and part.get("type") == "text"
                ]
                final_answer = "\n".join(text_parts)
                break

            # Execute tool calls
            tool_results_content = []
            for tc in tool_calls:
                tool_name = tc.get("name")
                tool_args = tc.get("input", {})
                tool_id = tc.get("id")

                if not guardrails.before_tool_call(tool_name, tool_args):
                    if telemetry_callback:
                        telemetry_callback("guardrail", f"Guardrail blocked tool `{tool_name}`")
                    continue

                if telemetry_callback:
                    telemetry_callback("tool_call", f"Invoking MCP tool `{tool_name}` with {tool_args}")

                t_start = time.time()
                handler = self._tool_dispatch.get(tool_name)
                if handler:
                    result = handler(tool_args)
                else:
                    result = {"error": f"Tool '{tool_name}' not recognized."}
                duration_ms = (time.time() - t_start) * 1000.0

                guardrails.after_tool_call(tool_name, tool_args, result, duration_ms)

                if telemetry_callback:
                    telemetry_callback("tool_result", f"`{tool_name}` completed in {duration_ms:.1f}ms")

                if "blast_radius_files" in result:
                    nodes_touched.update(result["blast_radius_files"])
                elif "id" in result:
                    nodes_touched.add(result["id"])

                tool_results_content.append({
                    "type": "tool_result",
                    "tool_use_id": tool_id,
                    "content": json.dumps(result)
                })

            messages.append({
                "role": "user",
                "content": tool_results_content
            })

        total_duration = (time.time() - start_time) * 1000.0
        telemetry = guardrails.get_telemetry()
        telemetry["total_runtime_ms"] = total_duration
        safety_report = guardrails.get_safety_report()

        if session_id and final_answer:
            self.session_manager.add_message(session_id, "assistant", final_answer)

        return {
            "status": "success",
            "prompt": prompt,
            "session_id": session_id,
            "response": final_answer,
            "turns": turns_executed,
            "nodes_touched": list(nodes_touched),
            "telemetry": telemetry,
            "safety_report": safety_report
        }


# Backward-compatibility alias
OmniContextAgent = CrossContextAgent

