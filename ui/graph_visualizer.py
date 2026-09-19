"""OmniContext / CrossContext - Interactive Cross-Repository Graph Visualizer.

Renders an interactive physics-driven dependency graph using embedded Vis.js HTML5 canvas.
Supports node dragging, zooming, hovering tooltips, clustering by repository,
and highlighting cross-repository API consumption edges.
"""

from typing import List, Dict, Any, Optional
import json
import streamlit as st
import streamlit.components.v1 as components


# Accessible vibrant palette for repositories
REPO_COLORS = [
    {"bg": "#1E3A8A", "border": "#3B82F6", "highlight": "#60A5FA"},  # Blue
    {"bg": "#064E3B", "border": "#10B981", "highlight": "#34D399"},  # Emerald
    {"bg": "#78350F", "border": "#F59E0B", "highlight": "#FBBF24"},  # Amber
    {"bg": "#831843", "border": "#EC4899", "highlight": "#F472B6"},  # Pink
    {"bg": "#4C1D95", "border": "#8B5CF6", "highlight": "#A78BFA"},  # Violet
    {"bg": "#134E4A", "border": "#14B8A6", "highlight": "#2DD4BF"},  # Teal
    {"bg": "#7C2D12", "border": "#F97316", "highlight": "#FB923C"},  # Orange
    {"bg": "#701A75", "border": "#D946EF", "highlight": "#E879F9"},  # Fuchsia
]

SYMBOL_SHAPES = {
    "function": "dot",
    "method": "dot",
    "class": "diamond",
    "endpoint": "star",
    "interface": "triangle",
    "variable": "square",
}

EDGE_STYLES = {
    "consumes_api": {"color": "#EF4444", "width": 3, "dashes": False, "label": "consumes_api (cross-repo)"},
    "calls": {"color": "#60A5FA", "width": 1.5, "dashes": False, "label": "calls"},
    "defines": {"color": "#6B7280", "width": 1, "dashes": [4, 4], "label": "defines"},
    "imports": {"color": "#10B981", "width": 1.5, "dashes": [6, 4], "label": "imports"},
    "inherits": {"color": "#F59E0B", "width": 2, "dashes": False, "label": "inherits"},
}


def _get_repo_color(repo: str, repo_list: List[str]) -> Dict[str, str]:
    """Returns deterministic color scheme for a repository."""
    if repo in repo_list:
        idx = repo_list.index(repo)
    else:
        idx = hash(repo) % len(REPO_COLORS)
    return REPO_COLORS[idx % len(REPO_COLORS)]


def build_legend(repos: List[str]) -> Dict[str, str]:
    """Returns a {repo_name: hex_color} mapping for UI display."""
    return {repo: _get_repo_color(repo, repos)["border"] for repo in repos}


