"""
OmniContext - Agent Lifecycle Guardrails & Safety Hooks
Protects context window against infinite recursion, cycle traps, and token bloat.
Enforces hard limits on tool call count, token budget, and blast-radius scope.
"""

import time
from typing import Dict, Any, List, Set


class LifecycleGuardrails:
    def __init__(self, max_tool_calls: int = 8, token_budget: int = 12000,
                 max_blast_radius_repos: int = 10, max_blast_radius_files: int = 50):
        self.max_tool_calls = max_tool_calls
        self.token_budget = token_budget
        self.max_blast_radius_repos = max_blast_radius_repos
        self.max_blast_radius_files = max_blast_radius_files
        self.tool_call_history: List[Dict[str, Any]] = []
        self.visited_symbols: Set[str] = set()
        self.approx_tokens_used = 0
        self.repos_touched: Set[str] = set()
        self.files_touched: Set[str] = set()
        self._guardrail_triggers: List[Dict[str, Any]] = []

    def before_tool_call(self, tool_name: str, tool_args: Dict[str, Any]) -> bool:
        """
        Validates safety constraints before executing a tool call.
        Returns True if execution should proceed, False to abort.
        """
        # 1. Enforce max tool calls limit
        if len(self.tool_call_history) >= self.max_tool_calls:
            self._record_trigger("max_tool_calls", f"Budget of {self.max_tool_calls} calls exhausted.")
            return False

        # 2. Token Budget Enforcement — hard block when context is exhausted
        if self.approx_tokens_used >= self.token_budget:
            self._record_trigger("token_budget_exceeded",
                                 f"Token budget exhausted: {self.approx_tokens_used}/{self.token_budget} tokens used.")
            return False

        # 3. Cycle Detection: Check for duplicate identical tool calls
        call_signature = f"{tool_name}:{str(sorted(tool_args.items()))}"
        past_signatures = [f"{c['name']}:{str(sorted(c['args'].items()))}" for c in self.tool_call_history]
        if past_signatures.count(call_signature) >= 2:
            self._record_trigger("cycle_detected",
                                 f"Duplicate recursive call detected for '{tool_name}'. Breaking cycle.")
            return False

        # 4. Blast-radius scope check — warn if traversal is spanning too many repos/files
        if len(self.repos_touched) > self.max_blast_radius_repos:
            self._record_trigger("blast_radius_repos",
                                 f"Blast radius spans {len(self.repos_touched)} repos (limit: {self.max_blast_radius_repos}).")
            return False

        if len(self.files_touched) > self.max_blast_radius_files:
            self._record_trigger("blast_radius_files",
                                 f"Blast radius spans {len(self.files_touched)} files (limit: {self.max_blast_radius_files}).")
            return False

        return True

    def after_tool_call(self, tool_name: str, tool_args: Dict[str, Any], result: Any, duration_ms: float):
        """Records telemetry and updates blast-radius tracking after tool completes."""
        self.tool_call_history.append({
            "name": tool_name,
            "args": tool_args,
            "duration_ms": duration_ms,
            "timestamp": time.time()
        })

        # Approximate token consumption tracking (~4 chars per token)
        result_str = str(result)
        self.approx_tokens_used += len(result_str) // 4

        # Track blast-radius scope from tool results
        if isinstance(result, dict):
            # Extract repos and files from blast-radius results
            for file_ref in result.get("blast_radius_files", []):
                self.files_touched.add(file_ref)
                if ":" in file_ref:
                    self.repos_touched.add(file_ref.split(":")[0])

            # Track individual symbol lookups
            if "repo" in result:
                self.repos_touched.add(result["repo"])
            for sym in result.get("symbols", []):
                if isinstance(sym, dict) and "repo" in sym:
                    self.repos_touched.add(sym["repo"])
            for caller in result.get("upstream_callers", []):
                if isinstance(caller, dict) and "repo" in caller:
                    self.repos_touched.add(caller["repo"])

    def _record_trigger(self, trigger_type: str, message: str):
        """Records a guardrail trigger event for safety reporting."""
        print(f"[Guardrails] {message}")
        self._guardrail_triggers.append({
            "type": trigger_type,
            "message": message,
            "timestamp": time.time(),
            "tool_calls_at_trigger": len(self.tool_call_history),
            "tokens_at_trigger": self.approx_tokens_used
        })

    def get_telemetry(self) -> Dict[str, Any]:
        """Returns execution telemetry metrics."""
        return {
            "total_tool_calls": len(self.tool_call_history),
            "approx_tokens_used": self.approx_tokens_used,
            "token_budget": self.token_budget,
            "budget_utilization_pct": round((self.approx_tokens_used / max(self.token_budget, 1)) * 100, 1),
            "tool_sequence": [c["name"] for c in self.tool_call_history],
            "total_tool_latency_ms": sum(c["duration_ms"] for c in self.tool_call_history),
            "repos_in_blast_radius": sorted(list(self.repos_touched)),
            "files_in_blast_radius": len(self.files_touched)
        }

    def get_safety_report(self) -> Dict[str, Any]:
        """Returns a structured safety report for UI display and auditing."""
        return {
            "guardrails_triggered": len(self._guardrail_triggers) > 0,
            "trigger_count": len(self._guardrail_triggers),
            "triggers": self._guardrail_triggers,
            "limits": {
                "max_tool_calls": self.max_tool_calls,
                "token_budget": self.token_budget,
                "max_blast_radius_repos": self.max_blast_radius_repos,
                "max_blast_radius_files": self.max_blast_radius_files
            },
            "usage": {
                "tool_calls_used": len(self.tool_call_history),
                "tokens_used": self.approx_tokens_used,
                "repos_touched": len(self.repos_touched),
                "files_touched": len(self.files_touched)
            },
            "all_clear": len(self._guardrail_triggers) == 0
        }
