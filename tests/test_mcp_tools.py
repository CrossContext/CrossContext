"""Unit Tests for MCP Deterministic Code Graph Tools."""

import pytest
from pathlib import Path
from mcp_server.parsers.scip_indexer import SCIPIndexer
from mcp_server.storage.sqlite_graph import SQLiteGraphStorage
from mcp_server.tools import CodeGraphTools


@pytest.fixture
def populated_tools(tmp_path):
    db_file = tmp_path / "test_mcp_graph.db"
    storage = SQLiteGraphStorage(db_path=str(db_file))
    indexer = SCIPIndexer(storage=storage)

    root = Path(__file__).resolve().parent.parent / "testbed"
    repos = {
        "repo_auth_core": str(root / "repo_auth_core"),
        "repo_frontend_portal": str(root / "repo_frontend_portal"),
    }
    indexer.index_multi_repos(repos)
    return CodeGraphTools(storage=storage)


def test_find_symbol_definition(populated_tools):
    res = populated_tools.find_symbol_definition("verify_jwt_token")
    assert res["found_count"] >= 1
    definition = res["definitions"][0]
    assert definition["symbol_name"] == "verify_jwt_token"
    assert definition["repo"] == "repo_auth_core"
    assert "Decodes and validates JWT" in definition["docstring"]


def test_get_usage_dependency_links(populated_tools):
    # Find endpoint node
    res = populated_tools.find_symbol_definition("verify_auth_v1")
    assert res["found_count"] >= 1
    endpoint_node = res["definitions"][0]

    dep_res = populated_tools.get_usage_dependency_links(endpoint_node["id"])
    assert "error" not in dep_res
    assert len(dep_res["edges"]) > 0

    # Verify cross-repo caller from repo_frontend_portal
    assert len(dep_res["cross_repo_callers"]) >= 1
    assert dep_res["cross_repo_callers"][0]["repo"] == "repo_frontend_portal"


def test_traverse_call_graph(populated_tools):
    res = populated_tools.traverse_call_graph(entry_symbol="verify_auth_v1", depth=2, direction="both")
    assert res["entry_symbol"] == "verify_auth_v1"
    assert len(res["nodes"]) >= 2
    assert len(res["impacted_repos"]) >= 2
    assert "repo_auth_core" in res["impacted_repos"]
    assert "repo_frontend_portal" in res["impacted_repos"]


def test_blast_radius_analysis(populated_tools):
    report = populated_tools.blast_radius_analysis("verify_auth_v1")
    assert report["target_symbol"] == "verify_auth_v1"
    assert "repo_frontend_portal" in report["cross_repo_impact"]
    assert len(report["affected_endpoints"]) >= 1
    assert any("Cross-repo impact" in act for act in report["recommended_actions"])


def test_get_ast_chunk(populated_tools):
    testbed_py = str(Path(__file__).resolve().parent.parent / "testbed" / "repo_auth_core" / "main.py")
    res = populated_tools.get_ast_chunk(testbed_py, start_line=1, end_line=10)
    assert "error" not in res
    assert res["line_count"] == 10
    assert "FastAPI" in res["code"]


def test_semantic_code_search(populated_tools):
    res = populated_tools.semantic_code_search("JWT")
    assert res["match_count"] >= 1
    assert any("JWT" in (n.get("signature", "") + n.get("docstring", "") + n.get("code_content", "")) for n in res["results"])
