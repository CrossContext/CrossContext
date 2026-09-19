"""
OmniContext - Interactive Cross-Repo Graph Visualizer
Renders the code dependency graph using streamlit-agraph with color-coded nodes
and labeled edges for the hackathon dashboard.
"""

from typing import List, Dict, Any, Optional, Tuple
try:
    from streamlit_agraph import agraph, Node, Edge, Config
    AGRAPH_AVAILABLE = True
except ImportError:
    AGRAPH_AVAILABLE = False


# Color palette: each repository gets a distinct, accessible color
REPO_COLORS = [
    "#3B82F6",  # Blue
    "#10B981",  # Emerald  
    "#F59E0B",  # Amber
    "#EF4444",  # Red
    "#8B5CF6",  # Violet
    "#EC4899",  # Pink
    "#14B8A6",  # Teal
    "#F97316",  # Orange
]

SYMBOL_TYPE_SHAPES = {
    "function": "dot",
    "method": "dot",
    "class": "diamond",
    "endpoint": "star",
    "interface": "triangle",
}

EDGE_TYPE_COLORS = {
    "calls": "#6B7280",
    "defines": "#9CA3AF",
    "consumes_api": "#EF4444",
    "imports": "#3B82F6",
}


def _get_repo_color(repo: str, repo_list: List[str]) -> str:
    """Returns a deterministic color for a repository."""
    if repo in repo_list:
        idx = repo_list.index(repo)
    else:
        idx = hash(repo) % len(REPO_COLORS)
    return REPO_COLORS[idx % len(REPO_COLORS)]


def build_agraph(
    nodes_data: List[Dict[str, Any]],
    edges_data: List[Dict[str, Any]],
    selected_repo: Optional[str] = None,
    height: int = 500,
) -> Tuple[List[Node], List[Edge], Config]:
    """
    Builds streamlit-agraph components from raw node/edge data.
    
    Args:
        nodes_data: List of dicts with keys: id, symbol_name, symbol_type, repo, file_path
        edges_data: List of dicts with keys: caller_id, callee_id, edge_type
        selected_repo: Optional filter to highlight nodes from a specific repo
        height: Graph canvas height in pixels

    Returns:
        Tuple of (agraph_nodes, agraph_edges, agraph_config) ready for `agraph()` call.
    """
    # Collect unique repos for color assignment
    all_repos = sorted(set(n.get("repo", "unknown") for n in nodes_data))

    ag_nodes = []
    node_ids = set()

    for n in nodes_data:
        node_id = n["id"]
        if node_id in node_ids:
            continue
        node_ids.add(node_id)

        repo = n.get("repo", "unknown")
        sym_type = n.get("symbol_type", "function")
        symbol_name = n.get("symbol_name", "?")
        file_path = n.get("file_path", "")

        color = _get_repo_color(repo, all_repos)
        shape = SYMBOL_TYPE_SHAPES.get(sym_type, "dot")

        # Dim nodes from other repos when a filter is active
        opacity = 1.0
        if selected_repo and repo != selected_repo:
            opacity = 0.3

        label = symbol_name
        title = (
            f"📦 {repo}\n"
            f"📄 {file_path}\n"
            f"🏷️ {sym_type}\n"
            f"🔑 {node_id}"
        )

        ag_nodes.append(Node(
            id=node_id,
            label=label,
            title=title,
            size=22 if sym_type == "endpoint" else 16,
            color=color,
            shape=shape,
            opacity=opacity,
        ))

    ag_edges = []
    for e in edges_data:
        caller = e.get("caller_id", "")
        callee = e.get("callee_id", "")
        edge_type = e.get("edge_type", "calls")

        # Only render edges where both endpoints exist in our node set
        if caller not in node_ids or callee not in node_ids:
            continue

        edge_color = EDGE_TYPE_COLORS.get(edge_type, "#9CA3AF")
        is_cross_repo = edge_type == "consumes_api"

        ag_edges.append(Edge(
            source=caller,
            target=callee,
            label=edge_type.replace("_", " "),
            color=edge_color,
            width=3 if is_cross_repo else 1.5,
            type="CURVE_SMOOTH" if is_cross_repo else "STRAIGHT",
        ))

    config = Config(
        width="100%",
        height=height,
        directed=True,
        physics=True,
        hierarchical=False,
        nodeHighlightBehavior=True,
        highlightColor="#F59E0B",
        collapsible=False,
        node={"labelProperty": "label"},
        link={"labelProperty": "label", "renderLabel": True},
    )

    return ag_nodes, ag_edges, config


def render_graph(
    nodes_data: List[Dict[str, Any]],
    edges_data: List[Dict[str, Any]],
    selected_repo: Optional[str] = None,
    height: int = 500,
):
    """Renders the interactive graph directly into the Streamlit app."""
    import streamlit as st
    if not AGRAPH_AVAILABLE:
        st.info("Interactive agraph unavailable. Visualizing symbols in table below.")
        return

    ag_nodes, ag_edges, config = build_agraph(
        nodes_data, edges_data, selected_repo=selected_repo, height=height
    )

    if not ag_nodes:
        import streamlit as st
        st.info("No symbols indexed yet. Use the sidebar to index repositories first.")
        return

    return agraph(nodes=ag_nodes, edges=ag_edges, config=config)


def build_legend(repos: List[str]) -> Dict[str, str]:
    """Returns a {repo_name: hex_color} mapping for display as a legend."""
    return {repo: _get_repo_color(repo, repos) for repo in repos}
