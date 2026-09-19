"""
OmniContext - Agent Orchestration Loop Tests
Verifies end-to-end multi-turn reasoning, guardrail enforcement, and telemetry.
"""

import sys
import asyncio
from pathlib import Path

import pytest

# Setup sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from agent_orchestrator.agent import OmniContextAgent
from agent_orchestrator.hooks import LifecycleGuardrails
from mcp_server.parsers.treesitter_engine import TreeSitterEngine
from mcp_server.parsers.scip_indexer import CrossRepoLinker


def _create_seeded_agent() -> OmniContextAgent:
    """Creates an agent with the testbed repositories pre-indexed."""
    agent = OmniContextAgent(":memory:")
    backend_dir = str(PROJECT_ROOT / "testbed" / "repo_auth_core")
    frontend_dir = str(PROJECT_ROOT / "testbed" / "repo_frontend_portal")

    parser = TreeSitterEngine()
    linker = CrossRepoLinker()

    b_nodes, b_edges = parser.parse_directory("repo_auth_core", backend_dir)
    f_nodes, f_edges = parser.parse_directory("repo_frontend_portal", frontend_dir)
    all_nodes = b_nodes + f_nodes
    cross_edges = linker.link_repositories(all_nodes)

    agent.tool_manager.graph_store.insert_nodes(all_nodes)
    agent.tool_manager.graph_store.insert_edges(b_edges + f_edges + cross_edges)

    return agent


@pytest.fixture
def seeded_agent():
    return _create_seeded_agent()


class TestAgentMultiTurnExecution:
    """Tests that the agent completes multi-turn cross-repo queries without infinite loops."""

    def test_agent_completes_deprecation_query(self, seeded_agent):
        """Agent should complete a multi-repo deprecation task and return a final migration plan."""
        result = asyncio.run(seeded_agent.run(
            "Deprecate legacy /v1/auth/verify endpoint and update all downstream frontend consumers to /v2/auth/token."
        ))

        assert result["status"] == "success"
        assert result["turns"] >= 1
        assert result["turns"] <= 6  # Must not run forever
        assert len(result["response"]) > 0  # Must produce a final answer

    def test_agent_mentions_both_repos_in_plan(self, seeded_agent):
        """The migration plan must reference both backend and frontend repositories."""
        result = asyncio.run(seeded_agent.run(
            "Deprecate legacy /v1/auth/verify endpoint and update all downstream frontend consumers."
        ))

        response_lower = result["response"].lower()
        # Agent should mention the backend service
        assert "repo_auth_core" in response_lower or "backend" in response_lower or "auth" in response_lower
        # Agent should mention the frontend consumer
        assert "repo_frontend_portal" in response_lower or "frontend" in response_lower or "consumer" in response_lower

    def test_agent_invokes_tools(self, seeded_agent):
        """Agent must invoke at least one MCP tool during reasoning."""
        result = asyncio.run(seeded_agent.run(
            "What is the blast radius of deprecating verify_legacy_auth?"
        ))

        assert result["telemetry"]["total_tool_calls"] >= 1
        assert len(result["telemetry"]["tool_sequence"]) >= 1


class TestGuardrailEnforcement:
    """Tests that lifecycle guardrails properly enforce safety limits."""

    def test_token_budget_blocks_execution(self):
        """Guardrail should block tool calls when token budget is exhausted."""
        guardrails = LifecycleGuardrails(max_tool_calls=10, token_budget=50)

        # Simulate a tool call that consumes a huge result (exceeding budget)
        assert guardrails.before_tool_call("traverse_call_graph", {"root_symbol": "test"}) is True

        # Inject a large result to exhaust the budget
        large_result = {"data": "x" * 500}  # ~125 tokens at 4 chars/token
        guardrails.after_tool_call("traverse_call_graph", {"root_symbol": "test"}, large_result, 1.0)

        # Next call should be blocked by token budget
        assert guardrails.before_tool_call("get_symbol_definition", {"symbol_name": "foo"}) is False

        # Verify trigger was recorded
        report = guardrails.get_safety_report()
        assert report["guardrails_triggered"] is True
        assert any(t["type"] == "token_budget_exceeded" for t in report["triggers"])

    def test_cycle_detection_blocks_repeated_calls(self):
        """Guardrail should detect and block duplicate identical tool calls."""
        guardrails = LifecycleGuardrails(max_tool_calls=20, token_budget=100000)

        call_args = {"root_symbol": "verify_legacy_auth"}
        small_result = {"found": True}

        # First two identical calls should pass
        assert guardrails.before_tool_call("traverse_call_graph", call_args) is True
        guardrails.after_tool_call("traverse_call_graph", call_args, small_result, 0.5)

        assert guardrails.before_tool_call("traverse_call_graph", call_args) is True
        guardrails.after_tool_call("traverse_call_graph", call_args, small_result, 0.5)

        # Third identical call should be blocked (cycle detection threshold = 2)
        assert guardrails.before_tool_call("traverse_call_graph", call_args) is False

        report = guardrails.get_safety_report()
        assert any(t["type"] == "cycle_detected" for t in report["triggers"])

    def test_max_tool_calls_limit(self):
        """Guardrail should block after max_tool_calls is reached."""
        guardrails = LifecycleGuardrails(max_tool_calls=3, token_budget=100000)

        for i in range(3):
            assert guardrails.before_tool_call("get_symbol_definition", {"symbol_name": f"sym_{i}"}) is True
            guardrails.after_tool_call("get_symbol_definition", {"symbol_name": f"sym_{i}"}, {"found": True}, 0.5)

        # 4th call should be blocked
        assert guardrails.before_tool_call("get_symbol_definition", {"symbol_name": "sym_3"}) is False

    def test_safety_report_all_clear(self):
        """Safety report should indicate all_clear when no guardrails triggered."""
        guardrails = LifecycleGuardrails()

        assert guardrails.before_tool_call("get_symbol_definition", {"symbol_name": "test"}) is True
        guardrails.after_tool_call("get_symbol_definition", {"symbol_name": "test"}, {"found": True}, 1.0)

        report = guardrails.get_safety_report()
        assert report["all_clear"] is True
        assert report["trigger_count"] == 0


