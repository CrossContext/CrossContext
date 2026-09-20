"""OmniContext - Cross-Repository Linker (SCIP / Semantic API Resolver).

Bridges distributed multi-repo boundaries by resolving:
1. HTTP API Endpoint definitions (FastAPI / Flask / Spring / Gin / Express) to API consumers (fetch / axios / requests / httpx / Go http), with full support for parameterized path variables (/users/{id} vs /users/123).
2. Shared package imports and bindings across federated repositories.
3. Cross-repository client SDK invocations and model inheritance.
"""

from __future__ import annotations
import re
from typing import Any, Dict, List, Optional, Tuple, Set
from common.models import CodeNode, CodeEdge, EdgeType, SymbolType


GENERIC_AND_BUILTIN_SYMBOLS: Set[str] = {
    "open", "close", "read", "write", "send", "recv", "start", "stop", "run", "init",
    "test", "request", "response", "data", "get", "post", "put", "delete", "patch",
    "set", "fetch", "config", "client", "service", "helper", "error", "result", "item",
    "user", "app", "server", "handler", "main", "parse", "format", "load", "dump",
    "create", "update", "remove", "clear", "validate", "check", "log", "debug", "info",
    "warn", "exec", "call", "apply", "map", "filter", "reduce", "list", "dict", "str",
    "int", "bool", "float", "len", "type", "print", "status", "value", "key", "token",
    "tofirestore", "formatbytes", "formatdate", "ismacos", "setup", "teardown", "beforeeach",
    "aftereach", "describe", "it", "expect", "assert", "render", "component", "props",
    "state", "params", "query", "body", "headers", "options", "context", "next",
    "index", "default", "util", "utils", "common", "shared", "model", "view", "controller",
    "clean", "reset", "build", "process", "handle", "execute", "dispose", "destroy", "refresh"
}

COMMON_THIRD_PARTY_PACKAGES: Set[str] = {
    "flask", "fastapi", "requests", "httpx", "aiohttp", "urllib", "urllib3", "pydantic",
    "sqlalchemy", "pytest", "unittest", "django", "celery", "redis", "boto3", "botocore",
    "numpy", "pandas", "scipy", "sklearn", "torch", "tensorflow", "transformers", "logging",
    "os", "sys", "re", "json", "time", "datetime", "math", "random", "pathlib", "typing",
    "collections", "itertools", "functools", "copy", "io", "shutil", "subprocess", "socket",
    "http", "asyncio", "threading", "multiprocessing", "react", "react-dom", "vue", "angular",
    "axios", "express", "lodash", "moment", "dayjs", "ky", "zustand", "redux", "next", "vite",
    "fs", "path", "events", "stream", "crypto", "util", "net", "tls", "dns", "zlib"
}


