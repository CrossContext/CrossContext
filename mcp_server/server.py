"""
CrossContext - Model Context Protocol (MCP) Server
Standardized JSON-RPC Gatekeeper decoupling multi-repo code state from agent reasoning.
Run with:
    python -m mcp_server.server
"""

import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from mcp.server.fastmcp import FastMCP
except (ImportError, ModuleNotFoundError):
    from mcp.server.mcpserver import MCPServer as FastMCP
from mcp_server.tools import CodeGraphToolManager

# Initialize MCP Server
mcp = FastMCP("CrossContext-CodeGraph-Server")
manager = CodeGraphToolManager(db_path=os.getenv("SQLITE_DB_PATH", "data/crosscontext_graph.db"))


@mcp.tool()
def get_symbol_definition(symbol_name: str, repo: Optional[str] = None) -> Dict[str, Any]:
    """
    Locates the exact definition, line numbers, and signature of a symbol across repositories.
    Args:
        symbol_name: Name of function, class, or endpoint (e.g., 'verify_legacy_auth')
        repo: Optional repository filter (e.g., 'repo_auth_core')
    """
    return manager.get_symbol_definition(symbol_name, repo)


@mcp.tool()
def get_usage_dependency_links(symbol_name_or_id: str) -> Dict[str, Any]:
    """
    Traces cross-repository caller and callee links. Identifies which services
    depend on or consume this symbol.
    Args:
        symbol_name_or_id: Symbol name or unique node ID
    """
    return manager.get_usage_dependency_links(symbol_name_or_id)


@mcp.tool()
def traverse_call_graph(root_symbol: str, max_depth: int = 3) -> Dict[str, Any]:
    """
    Computes the blast radius of modifying or deprecating an API or symbol.
    Returns upstream consumers and downstream dependencies spanning all repositories.
    Args:
        root_symbol: Starting symbol name (e.g., 'verify_legacy_auth')
        max_depth: Maximum recursion hops (default: 3)
    """
    return manager.traverse_call_graph(root_symbol, depth=max_depth)


@mcp.tool()
def get_ast_chunk(node_id: str) -> Dict[str, Any]:
    """
    Retrieves the complete unbroken AST code chunk for a symbol.
    Args:
        node_id: Deterministic node ID (e.g., 'repo_auth_core:src/api/auth.py:verify_legacy_auth:24')
    """
    return manager.get_ast_chunk(node_id)


@mcp.tool()
def semantic_code_search(query: str, repo: Optional[str] = None, limit: int = 5) -> Dict[str, Any]:
    """
    Searches codebases using natural language intent via dense vector embeddings.
    Args:
        query: Conceptual search query (e.g., 'JWT token verification')
        repo: Optional repository filter
        limit: Number of results (default: 5)
    """
    return manager.semantic_code_search(query, repo=repo, limit=limit)


@mcp.tool()
def index_local_repositories(repo_paths: Dict[str, str]) -> Dict[str, Any]:
    """
    Indexes directories into the semantic graph and vector store.
    Args:
        repo_paths: Map of repo name to absolute/relative directory path
    """
    return manager.index_repositories(repo_paths)


@mcp.tool()
def get_graph_diagnostics() -> Dict[str, Any]:
    """Returns database and vector store diagnostics."""
    return manager.get_system_stats()


if __name__ == "__main__":
    # If run directly as a script, default to stdio transport for IDE/Agent integration
    mcp.run(transport="stdio")
