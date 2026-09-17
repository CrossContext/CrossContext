"""
Unit & Integration Test for Tree-sitter Parser, Cross-Repo Linker, and Blast-Radius Traversal
"""

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from mcp_server.parsers.treesitter_engine import TreeSitterEngine
from mcp_server.parsers.scip_indexer import CrossRepoLinker
from mcp_server.storage.sqlite_graph import SQLiteGraphStore
from common.models import EdgeType, SymbolType


def test_cross_repo_pipeline():
    print("Testing End-to-End Ingestion & Cross-Repo Linking Pipeline...")
    parser = TreeSitterEngine()
    linker = CrossRepoLinker()
    store = SQLiteGraphStore(":memory:")

    # 1. Parse Backend Service
    backend_dir = PROJECT_ROOT / "testbed" / "repo_auth_core"
    backend_nodes, backend_edges = parser.parse_directory("repo_auth_core", str(backend_dir))
    print(f"  Backend Extracted: {len(backend_nodes)} symbols, {len(backend_edges)} internal edges")

    # Verify endpoint extraction
    endpoint_names = [n.symbol_name for n in backend_nodes if n.symbol_type == SymbolType.ENDPOINT]
    assert "verify_legacy_auth" in endpoint_names, f"Expected verify_legacy_auth, found {endpoint_names}"

    # 2. Parse Frontend Consumer
    frontend_dir = PROJECT_ROOT / "testbed" / "repo_frontend_portal"
    frontend_nodes, frontend_edges = parser.parse_directory("repo_frontend_portal", str(frontend_dir))
    print(f"  Frontend Extracted: {len(frontend_nodes)} symbols, {len(frontend_edges)} internal edges")

    # 3. Discover Cross-Repository Edges
    all_nodes = backend_nodes + frontend_nodes
    cross_edges = linker.link_repositories(all_nodes)
    print(f"  Discovered {len(cross_edges)} Cross-Repository Edges!")

    assert len(cross_edges) >= 1, "Failed to discover cross-repository dependency link!"
    edge = cross_edges[0]
    print(f"  Cross-Repo Edge: `{edge.caller_id}` --[{edge.edge_type.value}]--> `{edge.callee_id}`")
    assert edge.edge_type == EdgeType.CONSUMES_API

    # 4. Insert into SQLite Edge Matrix
    store.insert_nodes(all_nodes)
    store.insert_edges(backend_edges + frontend_edges + cross_edges)

    # 5. Execute Blast Radius Traversal for deprecating legacy auth
    traversal = store.traverse_blast_radius("verify_legacy_auth", max_depth=3)
    print("\n--- Blast Radius Traversal Result ---")
    print(traversal.summary())
    for f in traversal.blast_radius_files:
        print(f"  Affected File: {f}")

    assert len(traversal.upstream_callers) >= 1, "No upstream callers found in blast radius!"
    assert any("repo_frontend_portal" in f for f in traversal.blast_radius_files), "Frontend repo was not caught in blast radius!"

    print("\nSUCCESS: Cross-Repository Code Context Engine accurately resolved multi-repo dependencies!")


if __name__ == "__main__":
    test_cross_repo_pipeline()
