"""Instant 5-Second Environment Healthcheck for OmniContext."""

import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from common.models import CodeNode, CodeEdge, SymbolType, EdgeType
from mcp_server.parsers.treesitter_engine import TreeSitterEngine
from mcp_server.parsers.scip_indexer import SCIPIndexer
from mcp_server.storage.sqlite_graph import SQLiteGraphStorage
from mcp_server.tools import CodeGraphTools


def run_healthcheck():
    print("==================================================")
    print("🚀 Running OmniContext Environment Healthcheck...")
    print("==================================================")

    # 1. Check Data Models
    print("1/5 Checking Universal Data Models...", end=" ")
    node = CodeNode(
        id="test:file.py:test_fn:1",
        repo="test_repo",
        file_path="file.py",
        symbol_name="test_fn",
        symbol_type=SymbolType.FUNCTION,
        start_line=1,
        end_line=5,
        signature="def test_fn()",
        code_content="def test_fn():\n    pass\n",
        language="python",
    )
    assert node.symbol_name == "test_fn"
    print("✅ PASSED")

    # 2. Check SQLite Graph Storage & FTS5
    print("2/5 Checking SQLite Storage & FTS5 Index...", end=" ")
    storage = SQLiteGraphStorage(db_path=":memory:")
    storage.insert_node(node)
    found = storage.get_node_by_id(node.id)
    assert found is not None and found.symbol_name == "test_fn"
    fts_res = storage.search_nodes_fts("test_fn")
    assert len(fts_res) == 1
    print("✅ PASSED")

    # 3. Check AST Parser on Python & TypeScript
    print("3/5 Checking Boundary-Aware AST Engine...", end=" ")
    engine = TreeSitterEngine()
    testbed_py = root_dir / "testbed" / "repo_auth_core" / "main.py"
    py_nodes = engine.parse_file(testbed_py, repo="repo_auth_core")
    assert len(py_nodes) >= 5

    testbed_ts = root_dir / "testbed" / "repo_frontend_portal" / "src" / "api" / "authClient.ts"
    ts_nodes = engine.parse_file(testbed_ts, repo="repo_frontend_portal")
    assert len(ts_nodes) >= 2
    print("✅ PASSED")

    # 4. Check SCIP Cross-Repository Linker
    print("4/5 Checking Cross-Repository Dependency Linker...", end=" ")
    indexer = SCIPIndexer(storage=storage)
    repos = {
        "repo_auth_core": str(root_dir / "testbed" / "repo_auth_core"),
        "repo_frontend_portal": str(root_dir / "testbed" / "repo_frontend_portal"),
    }
    stats = indexer.index_multi_repos(repos)
    assert stats["repo_auth_core"] > 0
    assert stats["repo_frontend_portal"] > 0
    assert stats["total_edges_created"] > 0
    print(f"✅ PASSED ({stats['total_edges_created']} cross-repo edges indexed)")

    # 5. Check MCP Tool Execution
    print("5/5 Checking Deterministic MCP Graph Tools...", end=" ")
    tools = CodeGraphTools(storage=storage)
    def_res = tools.find_symbol_definition("verify_auth_v1")
    assert def_res["found_count"] >= 1

    blast = tools.blast_radius_analysis("verify_auth_v1")
    assert "repo_frontend_portal" in blast["cross_repo_impact"]
    print("✅ PASSED")

    print("==================================================")
    print("🎉 ALL 5/5 SUBSYSTEMS OPERATIONAL AND VERIFIED!")
    print("==================================================")


if __name__ == "__main__":
    run_healthcheck()
