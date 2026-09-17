"""Unit Tests for TreeSitterEngine and SCIPIndexer."""

import pytest
from pathlib import Path
from common.models import SymbolType, EdgeType
from mcp_server.parsers.treesitter_engine import TreeSitterEngine
from mcp_server.parsers.scip_indexer import SCIPIndexer
from mcp_server.storage.sqlite_graph import SQLiteGraphStorage


@pytest.fixture
def test_storage(tmp_path):
    db_file = tmp_path / "test_graph.db"
    return SQLiteGraphStorage(db_path=str(db_file))


def test_python_ast_parsing():
    engine = TreeSitterEngine()
    testbed_py = Path(__file__).resolve().parent.parent / "testbed" / "repo_auth_core" / "main.py"
    assert testbed_py.exists(), "testbed repo_auth_core/main.py must exist"

    nodes = engine.parse_file(testbed_py, repo="repo_auth_core")
    assert len(nodes) >= 5

    symbol_names = [n.symbol_name for n in nodes]
    assert "verify_jwt_token" in symbol_names
    assert "verify_auth_v1" in symbol_names
    assert "verify_auth_v2" in symbol_names

    # Verify FastAPI endpoint metadata extraction
    v1_endpoint = next(n for n in nodes if n.symbol_name == "verify_auth_v1")
    assert v1_endpoint.symbol_type == SymbolType.ENDPOINT
    assert v1_endpoint.metadata.get("route_path") == "/v1/auth/verify"
    assert v1_endpoint.metadata.get("http_method") == "GET"


def test_typescript_ast_parsing():
    engine = TreeSitterEngine()
    testbed_ts = Path(__file__).resolve().parent.parent / "testbed" / "repo_frontend_portal" / "src" / "api" / "authClient.ts"
    assert testbed_ts.exists(), "testbed authClient.ts must exist"

    nodes = engine.parse_file(testbed_ts, repo="repo_frontend_portal")
    assert len(nodes) >= 2

    symbols = {n.symbol_name: n for n in nodes}
    assert "AuthClient" in symbols or "verifySessionToken" in symbols

    # Check API call extraction
    client_func = symbols.get("verifySessionToken")
    if client_func:
        assert "/v1/auth/verify" in client_func.metadata.get("api_calls", [])


def test_boundary_aware_chunking():
    engine = TreeSitterEngine()
    testbed_py = Path(__file__).resolve().parent.parent / "testbed" / "repo_auth_core" / "main.py"
    chunks = engine.chunk_file(testbed_py, repo="repo_auth_core")

    assert len(chunks) > 0
    for chunk in chunks:
        assert chunk.start_line <= chunk.end_line
        assert chunk.code_content
        assert chunk.token_count_estimate > 0


def test_cross_repo_scip_indexing(test_storage):
    indexer = SCIPIndexer(storage=test_storage)
    root = Path(__file__).resolve().parent.parent / "testbed"

    repos = {
        "repo_auth_core": str(root / "repo_auth_core"),
        "repo_frontend_portal": str(root / "repo_frontend_portal"),
    }

    stats = indexer.index_multi_repos(repos)
    assert stats["repo_auth_core"] > 0
    assert stats["repo_frontend_portal"] > 0
    assert stats["total_edges_created"] > 0

    # Verify cross-repo CONSUMES_API edge
    all_edges = test_storage.get_all_edges()
    cross_repo_edges = [e for e in all_edges if e.caller_repo != e.callee_repo]
    assert len(cross_repo_edges) > 0

    api_edge = next((e for e in cross_repo_edges if e.edge_type == EdgeType.CONSUMES_API), None)
    assert api_edge is not None
    assert api_edge.caller_repo == "repo_frontend_portal"
    assert api_edge.callee_repo == "repo_auth_core"