class TestTelemetryCallback:
    """Tests that the telemetry callback receives expected events."""

    def test_telemetry_callback_receives_events(self, seeded_agent):
        """Telemetry callback should receive thinking, tool_call, and tool_result events."""
        events = []

        def callback(event_type, msg):
            events.append({"type": event_type, "msg": msg})

        asyncio.run(seeded_agent.run(
            "What is the blast radius of verify_legacy_auth?",
            telemetry_callback=callback
        ))

        event_types = [e["type"] for e in events]
        assert "thinking" in event_types  # Agent must enter thinking phase
        assert "tool_call" in event_types  # Agent must invoke at least one tool
        assert "tool_result" in event_types  # Agent must receive tool results


class TestSessionManager:
    """Tests for multi-turn session persistence, sliding window truncation, and compaction."""

    def test_session_creation_and_sliding_window(self):
        from agent_orchestrator.session_manager import SessionManager
        sm = SessionManager(max_messages=4, max_tokens_estimate=500)
        session_id = "test-session-1"

        sm.add_message(session_id, "user", "Hello 1")
        sm.add_message(session_id, "assistant", "Response 1")
        sm.add_message(session_id, "user", "Hello 2")
        sm.add_message(session_id, "assistant", "Response 2")
        assert len(sm.get_messages(session_id)) == 4

        # Adding 5th message should trigger sliding window truncation
        sm.add_message(session_id, "user", "Hello 3")
        messages = sm.get_messages(session_id)
        assert len(messages) == 4
        assert messages[-1]["content"] == "Hello 3"

        # Context for model should include summary of truncated history
        context = sm.get_context_for_model(session_id)
        assert len(context) == 5  # 1 summary message + 4 messages
        assert "[Prior conversation summary]" in context[0]["content"]

    def test_session_compaction_on_token_limit(self):
        from agent_orchestrator.session_manager import SessionManager
        # Low token estimate to trigger compaction
        sm = SessionManager(max_messages=10, max_tokens_estimate=50)
        session_id = "test-session-2"

        # Add multiple messages totaling > 50 tokens
        for i in range(4):
            sm.add_message(session_id, "user", f"Message {i}: " + "A" * 100)
        session = sm.get_session(session_id)
        assert session is not None
        assert len(session["summaries"]) >= 1

    def test_agent_multi_turn_with_session(self, seeded_agent):
        """Verify agent maintains conversation context across multiple turns using session_id."""
        session_id = "judge-demo-session"

        # Turn 1
        res1 = asyncio.run(seeded_agent.run(
            "What is the blast radius of verify_legacy_auth?",
            session_id=session_id
        ))
        assert res1["status"] == "success"
        assert res1["session_id"] == session_id

        # Check session manager holds messages
        history = seeded_agent.session_manager.get_messages(session_id)
        assert len(history) >= 2  # user prompt + assistant response

        # Turn 2
        res2 = asyncio.run(seeded_agent.run(
            "Which frontend files are affected?",
            session_id=session_id
        ))
        assert res2["status"] == "success"
        assert res2["session_id"] == session_id
        history2 = seeded_agent.session_manager.get_messages(session_id)
        assert len(history2) >= 4
