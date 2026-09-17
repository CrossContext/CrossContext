"""
OmniContext - Cross-Repository Linker (SCIP / Semantic API Resolver)
Bridges distributed multi-repo boundaries by resolving:
1. HTTP API Endpoint definitions (FastAPI / Flask) to Frontend API consumers (fetch / axios).
2. Shared package imports across federated repositories.
"""

from typing import List, Tuple
from common.models import CodeNode, CodeEdge, EdgeType, SymbolType


class CrossRepoLinker:
    """
    Connects symbols across multiple repositories to construct deterministic cross-repo edges.
    """
    def __init__(self):
        pass

    def link_repositories(self, nodes: List[CodeNode]) -> List[CodeEdge]:
        """
        Analyzes nodes across all indexed repositories and discovers cross-repository edges.
        """
        cross_edges: List[CodeEdge] = []

        # 1. Map all API endpoints by their normalized route
        # e.g., "/v1/auth/verify" -> CodeNode(repo="repo_auth_core", ...)
        endpoint_map = {}
        for node in nodes:
            if node.symbol_type == SymbolType.ENDPOINT:
                route = node.metadata.get("endpoint_route", "")
                if route:
                    norm_route = self._normalize_route(route)
                    endpoint_map[norm_route] = node

        # 2. Find frontend consumers calling those endpoints
        for node in nodes:
            consumed_endpoint = node.metadata.get("consumes_endpoint", "")
            if not consumed_endpoint and node.code_content:
                # Also check code content for endpoint strings
                for route in endpoint_map.keys():
                    if route in node.code_content and node.repo != endpoint_map[route].repo:
                        consumed_endpoint = route
                        break

            if consumed_endpoint:
                norm_consumed = self._normalize_route(consumed_endpoint)
                if norm_consumed in endpoint_map:
                    target_endpoint = endpoint_map[norm_consumed]
                    # Create deterministic cross-repo edge!
                    cross_edges.append(CodeEdge(
                        caller_id=node.id,
                        callee_id=target_endpoint.id,
                        edge_type=EdgeType.CONSUMES_API,
                        confidence=1.0,
                        metadata={
                            "route": norm_consumed,
                            "caller_repo": node.repo,
                            "target_repo": target_endpoint.repo
                        }
                    ))

        return cross_edges

    @staticmethod
    def _normalize_route(route: str) -> str:
        """Normalizes URLs to clean path: 'https://auth.internal.corp/api/v1/auth/verify' -> '/v1/auth/verify'"""
        clean = route.split("?")[0]
        for prefix in ["https://", "http://"]:
            if clean.startswith(prefix):
                clean = clean.split("/", 3)[-1] if "/" in clean[len(prefix):] else ""
        if not clean.startswith("/"):
            clean = "/" + clean
        if clean.startswith("/api/"):
            clean = clean[4:]
        return clean
