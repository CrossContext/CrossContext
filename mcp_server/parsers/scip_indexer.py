"""OmniContext - Cross-Repository Linker (SCIP / Semantic API Resolver).

Bridges distributed multi-repo boundaries by resolving:
1. HTTP API Endpoint definitions (FastAPI / Flask / Spring) to Frontend API consumers (fetch / axios).
2. Shared package imports across federated repositories.
3. Cross-repository class inheritance and client SDK invocations.
"""

from __future__ import annotations
import re
from typing import Any, Dict, List, Optional, Tuple
from common.models import CodeNode, CodeEdge, EdgeType, SymbolType


class CrossRepoLinker:
    """Connects symbols across multiple repositories to construct deterministic cross-repo edges."""

    def __init__(self):
        pass

    def link_repositories(self, nodes: List[CodeNode]) -> List[CodeEdge]:
        """Analyzes nodes across all indexed repositories and discovers cross-repository edges."""
        cross_edges: List[CodeEdge] = []

        # 1. Map all API endpoints by their normalized route
        endpoint_map: Dict[str, CodeNode] = {}
        nodes_by_name: Dict[str, List[CodeNode]] = {}

        for node in nodes:
            # Map by symbol name
            nodes_by_name.setdefault(node.symbol_name, []).append(node)

            # Map by endpoint route
            if node.symbol_type == SymbolType.ENDPOINT:
                route = node.metadata.get("endpoint_route", "")
                if route:
                    norm_route = self._normalize_route(route)
                    endpoint_map[norm_route] = node

        # 2. Find consumers calling those endpoints or SDK functions
        for node in nodes:
            # Check for API endpoint calls
            consumed_endpoint = node.metadata.get("consumes_endpoint", "")
            if not consumed_endpoint and node.code_content:
                for route in endpoint_map.keys():
                    if route in node.code_content and node.repo != endpoint_map[route].repo:
                        consumed_endpoint = route
                        break

            if consumed_endpoint:
                norm_consumed = self._normalize_route(consumed_endpoint)
                if norm_consumed in endpoint_map:
                    target_endpoint = endpoint_map[norm_consumed]
                    if target_endpoint.repo != node.repo:
                        cross_edges.append(CodeEdge(
                            caller_id=node.id,
                            callee_id=target_endpoint.id,
                            edge_type=EdgeType.CONSUMES_API,
                            confidence=1.0,
                            metadata={
                                "route": norm_consumed,
                                "caller_repo": node.repo,
                                "target_repo": target_endpoint.repo,
                            }
                        ))

            # Check for cross-repo SDK / function calls
            if node.code_content:
                for sym_name, targets in nodes_by_name.items():
                    if sym_name != node.symbol_name and len(sym_name) > 4:
                        if re.search(r'\b' + re.escape(sym_name) + r'\(', node.code_content):
                            for target in targets:
                                if target.repo != node.repo and target.symbol_type in (SymbolType.FUNCTION, SymbolType.METHOD):
                                    cross_edges.append(CodeEdge(
                                        caller_id=node.id,
                                        callee_id=target.id,
                                        edge_type=EdgeType.CALLS,
                                        confidence=0.9,
                                        metadata={
                                            "symbol": sym_name,
                                            "caller_repo": node.repo,
                                            "target_repo": target.repo,
                                        }
                                    ))

        return cross_edges

    @staticmethod
    def _normalize_route(route: str) -> str:
        """Normalizes URLs to clean path: 'http://localhost:8000/api/v1/auth/verify' -> '/v1/auth/verify'"""
        clean = route.split("?")[0]
        for prefix in ["https://", "http://"]:
            if clean.startswith(prefix):
                clean = clean.split("/", 3)[-1] if "/" in clean[len(prefix):] else ""
        if not clean.startswith("/"):
            clean = "/" + clean
        if clean.startswith("/api/"):
            clean = clean[4:]
        return clean.rstrip("/")


# Alias for backward compatibility
SCIPIndexer = CrossRepoLinker