def render_graph(
    nodes_data: List[Dict[str, Any]],
    edges_data: List[Dict[str, Any]],
    selected_repo: Optional[str] = None,
    highlight_node_id: Optional[str] = None,
    height: int = 550,
):
    """Renders the interactive Vis.js graph inside a Streamlit container."""
    if not nodes_data:
        st.info("No symbols indexed yet. Use the sidebar to index repositories.")
        return

    all_repos = sorted(list(set(n.get("repo", "unknown") for n in nodes_data)))

    # Format nodes for Vis.js
    vis_nodes = []
    node_ids = set()

    for n in nodes_data:
        node_id = n["id"]
        if node_id in node_ids:
            continue
        node_ids.add(node_id)

        repo = n.get("repo", "unknown")
        sym_type = n.get("symbol_type", "function")
        sym_name = n.get("symbol_name", "?")
        file_path = n.get("file_path", "")
        start_line = n.get("start_line", 1)

        scheme = _get_repo_color(repo, all_repos)
        shape = SYMBOL_SHAPES.get(sym_type, "dot")
        is_endpoint = sym_type == "endpoint"
        is_highlighted = highlight_node_id and (node_id == highlight_node_id or sym_name == highlight_node_id)

        # Opacity and scaling
        opacity = 1.0
        if selected_repo and repo != selected_repo:
            opacity = 0.35

        border_width = 3 if (is_endpoint or is_highlighted) else 1.5
        size = 28 if is_highlighted else (24 if is_endpoint else 16)

        tooltip = (
            f"<b>{sym_name}</b> ({sym_type})<br/>"
            f"📦 <b>Repo:</b> {repo}<br/>"
            f"📄 <b>File:</b> {file_path}:{start_line}"
        )

        vis_nodes.append({
            "id": node_id,
            "label": sym_name,
            "title": tooltip,
            "shape": shape,
            "size": size,
            "font": {"color": "#FFFFFF", "size": 13, "face": "Inter, sans-serif"},
            "color": {
                "background": "#F59E0B" if is_highlighted else scheme["bg"],
                "border": "#FFFFFF" if is_highlighted else scheme["border"],
                "highlight": {"background": scheme["highlight"], "border": "#FFFFFF"},
                "hover": {"background": scheme["highlight"], "border": "#FFFFFF"},
            },
            "borderWidth": border_width,
            "opacity": opacity,
            "repo": repo,
            "file_path": file_path,
            "symbol_type": sym_type,
            "start_line": start_line,
        })

    # Format edges for Vis.js
    vis_edges = []
    for e in edges_data:
        caller = e.get("caller_id", "")
        callee = e.get("callee_id", "")
        edge_type = e.get("edge_type", "calls")

        if caller not in node_ids or callee not in node_ids:
            continue

        style = EDGE_STYLES.get(edge_type, EDGE_STYLES["calls"])
        is_cross = edge_type == "consumes_api"

        vis_edges.append({
            "from": caller,
            "to": callee,
            "arrows": "to",
            "label": edge_type if is_cross else "",
            "font": {"color": "#FCA5A5", "size": 10, "align": "middle", "strokeWidth": 0},
            "color": {
                "color": style["color"],
                "highlight": "#EF4444" if is_cross else "#60A5FA",
                "hover": style["color"],
                "opacity": 0.9 if is_cross else 0.6,
            },
            "width": style["width"],
            "dashes": style["dashes"],
            "smooth": {"type": "curvedCW", "roundness": 0.2} if is_cross else {"type": "continuous"},
        })

    nodes_json = json.dumps(vis_nodes)
    edges_json = json.dumps(vis_edges)

    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
        <style type="text/css">
            body {{
                margin: 0;
                padding: 0;
                background-color: #0D1117;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                overflow: hidden;
            }}
            #graph-container {{
                width: 100%;
                height: {height}px;
                border: 1px solid #30363D;
                border-radius: 8px;
                background: radial-gradient(circle at center, #161B22 0%, #0D1117 100%);
            }}
            #controls {{
                position: absolute;
                top: 12px;
                right: 12px;
                z-index: 100;
                display: flex;
                gap: 8px;
            }}
            .graph-btn {{
                background: #21262D;
                border: 1px solid #30363D;
                color: #C9D1D9;
                padding: 6px 12px;
                border-radius: 6px;
                font-size: 12px;
                cursor: pointer;
                transition: all 0.2s;
            }}
            .graph-btn:hover {{
                background: #30363D;
                border-color: #58A6FF;
                color: #58A6FF;
            }}
            #node-info-card {{
                position: absolute;
                bottom: 12px;
                left: 12px;
                background: rgba(22, 27, 34, 0.95);
                border: 1px solid #30363D;
                border-left: 4px solid #F97316;
                border-radius: 6px;
                padding: 10px 14px;
                color: #C9D1D9;
                font-size: 12px;
                max-width: 380px;
                backdrop-filter: blur(4px);
                display: none;
                z-index: 100;
            }}
            #node-info-title {{
                font-weight: bold;
                color: #FFFFFF;
                font-size: 13px;
                margin-bottom: 4px;
            }}
        </style>
    </head>
    <body>
        <div id="graph-container"></div>
        <div id="controls">
            <button class="graph-btn" onclick="network.fit({{animation: true}})">🔍 Fit View</button>
            <button class="graph-btn" onclick="togglePhysics()">⚡ Toggle Physics</button>
        </div>
        <div id="node-info-card">
            <div id="node-info-title">Symbol Details</div>
            <div id="node-info-body">Click any node to inspect metadata.</div>
        </div>

        <script type="text/javascript">
            const rawNodes = {nodes_json};
            const rawEdges = {edges_json};

            const nodes = new vis.DataSet(rawNodes);
            const edges = new vis.DataSet(rawEdges);

            const container = document.getElementById('graph-container');
            const data = {{ nodes: nodes, edges: edges }};

            let physicsEnabled = true;

            const options = {{
                nodes: {{
                    shadow: {{ enabled: true, color: 'rgba(0,0,0,0.5)', size: 8, x: 2, y: 2 }}
                }},
                edges: {{
                    shadow: {{ enabled: true, color: 'rgba(0,0,0,0.3)', size: 4 }},
                    arrows: {{ to: {{ enabled: true, scaleFactor: 0.8 }} }}
                }},
                physics: {{
                    enabled: true,
                    solver: 'forceAtlas2Based',
                    forceAtlas2Based: {{
                        gravitationalConstant: -40,
                        centralGravity: 0.008,
                        springLength: 90,
                        springConstant: 0.12,
                        damping: 0.85
                    }},
                    stabilization: {{ iterations: 120 }}
                }},
                interaction: {{
                    hover: true,
                    tooltipDelay: 100,
                    zoomView: true,
                    dragView: true
                }}
            }};

            const network = new vis.Network(container, data, options);

            const infoCard = document.getElementById('node-info-card');
            const infoTitle = document.getElementById('node-info-title');
            const infoBody = document.getElementById('node-info-body');

            network.on('click', function(params) {{
                if (params.nodes.length > 0) {{
                    const nodeId = params.nodes[0];
                    const node = nodes.get(nodeId);
                    if (node) {{
                        infoTitle.innerHTML = '📌 ' + node.label + ' <span style="color:#58A6FF;">(' + node.symbol_type + ')</span>';
                        infoBody.innerHTML = '<b>Repo:</b> ' + node.repo + '<br/>' +
                                            '<b>File:</b> ' + node.file_path + ':' + node.start_line + '<br/>' +
                                            '<span style="font-family:monospace; color:#8B949E; font-size:10px;">' + node.id + '</span>';
                        infoCard.style.display = 'block';
                    }}
                }} else {{
                    infoCard.style.display = 'none';
                }}
            }});

            function togglePhysics() {{
                physicsEnabled = !physicsEnabled;
                network.setOptions({{ physics: {{ enabled: physicsEnabled }} }});
            }}
        </script>
    </body>
    </html>
    """

    components.html(html_code, height=height + 15)
