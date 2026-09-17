"""OmniContext Model Context Protocol (MCP) Server.

Exposes deterministic code graph navigation, boundary-aware AST retrieval,
and cross-repository blast-radius analysis over the standard MCP JSON-RPC protocol.
"""

from __future__ import annotations
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

from mcp_server.parsers.scip_indexer import SCIPIndexer
from mcp_server.storage.sqlite_graph import SQLiteGraphStorage
from mcp_server.tools import CodeGraphTools

# Initialize FastMCP Server
mcp = FastMCP("OmniContext CodeGraph")

# Shared storage and tools instance
DB_PATH = os.environ.get("OMNICONTEXT_DB_PATH", "omnicontext_graph.db")
storage = SQLiteGraphStorage(db_path=DB_PATH)
tools_engine = CodeGraphTools(storage=storage)
indexer = SCIPIndexer(storage=storage)


def auto_index_testbed_if_empty():
    """Auto-indexes the reference testbed repositories if the graph is currently unpopulated."""
    nodes = storage.get_all_nodes()
    if not nodes:
        root_dir = Path(__file__).resolve().parent.parent
        testbed_dir = root_dir / "testbed"
        if testbed_dir.is_dir():
            repos = {
                "repo_auth_core": str(testbed_dir / "repo_auth_core"),
                "repo_frontend_portal": str(testbed_dir / "repo_frontend_portal"),
                "repo_shared_sdk": str(testbed_dir / "repo_shared_sdk"),
            }
            existing_repos = {k: v for k, v in repos.items() if Path(v).is_dir()}
            if existing_repos:
                indexer.index_multi_repos(existing_repos)


# Run auto-indexing on module load
auto_index_testbed_if_empty()


@mcp.tool()
def find_symbol_definition(symbol_name: str, repo: Optional[str] = None) -> str:
    """Finds the precise definition, file path, line bounds, and AST content of a symbol.

    Args:
        symbol_name: Name of the function, class, endpoint, or variable.
        repo: Optional repository filter (e.g. 'repo_auth_core').
    """
    res = tools_engine.find_symbol_definition(symbol_name, repo)
    return json.dumps(res, indent=2)


@mcp.tool()
def get_usage_dependency_links(symbol_id: str) -> str:
    """Finds all direct callers, consumers, and downstream dependencies across repositories.

    Args:
        symbol_id: Unique symbol ID or symbol name.
    """
    res = tools_engine.get_usage_dependency_links(symbol_id)
    return json.dumps(res, indent=2)


@mcp.tool()
def traverse_call_graph(
    entry_symbol: str, depth: int = 2, direction: str = "both", repo: Optional[str] = None
) -> str:
    """Traces the multi-hop caller/callee dependency graph starting from an entry symbol.

    Args:
        entry_symbol: Function, class, or endpoint to start traversal from.
        depth: Maximum traversal hops (default 2).
        direction: 'downstream' (callers), 'upstream' (callees), or 'both'.
        repo: Optional repository filter for entry point.
    """
    res = tools_engine.traverse_call_graph(entry_symbol, depth=depth, direction=direction, repo=repo)
    return json.dumps(res, indent=2)


@mcp.tool()
def get_ast_chunk(
    file_path: str, start_line: int, end_line: int, repo: Optional[str] = None
) -> str:
    """Retrieves exact, unbroken structural code chunk between specified line bounds.

    Args:
        file_path: Relative or absolute path to the file.
        start_line: 1-indexed starting line.
        end_line: 1-indexed ending line.
        repo: Optional repository identifier.
    """
    res = tools_engine.get_ast_chunk(file_path, start_line=start_line, end_line=end_line, repo=repo)
    return json.dumps(res, indent=2)


@mcp.tool()
def semantic_code_search(query: str, repo: Optional[str] = None, limit: int = 10) -> str:
    """Performs full-text & semantic keyword search across code symbols, signatures, and docstrings.

    Args:
        query: Search query (symbol name, concept, route).
        repo: Optional repository filter.
        limit: Max results to return.
    """
    res = tools_engine.semantic_code_search(query, repo=repo, limit=limit)
    return json.dumps(res, indent=2)


@mcp.tool()
def blast_radius_analysis(entry_symbol: str, repo: Optional[str] = None) -> str:
    """Analyzes full downstream blast radius of modifying, renaming, or deprecating a symbol.

    Args:
        entry_symbol: Symbol or endpoint being modified (e.g. 'verify_auth_v1' or '/v1/auth/verify').
        repo: Optional source repository.
    """
    res = tools_engine.blast_radius_analysis(entry_symbol, repo=repo)
    return json.dumps(res, indent=2)


@mcp.tool()
def index_codebases(repo_paths_json: Optional[str] = None) -> str:
    """Re-indexes codebases from provided repo mapping JSON string or default testbed.

    Args:
        repo_paths_json: Optional JSON string of {repo_name: path}.
    """
    storage.clear_all()
    if repo_paths_json:
        repo_dict = json.loads(repo_paths_json)
    else:
        root_dir = Path(__file__).resolve().parent.parent
        testbed_dir = root_dir / "testbed"
        repo_dict = {
            "repo_auth_core": str(testbed_dir / "repo_auth_core"),
            "repo_frontend_portal": str(testbed_dir / "repo_frontend_portal"),
            "repo_shared_sdk": str(testbed_dir / "repo_shared_sdk"),
        }
    stats = indexer.index_multi_repos(repo_dict)
    return json.dumps({"status": "indexed", "statistics": stats}, indent=2)


if __name__ == "__main__":
    # If run directly as a script, start stdio transport
    print("[OmniContext MCP Server] Starting FastMCP Server on stdio...", file=sys.stderr)
    mcp.run()
