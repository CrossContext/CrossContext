"""
CrossContext - Organization Context & AI Blueprint Generator
Analyzes the cross-repository code graph to generate:
1. A visually rich architecture report with dependency metrics for humans.
2. An ultra-compressed, token-optimized context document (.txt) tailored
   specifically for IDEs (Cursor, Claude Code, Windsurf) to give agents
   instant multi-repo awareness without burning token budgets.
"""

from typing import Dict, Any, List, Optional
from collections import defaultdict


class OrgContextGenerator:
    """Generates human-readable and AI-optimized organization context from the code graph."""

    def __init__(self, graph_store):
        self.store = graph_store

    def analyze_organization(self) -> Dict[str, Any]:
        """Analyzes all indexed repositories, symbols, and cross-repo links."""
        nodes = self.store.get_all_nodes()
        edges = self.store.get_all_edges()

        # 1. Repository groupings
        repo_nodes = defaultdict(list)
        repo_files = defaultdict(set)
        repo_languages = defaultdict(lambda: defaultdict(int))

        for n in nodes:
            repo = n.repo
            repo_nodes[repo].append(n)
            repo_files[repo].add(n.file_path)

            ext = n.file_path.split(".")[-1].lower() if "." in n.file_path else "unknown"
            lang_map = {
                "py": "Python",
                "ts": "TypeScript",
                "tsx": "TypeScript/React",
                "js": "JavaScript",
                "go": "Go",
                "java": "Java",
            }
            lang = lang_map.get(ext, ext.upper())
            repo_languages[repo][lang] += 1

        # 2. Cross-repo contract analysis
        node_lookup = {n.id: n for n in nodes}
        cross_repo_edges = []
        internal_edges = []
        repo_dependencies = defaultdict(lambda: defaultdict(int))

        for e in edges:
            caller_id = getattr(e, "caller_id", "") or (e.get("caller_id") if isinstance(e, dict) else "")
            callee_id = getattr(e, "callee_id", "") or (e.get("callee_id") if isinstance(e, dict) else "")
            edge_type = getattr(e, "edge_type", "") or (e.get("edge_type") if isinstance(e, dict) else "")
            if hasattr(edge_type, "value"):
                edge_type = edge_type.value

            caller_node = node_lookup.get(caller_id)
            callee_node = node_lookup.get(callee_id)

            if caller_node and callee_node:
                if caller_node.repo != callee_node.repo:
                    cross_repo_edges.append({
                        "caller_repo": caller_node.repo,
                        "caller_file": caller_node.file_path,
                        "caller_symbol": caller_node.symbol_name,
                        "callee_repo": callee_node.repo,
                        "callee_file": callee_node.file_path,
                        "callee_symbol": callee_node.symbol_name,
                        "edge_type": str(edge_type),
                    })
                    repo_dependencies[caller_node.repo][callee_node.repo] += 1
                else:
                    internal_edges.append(e)

        # 3. Compile repo summaries
        repo_summaries = []
        for repo in sorted(repo_nodes.keys()):
            r_nodes = repo_nodes[repo]
            r_files = sorted(list(repo_files[repo]))
            lang_counts = repo_languages[repo]
            primary_lang = max(lang_counts.items(), key=lambda x: x[1])[0] if lang_counts else "Unknown"

            endpoints = [n for n in r_nodes if getattr(n.symbol_type, "value", str(n.symbol_type)) == "endpoint"]
            classes = [n for n in r_nodes if getattr(n.symbol_type, "value", str(n.symbol_type)) == "class"]
            functions = [n for n in r_nodes if getattr(n.symbol_type, "value", str(n.symbol_type)) in ("function", "method")]

            repo_summaries.append({
                "repo_name": repo,
                "primary_language": primary_lang,
                "total_files": len(r_files),
                "total_symbols": len(r_nodes),
                "endpoints_count": len(endpoints),
                "classes_count": len(classes),
                "functions_count": len(functions),
                "files": r_files,
                "endpoints": [n.symbol_name for n in endpoints],
            })

        return {
            "total_repositories": len(repo_nodes),
            "total_files": sum(len(f) for f in repo_files.values()),
            "total_symbols": len(nodes),
            "total_edges": len(edges),
            "cross_repo_contracts_count": len(cross_repo_edges),
            "repositories": repo_summaries,
            "cross_repo_contracts": cross_repo_edges,
            "repo_dependency_matrix": dict(repo_dependencies),
        }

    def generate_ai_optimized_context(self) -> str:
        """
        Generates an ultra-compressed, deterministic plain text document (.txt)
        optimized specifically for AI agents (Cursor, Claude, Windsurf, VS Code).
        Maximizes information density while keeping token overhead strictly minimal.
        """
        data = self.analyze_organization()
        nodes = self.store.get_all_nodes()

        lines = [
            "# ===================================================================",
            "# CROSSCONTEXT FEDERATED ORGANIZATION CODEBASE BLUEPRINT",
            f"# Generated for Autonomous AI Agents | Total Repositories: {data['total_repositories']}",
            "# ===================================================================",
            "",
            "## 1. REPOSITORY INVENTORY & ARCHITECTURAL ROLES",
        ]

        for r in data["repositories"]:
            lines.append(f"- Repo: `{r['repo_name']}` ({r['primary_language']}) | Files: {r['total_files']} | Symbols: {r['total_symbols']}")
            if r["endpoints"]:
                lines.append(f"  Exported Endpoints: {', '.join(r['endpoints'])}")

        lines.extend([
            "",
            "## 2. CROSS-REPOSITORY API CONTRACT MATRIX",
            "# Format: [Consumer Repo/File] -> (Relationship) -> [Producer Repo/File: Symbol]",
        ])

        if data["cross_repo_contracts"]:
            for c in data["cross_repo_contracts"]:
                lines.append(
                    f"- [{c['caller_repo']}] {c['caller_file']} ({c['caller_symbol']}) "
                    f"--{c['edge_type']}--> "
                    f"[{c['callee_repo']}] {c['callee_file']}: `{c['callee_symbol']}`"
                )
        else:
            lines.append("- No cross-repo edges detected. Repositories operate as isolated modules.")

        lines.extend([
            "",
            "## 3. DETERMINISTIC SYMBOL MAP & AST BOUNDARIES",
            "# Use this index to locate exact functions/classes without full-repo scans.",
        ])

        # Group by repo and file for clean compactness
        by_repo_file = defaultdict(lambda: defaultdict(list))
        for n in nodes:
            sym_type = getattr(n.symbol_type, "value", str(n.symbol_type))
            by_repo_file[n.repo][n.file_path].append(f"`{n.symbol_name}` ({sym_type}: L{n.start_line}-{n.end_line})")

        for repo in sorted(by_repo_file.keys()):
            lines.append(f"\n### `{repo}`")
            for f_path in sorted(by_repo_file[repo].keys()):
                sym_list = ", ".join(by_repo_file[repo][f_path])
                lines.append(f"  - `{f_path}`: {sym_list}")

        lines.extend([
            "",
            "# ===================================================================",
            "# INSTRUCTIONS FOR CODING AGENT:",
            "# 1. When modifying an endpoint, verify all consumer files listed in Section 2.",
            "# 2. Use line numbers in Section 3 to request targeted diffs without reading entire files.",
            "# 3. Never invent cross-repo communication protocols; adhere to contracts in Section 2.",
            "# ===================================================================",
        ])

        return "\n".join(lines)
