"""
OmniContext - Telemetry & Safety Report Viewer
Renders execution metrics, tool sequence timelines, and guardrail status
indicators in the Streamlit dashboard.
"""

from typing import Dict, Any, Optional
import streamlit as st


def render_telemetry_panel(result: Dict[str, Any]):
    """
    Renders the agent execution telemetry metrics panel.

    Args:
        result: The full agent.run() output dict containing telemetry and safety_report.
    """
    telemetry = result.get("telemetry", {})
    turns = result.get("turns", 0)

    # --- KPI Metrics Row ---
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="⚡ Total Runtime",
            value=f"{telemetry.get('total_runtime_ms', 0):.0f}ms"
        )
    with col2:
        st.metric(
            label="🔧 Tool Calls",
            value=telemetry.get("total_tool_calls", 0),
            delta=f"of {8} max"
        )
    with col3:
        utilization = telemetry.get("budget_utilization_pct", 0)
        st.metric(
            label="📊 Token Budget Used",
            value=f"{utilization}%",
            delta=f"{telemetry.get('approx_tokens_used', 0)} tokens"
        )
    with col4:
        st.metric(
            label="🔄 Reasoning Turns",
            value=turns
        )

    # --- Tool Sequence Timeline ---
    tool_sequence = telemetry.get("tool_sequence", [])
    if tool_sequence:
        st.markdown("#### 🛠️ Tool Invocation Sequence")

        for i, tool_name in enumerate(tool_sequence):
            tool_data = telemetry.get("tool_call_history", [{}])
            emoji = _tool_emoji(tool_name)
            st.markdown(
                f"**Step {i + 1}** {emoji} `{tool_name}`"
            )

    # --- Blast Radius Summary ---
    repos_in_blast = telemetry.get("repos_in_blast_radius", [])
    files_in_blast = telemetry.get("files_in_blast_radius", 0)

    if repos_in_blast or files_in_blast:
        st.markdown("#### 💥 Blast Radius")
        col_a, col_b = st.columns(2)
        with col_a:
            st.metric("Repos Affected", len(repos_in_blast))
            if repos_in_blast:
                for repo in repos_in_blast:
                    st.markdown(f"- `{repo}`")
        with col_b:
            st.metric("Files Affected", files_in_blast)

    # --- Tool Latency ---
    total_latency = telemetry.get("total_tool_latency_ms", 0)
    if total_latency > 0:
        st.caption(f"Total MCP tool latency: {total_latency:.1f}ms")


def render_safety_report(result: Dict[str, Any]):
    """
    Renders guardrail safety indicators with color-coded status.

    Args:
        result: The full agent.run() output dict containing safety_report.
    """
    safety = result.get("safety_report", {})
    if not safety:
        st.info("No safety data available.")
        return

    all_clear = safety.get("all_clear", True)

    # --- Status Header ---
    if all_clear:
        st.success("✅ All guardrails passed — no limits were triggered.")
    else:
        trigger_count = safety.get("trigger_count", 0)
        st.warning(f"⚠️ {trigger_count} guardrail(s) triggered during execution.")

    # --- Limits vs. Usage Comparison ---
    limits = safety.get("limits", {})
    usage = safety.get("usage", {})

    if limits and usage:
        st.markdown("#### 📏 Guardrail Limits vs. Usage")

        data_rows = [
            ("Tool Calls", usage.get("tool_calls_used", 0), limits.get("max_tool_calls", 8)),
            ("Token Budget", usage.get("tokens_used", 0), limits.get("token_budget", 12000)),
            ("Repos Touched", usage.get("repos_touched", 0), limits.get("max_blast_radius_repos", 10)),
            ("Files Touched", usage.get("files_touched", 0), limits.get("max_blast_radius_files", 50)),
        ]

        for label, used, limit in data_rows:
            pct = (used / max(limit, 1)) * 100
            status = "🟢" if pct < 80 else ("🟡" if pct < 100 else "🔴")
            st.markdown(f"{status} **{label}**: {used} / {limit} ({pct:.0f}%)")

    # --- Trigger Details ---
    triggers = safety.get("triggers", [])
    if triggers:
        st.markdown("#### 🚨 Trigger Events")
        for t in triggers:
            st.error(f"**{t['type']}** — {t['message']}")


def render_agent_response(result: Dict[str, Any]):
    """Renders the agent's final response with expandable details."""

    status = result.get("status", "unknown")
    response = result.get("response", "")

    if status == "success" and response:
        st.markdown("### 📋 Agent Response")
        st.markdown(response)
    elif not response:
        st.warning("Agent did not produce a final text response (may have been blocked by guardrails).")

    # Nodes touched
    nodes = result.get("nodes_touched", [])
    if nodes:
        with st.expander(f"🔗 {len(nodes)} Node(s) Touched", expanded=False):
            for node_ref in nodes:
                st.code(node_ref, language=None)


def _tool_emoji(tool_name: str) -> str:
    """Returns a contextual emoji for a tool name."""
    mapping = {
        "traverse_call_graph": "🔀",
        "get_symbol_definition": "📍",
        "get_usage_dependency_links": "🔗",
        "get_ast_chunk": "🧩",
        "semantic_code_search": "🔍",
    }
    return mapping.get(tool_name, "🔧")
