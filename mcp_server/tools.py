"""Deterministic Code Graph Query Tools for OmniContext MCP Server.

Provides autonomous coding agents with exact, verifiable, AST-level code navigation,
dependency tracing, and blast-radius analysis across multi-repository architectures.
"""

from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from common.models import CodeNode, CodeEdge, TraversalResult, BlastRadiusReport
from mcp_server.storage.sqlite_graph import SQLiteGraphStorage


class CodeGraphTools:
    """Tool execution harness for CodeGraph MCP Server."""

    def __init__(self, storage: Optional[SQLiteGraphStorage] = None):
        self.storage = storage or SQLiteGraphStorage()

    def find_symbol_definition(self, symbol_name: str, repo: Optional[str] = None) -> Dict[str, Any]:
        """Finds the precise definition, file path, line bounds, and AST content of a symbol.

        Args:
            symbol_name: The name of the function, class, endpoint, or variable.
            repo: Optional repository name to narrow the search.
        """
        nodes = self.storage.find_nodes_by_symbol(symbol_name, repo)
        if not nodes:
            # Try FTS search if exact symbol name not found
            fts_matches = self.storage.search_nodes_fts(symbol_name, repo, limit=3)
            if fts_matches:
                nodes = fts_matches

        return {
            "query_symbol": symbol_name,
            "repo_filter": repo,
            "found_count": len(nodes),
            "definitions": [n.model_dump() for n in nodes],
        }

    def get_usage_dependency_links(self, symbol_id: str) -> Dict[str, Any]:
        """Finds all direct callers, consumers, and dependencies of a symbol across repositories.

        Args:
            symbol_id: Unique symbol ID or symbol name.
        """
        # Resolve node if symbol_name was passed
        node = self.storage.get_node_by_id(symbol_id)
        if not node:
            matches = self.storage.find_nodes_by_symbol(symbol_id)
            if matches:
                node = matches[0]

        if not node:
            return {"error": f"Symbol or Node '{symbol_id}' not found in code graph."}

        callers = self.storage.get_callers(node.id)
        callees = self.storage.get_callees(node.id)
        edges = self.storage.get_edges_for_node(node.id, direction="both")

        return {
            "target_node": node.model_dump(),
            "direct_callers": [c.model_dump() for c in callers],
            "direct_callees": [c.model_dump() for c in callees],
            "cross_repo_callers": [c.model_dump() for c in callers if c.repo != node.repo],
            "edges": [e.model_dump() for e in edges],
            "total_dependencies": len(callers) + len(callees),
        }

    def traverse_call_graph(
        self, entry_symbol: str, depth: int = 2, direction: str = "both", repo: Optional[str] = None
    ) -> Dict[str, Any]:
        """Traces the multi-hop dependency graph starting from an entry symbol.

        Args:
            entry_symbol: Function, class, or endpoint to start traversal from.
            depth: Maximum traversal hops (default 2).
            direction: 'downstream' (callers), 'upstream' (callees), or 'both'.
            repo: Optional repository filter for entry point.
        """
        result: TraversalResult = self.storage.traverse_graph(
            entry_symbol=entry_symbol, depth=depth, direction=direction, repo=repo
        )
        return result.model_dump()

    def get_ast_chunk(
        self, file_path: str, start_line: int, end_line: int, repo: Optional[str] = None
    ) -> Dict[str, Any]:
        """Retrieves exact, unbroken structural code chunk between specified line bounds.

        Args:
            file_path: Relative or absolute path to the file.
            start_line: 1-indexed starting line.
            end_line: 1-indexed ending line.
            repo: Optional repository identifier.
        """
        path = Path(file_path)
        if not path.is_file():
            # Search in database for node with matching file_path
            all_nodes = self.storage.get_all_nodes(repo=repo)
            for n in all_nodes:
                if n.file_path == file_path or n.file_path.endswith(file_path):
                    if n.code_content:
                        return {
                            "file_path": n.file_path,
                            "repo": n.repo,
                            "start_line": n.start_line,
                            "end_line": n.end_line,
                            "code": n.code_content,
                            "symbol_name": n.symbol_name,
                        }

            return {"error": f"File '{file_path}' could not be located on disk or in graph storage."}

        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            slice_lines = lines[max(0, start_line - 1) : min(len(lines), end_line)]
            return {
                "file_path": file_path,
                "start_line": start_line,
                "end_line": end_line,
                "line_count": len(slice_lines),
                "code": "\n".join(slice_lines),
            }
        except Exception as e:
            return {"error": f"Error reading file '{file_path}': {str(e)}"}

    def semantic_code_search(self, query: str, repo: Optional[str] = None, limit: int = 10) -> Dict[str, Any]:
        """Performs full-text & semantic keyword search across code symbols and docstrings.

        Args:
            query: Search query (symbol name, concept, route).
            repo: Optional repository filter.
            limit: Max results to return.
        """
        results = self.storage.search_nodes_fts(query, repo=repo, limit=limit)
        return {
            "query": query,
            "repo_filter": repo,
            "match_count": len(results),
            "results": [n.model_dump() for n in results],
        }

    def blast_radius_analysis(self, entry_symbol: str, repo: Optional[str] = None) -> Dict[str, Any]:
        """Analyzes full downstream blast radius of modifying, renaming, or deprecating a symbol.

        Args:
            entry_symbol: Symbol or endpoint being modified (e.g. 'verify_auth_v1' or '/v1/auth/verify').
            repo: Optional source repository.
        """
        report: BlastRadiusReport = self.storage.analyze_blast_radius(entry_symbol, repo)
        return report.model_dump()