class CrossRepoLinker:
    """Connects symbols across multiple repositories to construct deterministic cross-repo edges."""

    def __init__(self):
        pass

    @staticmethod
    def _is_repo_imported(target_repo: str, import_stmt: str) -> bool:
        """Determines if an import statement explicitly references the target repository."""
        clean_imp = import_stmt.strip().replace("\\", "/")
        repo_names = [target_repo]
        clean_no_prefix = re.sub(r'^repo[_-]', '', target_repo)
        if len(clean_no_prefix) >= 4 and clean_no_prefix.lower() not in COMMON_THIRD_PARTY_PACKAGES:
            repo_names.append(clean_no_prefix)

        for r_name in repo_names:
            # Word or path boundary matching: e.g. from repo_shared_sdk import ... or from '@org/shared_sdk'
            pattern = rf'(?:^|[\s\'"`/@./])({re.escape(r_name)})(?:[\s\'"`/@./]|$)'
            if re.search(pattern, clean_imp, re.IGNORECASE):
                # Ensure the statement is not actually just importing a 3rd-party library
                parts = [p.lower() for p in re.split(r'[\s./\'"`]', clean_imp) if p]
                if len(parts) > 1 and parts[0] in ("from", "import"):
                    root_mod = parts[1]
                    if root_mod in COMMON_THIRD_PARTY_PACKAGES and root_mod != r_name.lower():
                        continue
                return True
        return False

    def link_repositories(self, nodes: List[CodeNode]) -> List[CodeEdge]:
        """Analyzes nodes across all indexed repositories and discovers cross-repository edges."""
        cross_edges: List[CodeEdge] = []
        seen_edges: Set[Tuple[str, str, str]] = set()

        # 1. Map all API endpoints
        endpoint_method_map: Dict[Tuple[str, str], CodeNode] = {}
        route_fallback_map: Dict[str, List[CodeNode]] = {}
        all_endpoints: List[CodeNode] = []
        nodes_by_name: Dict[str, List[CodeNode]] = {}
        nodes_by_repo: Dict[str, List[CodeNode]] = {}

        for node in nodes:
            nodes_by_name.setdefault(node.symbol_name, []).append(node)
            nodes_by_repo.setdefault(node.repo, []).append(node)

            if node.symbol_type == SymbolType.ENDPOINT:
                all_endpoints.append(node)
                route = node.metadata.get("endpoint_route", "")
                method = (node.metadata.get("http_method") or "GET").upper()
                if route:
                    norm_route = self._normalize_route(route)
                    endpoint_method_map[(method, norm_route)] = node
                    route_fallback_map.setdefault(norm_route, []).append(node)

        # 2. Match consumers to endpoints with method-aware & parameterized routing
        for node in nodes:
            consumed_endpoint = node.metadata.get("consumes_endpoint", "")
            consumed_method = (node.metadata.get("consumes_http_method") or "GET").upper()

            if consumed_endpoint:
                norm_consumed = self._normalize_route(consumed_endpoint)

                # Guard: Root path or bare slash ('/' or "") requires an explicit target service base URL matching the target repo
                is_root_route = norm_consumed in ("", "/")
                target_base_url = (node.metadata or {}).get("target_base_url", "").lower()
                if is_root_route and not target_base_url:
                    continue

                target_endpoint = None

                # 2a. First try exact method + route match
                target_endpoint = endpoint_method_map.get((consumed_method, norm_consumed))

                # 2b. Try exact route match from different repo (method fallback)
                if not target_endpoint and norm_consumed in route_fallback_map:
                    target_endpoint = next((ep for ep in route_fallback_map[norm_consumed] if ep.repo != node.repo), None)

                # 2c. Try parameterized / wildcard route matching across all external endpoints (only for non-root routes)
                if not target_endpoint and not is_root_route:
                    # Prefer matching HTTP method first
                    for ep in all_endpoints:
                        if ep.repo == node.repo:
                            continue
                        ep_route = ep.metadata.get("endpoint_route", "")
                        ep_method = (ep.metadata.get("http_method") or "GET").upper()
                        if ep_method == consumed_method and self._route_matches(ep_route, consumed_endpoint):
                            target_endpoint = ep
                            break

                    # If still not found, check any method
                    if not target_endpoint:
                        for ep in all_endpoints:
                            if ep.repo == node.repo:
                                continue
                            ep_route = ep.metadata.get("endpoint_route", "")
                            if self._route_matches(ep_route, consumed_endpoint):
                                target_endpoint = ep
                                break

                # Root route verification: target base URL must match producer repo
                if target_endpoint and is_root_route:
                    target_repo_clean = re.sub(r'^repo[_-]', '', target_endpoint.repo).lower().replace("_", "-")
                    if target_repo_clean not in target_base_url and target_endpoint.repo.lower() not in target_base_url:
                        target_endpoint = None

                if target_endpoint and target_endpoint.repo != node.repo:
                    edge_key = (node.id, target_endpoint.id, EdgeType.CONSUMES_API.value)
                    if edge_key not in seen_edges:
                        seen_edges.add(edge_key)
                        cross_edges.append(CodeEdge(
                            caller_id=node.id,
                            callee_id=target_endpoint.id,
                            edge_type=EdgeType.CONSUMES_API,
                            confidence=1.0,
                            metadata={
                                "route": norm_consumed,
                                "target_endpoint_route": target_endpoint.metadata.get("endpoint_route", ""),
                                "http_method": consumed_method,
                                "caller_repo": node.repo,
                                "target_repo": target_endpoint.repo,
                            }
                        ))

            # 3. Cross-repo SDK / function calls & Import bindings
            file_imports = node.metadata.get("file_imports", [])

            # 3a. Check explicit cross-repo imports (e.g. from repo_shared_sdk import client)
            for imp in file_imports:
                for target_repo, target_nodes in nodes_by_repo.items():
                    if target_repo == node.repo:
                        continue

                    if not self._is_repo_imported(target_repo, imp):
                        continue

                    for t_node in target_nodes:
                        if t_node.symbol_name.lower() in GENERIC_AND_BUILTIN_SYMBOLS:
                            continue
                        if len(t_node.symbol_name) < 4:
                            continue

                        # Verify symbol is specifically imported or called in code
                        is_symbol_in_import = bool(re.search(r'\b' + re.escape(t_node.symbol_name) + r'\b', imp))
                        is_symbol_in_code = bool(node.code_content and re.search(r'\b' + re.escape(t_node.symbol_name) + r'\b', node.code_content))

                        if is_symbol_in_import or is_symbol_in_code:
                            edge_key = (node.id, t_node.id, EdgeType.IMPORTS.value)
                            if edge_key not in seen_edges:
                                seen_edges.add(edge_key)
                                cross_edges.append(CodeEdge(
                                    caller_id=node.id,
                                    callee_id=t_node.id,
                                    edge_type=EdgeType.IMPORTS,
                                    confidence=0.98,
                                    metadata={
                                        "import": imp,
                                        "symbol": t_node.symbol_name,
                                        "caller_repo": node.repo,
                                        "target_repo": target_repo
                                    }
                                ))

            # 3b. Check invocations of external functions/methods (SDK client prefix or imported symbols)
            if node.code_content:
                tokens = set(re.findall(r'\b[a-zA-Z0-9_]{4,}\b', node.code_content))
                candidate_names = tokens.intersection(nodes_by_name.keys())

                for sym_name in candidate_names:
                    if sym_name == node.symbol_name:
                        continue
                    # Guardrail: Never resolve generic names or built-ins across repos
                    if sym_name.lower() in GENERIC_AND_BUILTIN_SYMBOLS:
                        continue

                    targets = nodes_by_name[sym_name]
                    external_targets = [
                        t for t in targets
                        if t.repo != node.repo and t.symbol_type in (SymbolType.FUNCTION, SymbolType.METHOD, SymbolType.CLASS)
                    ]
                    if not external_targets:
                        continue

                    for target in external_targets:
                        # Cross-repo symbol invocation strictly requires that the target repo was imported
                        is_repo_imported = any(self._is_repo_imported(target.repo, imp) for imp in file_imports)
                        if not is_repo_imported:
                            continue

                        is_imported_call = any(
                            sym_name in imp and self._is_repo_imported(target.repo, imp)
                            for imp in file_imports
                        )
                        is_explicit_sdk_call = bool(
                            re.search(r'\b[a-zA-Z0-9_]*(?:Client|Service|SDK|Helper)\.' + re.escape(sym_name) + r'\(', node.code_content)
                        )

                        if is_imported_call or is_explicit_sdk_call:
                            edge_key = (node.id, target.id, EdgeType.CALLS.value)
                            if edge_key not in seen_edges:
                                seen_edges.add(edge_key)
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
        clean = route.split("?")[0].strip()
        clean = re.sub(r'^https?://[^/]+', '', clean)
        if not clean.startswith("/"):
            clean = "/" + clean
        if clean.startswith("/api/"):
            clean = clean[4:]
        return clean.rstrip("/") or "/"

    @staticmethod
    def _normalize_parameterized_route(route: str) -> str:
        """
        Normalizes variable path segments to canonical '{_param_}' placeholder.
        Examples:
          '/users/{id}' -> '/users/{_param_}'
          '/users/:id' -> '/users/{_param_}'
          '/users/<int:id>' -> '/users/{_param_}'
          '/users/${userId}' -> '/users/{_param_}'
        """
        clean = CrossRepoLinker._normalize_route(route)
        # Replace path variables: <int:id>, {id}, ${id}, :id
        clean = re.sub(r'<[^>]+>', '{_param_}', clean)
        clean = re.sub(r'\{[^{}]+\}', '{_param_}', clean)
        clean = re.sub(r'\$\{[^{}]+\}', '{_param_}', clean)
        clean = re.sub(r':[a-zA-Z0-9_\-]+', '{_param_}', clean)
        return clean

    @staticmethod
    def _route_matches(endpoint_route: str, consumer_route: str) -> bool:
        """
        Determines if a consumer route matches an endpoint route.
        Supports:
          - Exact match after normalization: '/v1/auth/verify' == '/v1/auth/verify'
          - Parameterized match: '/users/{id}' matches '/users/123' or '/users/:id'
          - Segment-by-segment parameter wildcard matching
        """
        if not endpoint_route or not consumer_route:
            return False

        norm_ep = CrossRepoLinker._normalize_route(endpoint_route)
        norm_co = CrossRepoLinker._normalize_route(consumer_route)

        if norm_ep == norm_co:
            return True

        canon_ep = CrossRepoLinker._normalize_parameterized_route(endpoint_route)
        canon_co = CrossRepoLinker._normalize_parameterized_route(consumer_route)
        if canon_ep == canon_co:
            return True

        # Segment-by-segment matching:
        ep_parts = [p for p in norm_ep.split("/") if p]
        co_parts = [p for p in norm_co.split("/") if p]
        if len(ep_parts) != len(co_parts):
            return False

        for ep_seg, co_seg in zip(ep_parts, co_parts):
            if ep_seg == co_seg:
                continue
            is_ep_param = bool(re.match(r'^(\{[^}]+\}|:[a-zA-Z0-9_]+|<.*>|\*)$', ep_seg))
            is_co_param = bool(re.match(r'^(\{[^}]+\}|:[a-zA-Z0-9_]+|<.*>|\*|\$\{[^}]+\})$', co_seg))
            if is_ep_param and is_co_param:
                continue
            if is_ep_param and re.match(r'^[a-zA-Z0-9_\-\.]+$', co_seg):
                continue
            if is_co_param and re.match(r'^[a-zA-Z0-9_\-\.]+$', ep_seg):
                continue
            return False

        return True


# Alias for backward compatibility
SCIPIndexer = CrossRepoLinker
