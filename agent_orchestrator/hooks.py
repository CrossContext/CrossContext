"""
OmniContext - Agent Lifecycle Guardrails & Safety Hooks
Protects context window against infinite recursion, cycle traps, and token bloat.
"""

import time
from typing import Dict, Any, List, Set


class LifecycleGuardrails:
    def __init__(self, max_tool_calls: int = 8, token_budget: int = 12000):
        self.max_tool_calls = max_tool_calls
        self.token_budget = token_budget
        self.tool_call_history: List[Dict[str, Any]] = []
        self.visited_symbols: Set[str] = set()
        self.approx_tokens_used = 0

    def before_tool_call(self, tool_name: str, tool_args: Dict[str, Any]) -> bool:
        """
        Validates safety constraints before executing a tool call.
        Returns True if execution should proceed, False to abort.
        """
        # 1. Enforce max tool calls limit
        if len(self.tool_call_history) >= self.max_tool_calls:
            print(f"[Guardrails] Max tool call budget ({self.max_tool_calls}) reached. Breaking loop.")
            return False

        # 2. Cycle Detection: Check for duplicate identical tool calls
        call_signature = f"{tool_name}:{str(sorted(tool_args.items()))}"
        past_signatures = [f"{c['name']}:{str(sorted(c['args'].items()))}" for c in self.tool_call_history]
        if past_signatures.count(call_signature) >= 2:
            print(f"[Guardrails] Duplicate recursive call detected for '{tool_name}'. Breaking cycle.")
            return False

        return True

    def after_tool_call(self, tool_name: str, tool_args: Dict[str, Any], result: Any, duration_ms: float):
        """Records telemetry after tool completes."""
        self.tool_call_history.append({
            "name": tool_name,
            "args": tool_args,
            "duration_ms": duration_ms,
            "timestamp": time.time()
        })
        # Approximate token consumption tracking (~4 chars per token)
        result_str = str(result)
        self.approx_tokens_used += len(result_str) // 4

    def get_telemetry(self) -> Dict[str, Any]:
        return {
            "total_tool_calls": len(self.tool_call_history),
            "approx_tokens_used": self.approx_tokens_used,
            "token_budget": self.token_budget,
            "tool_sequence": [c["name"] for c in self.tool_call_history],
            "total_tool_latency_ms": sum(c["duration_ms"] for c in self.tool_call_history)
        }
