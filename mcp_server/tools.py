"""
OmniContext - MCP Server Tool Implementations
Exposes deterministic semantic code graph querying tools to the Strands Agent via Model Context Protocol.
"""

from typing import Optional, Dict, Any, List
from common.models import CodeNode, CodeEdge, RetrievalResult, TraversalResult
from mcp_server.storage.sqlite_graph import SQLiteGraphStore
from mcp_server.storage.opensearch_client import DualModeVectorStore
from mcp_server.parsers.treesitter_engine import TreeSitterEngine
from mcp_server.parsers.scip_indexer import CrossRepoLinker


class CodeGraphToolManager:
    """Manages graph store and tool dispatch for the MCP server."""
    def __init__(self, db_path: str = "data/omnicontext_graph.db"):
        self.graph_store = SQLiteGraphStore(db_path)
        self.vector_store = DualModeVectorStore()
        self.parser = TreeSitterEngine()
        self.linker = CrossRepoLinker()

    def index_repositories(self, repo_paths: Dict[str, str]) -> Dict[str, Any]:
        """
        Ingests and indexes multiple repositories.
        repo_paths: {"repo_auth_core": "path/to/repo_auth_core", ...}
        """
        all_nodes: List[CodeNode] = []
        all_edges: List[CodeEdge] = []

        for repo_name, path in repo_paths.items():
            nodes, edges = self.parser.parse_directory(repo_name, path)
            all_nodes.extend(nodes)
            all_edges.extend(edges)

        # Cross-repository linking
        cross_edges = self.linker.link_repositories(all_nodes)
        all_edges.extend(cross_edges)

        # Persist to relational and vector stores
        self.graph_store.insert_nodes(all_nodes)
        self.graph_store.insert_edges(all_edges)
        self.vector_store.index_nodes(all_nodes)

        return {
            "indexed_nodes": len(all_nodes),
            "internal_edges": len(all_edges) - len(cross_edges),
            "cross_repo_edges": len(cross_edges),
            "repositories": list(repo_paths.keys())
        }

    def get_symbol_definition(self, symbol_name: str, repo: Optional[str] = None) -> Dict[str, Any]:
        """Locates the exact definition and code slice of a function, class, or endpoint."""
        nodes = self.graph_store.find_nodes_by_name(symbol_name, repo=repo)
        if not nodes:
            # Fallback to lexical search
            nodes = self.graph_store.search_nodes_lexical(symbol_name, repo=repo, limit=3)
        return {
            "found": bool(nodes),
            "count": len(nodes),
            "symbols": [n.to_dict() for n in nodes]
        }

    def get_usage_dependency_links(self, symbol_id_or_name: str) -> Dict[str, Any]:
        """
        Returns all upstream callers and downstream consumers that depend on this symbol
        across all repository boundaries.
        """
        node = self.graph_store.get_node(symbol_id_or_name)
        if not node:
            matches = self.graph_store.find_nodes_by_name(symbol_id_or_name)
            node = matches[0] if matches else None

        if not node:
            return {"found": False, "message": f"Symbol '{symbol_id_or_name}' not found in code graph."}

        callers = self.graph_store.get_callers(node.id)
        callees = self.graph_store.get_callees(node.id)

        return {
            "target_symbol": node.to_dict(),
            "upstream_callers_count": len(callers),
            "upstream_callers": [c.to_dict() for c in callers],
            "downstream_callees_count": len(callees),
            "downstream_callees": [c.to_dict() for c in callees]
        }

    def traverse_call_graph(self, root_symbol: str, depth: int = 3) -> Dict[str, Any]:
        """
        Traces the full blast radius across repositories starting from a root symbol.
        Used to analyze the impact of modifying or deprecating an API endpoint.
        """
        traversal: TraversalResult = self.graph_store.traverse_blast_radius(root_symbol, max_depth=depth)
        return {
            "root_symbol": traversal.root_symbol,
            "max_depth": traversal.depth,
            "blast_radius_files": traversal.blast_radius_files,
            "upstream_callers": [n.to_dict() for n in traversal.upstream_callers],
            "downstream_dependencies": [n.to_dict() for n in traversal.downstream_dependencies],
            "execution_time_ms": traversal.execution_time_ms,
            "summary": traversal.summary()
        }

    def get_ast_chunk(self, node_id: str) -> Dict[str, Any]:
        """Retrieves the complete unbroken AST code block for a symbol."""
        node = self.graph_store.get_node(node_id)
        if not node:
            return {"found": False, "error": f"Node ID '{node_id}' not found."}
        return {
            "found": True,
            "id": node.id,
            "repo": node.repo,
            "file_path": node.file_path,
            "lines": f"{node.start_line}-{node.end_line}",
            "signature": node.signature,
            "code_content": node.code_content
        }

    def semantic_code_search(self, query: str, repo: Optional[str] = None, limit: int = 5) -> Dict[str, Any]:
        """Performs natural language to code search using dense embeddings (Titan v2 / Local)."""
        nodes = self.vector_store.search_semantic(query, repo=repo, limit=limit)
        return {
            "query": query,
            "count": len(nodes),
            "results": [n.to_dict() for n in nodes]
        }

    def get_system_stats(self) -> Dict[str, Any]:
        """Returns diagnostic metrics for telemetry monitoring."""
        graph_stats = self.graph_store.get_stats()
        vector_stats = self.vector_store.get_stats()
        return {
            "graph_engine": graph_stats,
            "vector_engine": vector_stats
        }
