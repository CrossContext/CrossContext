"""Unit & Integration Tests for OmniContext MCP Code Graph Tools."""

import pytest
from pathlib import Path
from mcp_server.tools import CodeGraphToolManager
from common.models import SymbolType


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
    # Check that caller is from frontend portal
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


def test_multi_language_parsing():
    from mcp_server.parsers.treesitter_engine import TreeSitterEngine

    engine = TreeSitterEngine()

    # Test Go parsing
    go_code = """
package auth

type SessionManager struct {
    SecretKey string
}

func (s *SessionManager) ValidateToken(token string) bool {
    return len(token) > 0
}
"""
    go_nodes, _ = engine.parse_file("repo_go", "session.go", go_code)
    assert len(go_nodes) >= 2
    assert any(n.symbol_name == "ValidateToken" for n in go_nodes)

    # Test Java parsing
    java_code = """
package com.auth.controller;

import org.springframework.web.bind.annotation.*;

@RestController
public class AuthController {

    @GetMapping("/api/v1/auth/verify")
    public AuthResponse verifyToken(@RequestHeader String token) {
        return new AuthResponse(true);
    }
}
"""
    java_nodes, _ = engine.parse_file("repo_java", "AuthController.java", java_code)
    assert len(java_nodes) >= 2
    endpoint_node = next((n for n in java_nodes if n.symbol_type == SymbolType.ENDPOINT), None)
    assert endpoint_node is not None
    assert endpoint_node.metadata.get("endpoint_route") == "/api/v1/auth/verify"
