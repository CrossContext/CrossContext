"""
CrossContext - Test Suite for Dynamic Cross-Repository Diff Generator & Org Blueprint
Tests:
1. Dynamic Unified Diff Synthesis from AST Graph Nodes
2. Blast Radius Propagation to Coordinated Pull Request Specs
3. Cross-Repo API Contract Matrix Analysis & ORG_CONTEXT Generation
"""

import pytest
from common.models import CodeNode, CodeEdge, SymbolType, EdgeType
from mcp_server.storage.sqlite_graph import SQLiteGraphStore
from mcp_server.tools import CodeGraphToolManager
from mcp_server.context_generator import OrgContextGenerator
from agent_orchestrator.diff_generator import CrossRepoDiffGenerator


@pytest.fixture
def memory_tool_manager():
    """Sets up an in-memory graph store with multi-repo nodes and edges."""
    tm = CodeGraphToolManager(":memory:")
    store = tm.graph_store

    # 1. Producer nodes (repo_backend)
    prod_node = CodeNode(
        id="repo_backend:src/api/auth.py:verify_legacy_auth:20",
        repo="repo_backend",
        file_path="src/api/auth.py",
        symbol_name="verify_legacy_auth",
        symbol_type=SymbolType.ENDPOINT,
        start_line=20,
        end_line=30,
        signature="@app.post('/v1/auth/verify')",
        code_content='''@app.post("/v1/auth/verify")
def verify_legacy_auth(req: TokenRequest):
    return {"status": "authenticated", "user_id": req.user_id}
''',
        metadata={"endpoint_route": "/v1/auth/verify", "http_method": "POST"}
    )

    # 2. Consumer nodes (repo_frontend)
    cons_node = CodeNode(
        id="repo_frontend:src/services/client.ts:loginUser:10",
        repo="repo_frontend",
        file_path="src/services/client.ts",
        symbol_name="loginUser",
        symbol_type=SymbolType.FUNCTION,
        start_line=10,
        end_line=22,
        signature="async function loginUser(id: string)",
        code_content='''async function loginUser(id: string) {
    const res = await axios.post("/v1/auth/verify", { user_id: id });
    return res.data;
}
''',
        metadata={"consumes_endpoint": "/v1/auth/verify", "consumes_http_method": "POST"}
    )

    # 3. Cross-repo edge
    edge = CodeEdge(
        caller_id=cons_node.id,
        callee_id=prod_node.id,
        edge_type=EdgeType.CONSUMES_API,
        confidence=1.0,
        metadata={"route": "/v1/auth/verify", "http_method": "POST"}
    )

    store.insert_nodes([prod_node, cons_node])
    store.insert_edges([edge])
    return tm


def test_dynamic_diff_from_graph(memory_tool_manager):
    """Verifies that CrossRepoDiffGenerator dynamically derives PRs and patches from graph nodes."""
    generator = CrossRepoDiffGenerator(tool_manager=memory_tool_manager)
    res = generator.synthesize_cross_repo_patches("Deprecate /v1/auth/verify and update callers to /v2/auth/token")

    assert res["status"] == "success"
    assert res["total_repositories"] == 2
    assert res["total_files_affected"] == 2
    assert res["total_additions"] > 0
    assert res["total_deletions"] >= 0

    repos = [pr["repo"] for pr in res["pull_requests"]]
    assert "repo_backend" in repos
    assert "repo_frontend" in repos

    # Verify Producer PR
    backend_pr = next(pr for pr in res["pull_requests"] if pr["repo"] == "repo_backend")
    assert "deprecated=True" in backend_pr["patches"][0]["new_content"]
    assert "Sunset" in backend_pr["patches"][0]["new_content"]
    assert "repo_frontend#migration" in backend_pr["cross_linked_prs"]

    # Verify Consumer PR
    frontend_pr = next(pr for pr in res["pull_requests"] if pr["repo"] == "repo_frontend")
    assert "/v2/auth/token" in frontend_pr["patches"][0]["new_content"]
    assert "repo_backend#migration" in frontend_pr["cross_linked_prs"]


def test_org_blueprint_generation(memory_tool_manager):
    """Verifies architecture analysis and AI-optimized blueprint context generation."""
    generator = OrgContextGenerator(memory_tool_manager.graph_store)
    analysis = generator.analyze_organization()

    assert analysis["total_repositories"] == 2
    assert analysis["total_symbols"] == 2
    assert analysis["cross_repo_contracts_count"] == 1

    contract = analysis["cross_repo_contracts"][0]
    assert contract["caller_repo"] == "repo_frontend"
    assert contract["callee_repo"] == "repo_backend"
    assert contract["route"] == "/v1/auth/verify"

    # Verify Markdown Context text
    ai_context = generator.generate_ai_optimized_context()
    assert "CROSSCONTEXT FEDERATED ORGANIZATION CODEBASE BLUEPRINT" in ai_context
    assert "repo_backend" in ai_context
    assert "repo_frontend" in ai_context
    assert "--consumes_api [POST /v1/auth/verify]-->" in ai_context
