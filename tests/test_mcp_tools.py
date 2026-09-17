"""Unit & Integration Tests for OmniContext MCP Code Graph Tools."""

import pytest
from pathlib import Path
from mcp_server.tools import CodeGraphToolManager
from mcp_server.parsers.treesitter_engine import TreeSitterEngine
from mcp_server.parsers.scip_indexer import CrossRepoLinker
from common.models import SymbolType, EdgeType


@pytest.fixture
def populated_tool_manager(tmp_path):
    db_file = tmp_path / "test_mcp.db"
    manager = CodeGraphToolManager(db_path=str(db_file))
    root = Path(__file__).resolve().parent.parent / "testbed"

    repos = {
        "repo_auth_core": str(root / "repo_auth_core"),
        "repo_frontend_portal": str(root / "repo_frontend_portal"),
    }
    manager.index_repositories(repos)
    return manager


def test_get_symbol_definition(populated_tool_manager):
    res = populated_tool_manager.get_symbol_definition("verify_legacy_auth")
    assert res["found"] is True
    assert res["count"] >= 1
    sym = res["symbols"][0]
    assert sym["symbol_name"] == "verify_legacy_auth"
    assert sym["repo"] == "repo_auth_core"
    assert sym["symbol_type"] == "endpoint"


def test_get_usage_dependency_links(populated_tool_manager):
    res = populated_tool_manager.get_usage_dependency_links("verify_legacy_auth")
    assert res["found"] is True
    assert res["upstream_callers_count"] >= 1
    caller = res["upstream_callers"][0]
    assert caller["repo"] == "repo_frontend_portal"


def test_traverse_call_graph(populated_tool_manager):
    res = populated_tool_manager.traverse_call_graph("verify_legacy_auth", depth=3)
    assert res["root_symbol"] == "verify_legacy_auth"
    assert len(res["upstream_callers"]) >= 1
    assert any("repo_frontend_portal" in f for f in res["blast_radius_files"])


def test_get_ast_chunk(populated_tool_manager):
    sym_def = populated_tool_manager.get_symbol_definition("verify_legacy_auth")
    node_id = sym_def["symbols"][0]["id"]

    chunk = populated_tool_manager.get_ast_chunk(node_id)
    assert chunk["found"] is True
    assert "verify_legacy_auth" in chunk["code_content"]
    assert chunk["lines"] != ""


def test_absolute_url_cleaning_and_method_matching():
    engine = TreeSitterEngine()
    linker = CrossRepoLinker()

    ts_code = """
import { authClient } from "./services/authClient";

export async function checkSession(token: string) {
    const res = await fetch("https://auth.internal.corp/api/v1/auth/verify", {
        method: "POST",
        body: JSON.stringify({ token })
    });
    return res.json();
}
"""
    frontend_nodes, _ = engine.parse_file("repo_frontend", "session.ts", ts_code)
    assert len(frontend_nodes) >= 1
    fe_node = frontend_nodes[0]
    assert CrossRepoLinker._normalize_route(fe_node.metadata.get("consumes_endpoint")) == "/v1/auth/verify"
    assert fe_node.metadata.get("consumes_http_method") == "POST"

    py_code = """
from fastapi import APIRouter

router = APIRouter()

@router.post("/v1/auth/verify")
def verify_auth_post(req: dict):
    return {"status": "ok"}

@router.get("/v1/auth/verify")
def verify_auth_get():
    return {"status": "ok"}
"""
    backend_nodes, _ = engine.parse_file("repo_backend", "auth.py", py_code)
    assert len(backend_nodes) == 2

    # Cross-repo link should accurately match POST handler
    edges = linker.link_repositories(frontend_nodes + backend_nodes)
    assert len(edges) == 1
    edge = edges[0]
    assert edge.edge_type == EdgeType.CONSUMES_API
    assert "verify_auth_post" in edge.callee_id


def test_spring_controller_prefix_composition():
    engine = TreeSitterEngine()
    java_code = """
package com.auth.controller;

import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1")
public class AuthController {

    @GetMapping("/users")
    public String getUsers() {
        return "users";
    }
}
"""
    nodes, _ = engine.parse_file("repo_java", "AuthController.java", java_code)
    endpoint_node = next((n for n in nodes if n.symbol_type == SymbolType.ENDPOINT), None)
    assert endpoint_node is not None
    # Verifies controller prefix composition
    assert endpoint_node.metadata.get("endpoint_route") == "/api/v1/users"
    assert endpoint_node.metadata.get("http_method") == "GET"


def test_go_brace_boundary_chunking():
    engine = TreeSitterEngine()
    # 45 line Go function
    go_body = "\n".join([f"    x_{i} := {i}" for i in range(40)])
    go_code = f"""package main

func LargeProcessor(data string) int {{
{go_body}
    return 42
}}
"""
    nodes, _ = engine.parse_file("repo_go", "large.go", go_code)
    assert len(nodes) == 1
    node = nodes[0]
    # End line should encompass the whole function, not truncated to line 30
    assert node.end_line >= 40
    assert "return 42" in node.code_content
