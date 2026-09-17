"""SCIP & Cross-Repository Dependency Linker for OmniContext.

Resolves imports, function invocations, class inheritance, and cross-repo HTTP API
contracts (e.g. frontend fetch('/v1/auth/verify') -> backend @app.get('/v1/auth/verify')).
"""

from __future__ import annotations
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from common.models import CodeNode, CodeEdge, EdgeType, SymbolType
from mcp_server.parsers.treesitter_engine import TreeSitterEngine
from mcp_server.storage.sqlite_graph import SQLiteGraphStorage


class SCIPIndexer:
    """Indexes multi-repo codebases, building a cross-repository caller/callee graph."""

    def __init__(self, storage: Optional[SQLiteGraphStorage] = None):
        self.engine = TreeSitterEngine()
        self.storage = storage or SQLiteGraphStorage()

    def index_repository(self, repo_dir: str, repo_name: Optional[str] = None) -> List[CodeNode]:
        """Scans a repository directory, extracts AST nodes, and stores them."""
        repo_path = Path(repo_dir).resolve()
        name = repo_name or repo_path.name

        nodes: List[CodeNode] = []
        supported_extensions = {".py", ".ts", ".tsx", ".js", ".jsx", ".go"}

        for root, dirs, files in os.walk(repo_path):
            # Skip hidden, build, and node_modules folders
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("node_modules", "dist", "build", "__pycache__", ".venv", "venv")]

            for file in files:
                ext = Path(file).suffix.lower()
                if ext in supported_extensions:
                    full_path = Path(root) / file
                    rel_path = str(full_path.relative_to(repo_path).as_posix())
                    file_nodes = self.engine.parse_file(full_path, repo=name)
                    # Update file_path to be relative to repo root
                    for n in file_nodes:
                        n.file_path = rel_path
                        self.storage.insert_node(n)
                        nodes.append(n)

        return nodes

    def build_cross_repo_links(self) -> List[CodeEdge]:
        """Analyzes all stored nodes to generate internal and cross-repository edges."""
        all_nodes = self.storage.get_all_nodes()
        generated_edges: List[CodeEdge] = []

        # Index nodes by symbol_name and route_path
        nodes_by_name: Dict[str, List[CodeNode]] = {}
        nodes_by_route: Dict[str, List[CodeNode]] = {}

        for n in all_nodes:
            # Index by simple symbol name (e.g. 'verify_token')
            simple_name = n.symbol_name.split(".")[-1]
            nodes_by_name.setdefault(simple_name, []).append(n)
            nodes_by_name.setdefault(n.symbol_name, []).append(n)

            # Index by HTTP endpoint route
            route = n.metadata.get("route_path")
            if route:
                # Clean route (e.g. /v1/auth/verify)
                norm_route = self._normalize_route(route)
                nodes_by_route.setdefault(norm_route, []).append(n)

        # Iterate over all nodes to detect references
        for caller in all_nodes:
            meta = caller.metadata or {}

            # 1. API Call dependencies (Cross-Repo HTTP calls)
            api_calls = meta.get("api_calls", [])
            # Also check code content for endpoint strings
            if caller.code_content:
                for endpoint_match in re.finditer(r"['\"`](/(?:v[0-9]+/)?(?:api/)?[a-zA-Z0-9_\-\/]+)['\"`]", caller.code_content):
                    api_calls.append(endpoint_match.group(1))

            for api_path in set(api_calls):
                norm_path = self._normalize_route(api_path)
                target_endpoints = nodes_by_route.get(norm_path, [])
                for target in target_endpoints:
                    if target.id != caller.id:
                        edge = CodeEdge(
                            id=f"{caller.id}->consumes_api->{target.id}",
                            caller_id=caller.id,
                            callee_id=target.id,
                            edge_type=EdgeType.CONSUMES_API,
                            caller_repo=caller.repo,
                            callee_repo=target.repo,
                            context_line=caller.start_line,
                            call_snippet=f"HTTP call to {api_path}",
                            metadata={"route": api_path},
                        )
                        self.storage.insert_edge(edge)
                        generated_edges.append(edge)

            # 2. Function calls & method invocations
            calls = meta.get("calls", [])
            for callee_name in set(calls):
                candidates = nodes_by_name.get(callee_name, [])
                for target in candidates:
                    if target.id != caller.id:
                        # Prioritize same repo or exact match
                        edge_type = EdgeType.CALLS
                        edge = CodeEdge(
                            id=f"{caller.id}->calls->{target.id}",
                            caller_id=caller.id,
                            callee_id=target.id,
                            edge_type=edge_type,
                            caller_repo=caller.repo,
                            callee_repo=target.repo,
                            context_line=caller.start_line,
                            call_snippet=f"invokes {callee_name}()",
                            metadata={"symbol": callee_name},
                        )
                        self.storage.insert_edge(edge)
                        generated_edges.append(edge)

            # 3. Class inheritance
            bases = meta.get("bases", [])
            for base_name in bases:
                candidates = nodes_by_name.get(base_name, [])
                for target in candidates:
                    if target.id != caller.id:
                        edge = CodeEdge(
                            id=f"{caller.id}->inherits->{target.id}",
                            caller_id=caller.id,
                            callee_id=target.id,
                            edge_type=EdgeType.INHERITS,
                            caller_repo=caller.repo,
                            callee_repo=target.repo,
                            context_line=caller.start_line,
                            call_snippet=f"class {caller.symbol_name} extends {base_name}",
                            metadata={"base_class": base_name},
                        )
                        self.storage.insert_edge(edge)
                        generated_edges.append(edge)

        return generated_edges

    def index_multi_repos(self, repo_directories: Dict[str, str]) -> Dict[str, int]:
        """Indexes multiple repositories and links cross-repository relationships.

        Args:
            repo_directories: Dict of {repo_name: directory_path}
        """
        results = {}
        for repo_name, repo_dir in repo_directories.items():
            nodes = self.index_repository(repo_dir, repo_name)
            results[repo_name] = len(nodes)

        edges = self.build_cross_repo_links()
        results["total_edges_created"] = len(edges)
        return results

    def _normalize_route(self, route: str) -> str:
        """Normalizes an API route string for robust matching."""
        route = route.strip().rstrip("/")
        if not route.startswith("/"):
            route = "/" + route
        # Normalize path params like /users/{id} or /users/:id to /users/*
        route = re.sub(r"\{[^}]+\}", "*", route)
        route = re.sub(r":[a-zA-Z0-9_]+", "*", route)
        return route
