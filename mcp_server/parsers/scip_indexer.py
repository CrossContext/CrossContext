"""OmniContext - Cross-Repository Linker (SCIP / Semantic API Resolver).

Bridges distributed multi-repo boundaries by resolving:
1. HTTP API Endpoint definitions (FastAPI / Flask / Spring) to Frontend API consumers (fetch / axios), keyed by method + route.
2. Shared package imports across federated repositories requiring resolvable import references.
3. Cross-repository client SDK invocations and model inheritance.
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

        # 1. Map all API endpoints by (HTTP Method, Normalized Route) and route fallback
        endpoint_method_map: Dict[Tuple[str, str], CodeNode] = {}
        route_fallback_map: Dict[str, List[CodeNode]] = {}
        nodes_by_name: Dict[str, List[CodeNode]] = {}

        for node in nodes:
            nodes_by_name.setdefault(node.symbol_name, []).append(node)

            if node.symbol_type == SymbolType.ENDPOINT:
                route = node.metadata.get("endpoint_route", "")
                method = (node.metadata.get("http_method") or "GET").upper()
                if route:
                    norm_route = self._normalize_route(route)
                    endpoint_method_map[(method, norm_route)] = node
                    route_fallback_map.setdefault(norm_route, []).append(node)

        # 2. Match consumers to endpoints with method-aware routing
        for node in nodes:
            consumed_endpoint = node.metadata.get("consumes_endpoint", "")
            consumed_method = (node.metadata.get("consumes_http_method") or "GET").upper()

            if not consumed_endpoint and node.code_content:
                for norm_path in route_fallback_map.keys():
                    if norm_path in node.code_content and all(ep.repo != node.repo for ep in route_fallback_map[norm_path]):
                        consumed_endpoint = norm_path
                        break

            if consumed_endpoint:
                norm_consumed = self._normalize_route(consumed_endpoint)
                # First try exact method + route match
                target_endpoint = endpoint_method_map.get((consumed_method, norm_consumed))
                if not target_endpoint and norm_consumed in route_fallback_map:
                    # Fallback to route-matching endpoint from different repo
                    target_endpoint = next((ep for ep in route_fallback_map[norm_consumed] if ep.repo != node.repo), None)

                if target_endpoint and target_endpoint.repo != node.repo:
                    cross_edges.append(CodeEdge(
                        caller_id=node.id,
                        callee_id=target_endpoint.id,
                        edge_type=EdgeType.CONSUMES_API,
                        confidence=1.0,
                        metadata={
                            "route": norm_consumed,
                            "http_method": consumed_method,
                            "caller_repo": node.repo,
                            "target_repo": target_endpoint.repo,
                        }
                    ))

            # 3. Cross-repo SDK / function calls (Requires resolvable import or client receiver)
            if node.code_content:
                file_imports = node.metadata.get("file_imports", [])
                tokens = set(re.findall(r'\b[a-zA-Z0-9_]{4,}\b', node.code_content))
                candidate_names = tokens.intersection(nodes_by_name.keys())

                for sym_name in candidate_names:
                    if sym_name == node.symbol_name:
                        continue
                    targets = nodes_by_name[sym_name]
                    # Filter for targets in other repositories with function/method type
                    external_targets = [t for t in targets if t.repo != node.repo and t.symbol_type in (SymbolType.FUNCTION, SymbolType.METHOD)]
                    if not external_targets:
                        continue

                    # Check if function is called with client prefix e.g. client.verify_token() or defaultAuthClient.verifyUserSession()
                    is_explicit_call = bool(re.search(r'\b[a-zA-Z0-9_]*(?:Client|Service|SDK)\.' + re.escape(sym_name) + r'\(', node.code_content))
                    # Or if caller file explicitly imports the target module or target symbol name
                    is_imported_call = bool(file_imports and any(sym_name in imp or any(t.file_path in imp for t in external_targets) for imp in file_imports))

                    if is_explicit_call or is_imported_call:
                        for target in external_targets:
                            cross_edges.append(CodeEdge(
                                caller_id=node.id,
                                callee_id=target.id,
                                edge_type=EdgeType.CALLS,
                                confidence=0.95,
                                metadata={
                                    "symbol": sym_name,
                                    "caller_repo": node.repo,
                                    "target_repo": target.repo,
                                }
                            ))

        return cross_edges

    @staticmethod
    def _normalize_route(route: str) -> str:
        """Normalizes URLs to clean path: 'https://auth.internal.corp/api/v1/auth/verify' -> '/v1/auth/verify'"""
        clean = route.split("?")[0]
        # Strip protocol and host if full URL
        clean = re.sub(r'^https?://[^/]+', '', clean)
        if not clean.startswith("/"):
            clean = "/" + clean
        if clean.startswith("/api/"):
            clean = clean[4:]
        return clean.rstrip("/")


# Alias for backward compatibility
SCIPIndexer = CrossRepoLinker
