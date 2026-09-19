"""
Unit Tests for Member 1: Ingestion & Multi-Language Graph Engine
Validates:
1. Multi-language AST parsing (Python, TypeScript/JavaScript, Go)
2. Dynamic endpoint and consumer extraction across languages
3. SCIP CrossRepoLinker with parameterized route matching (/users/{id} vs /users/123)
4. Cross-repo import bindings and package linkage
"""

import pytest
from common.models import CodeNode, CodeEdge, SymbolType, EdgeType
from mcp_server.parsers.treesitter_engine import TreeSitterEngine
from mcp_server.parsers.scip_indexer import CrossRepoLinker
from mcp_server.ingestion.github_ingester import GitHubRepoIngester


@pytest.fixture
def parser():
    return TreeSitterEngine()


@pytest.fixture
def linker():
    return CrossRepoLinker()


# =============================================================
# 1. Multi-Language AST Parsing Tests
# =============================================================

def test_python_fastapi_and_requests_parsing(parser):
    """Test Python AST extraction for FastAPI endpoints and requests consumers."""
    backend_code = """
from fastapi import APIRouter

router = APIRouter()

@router.get("/v1/users/{user_id}")
async def get_user_profile(user_id: str):
    \"\"\"Fetches user details by user ID.\"\"\"
    return {"user_id": user_id, "status": "active"}
"""
    nodes, edges = parser.parse_file("repo_backend", "src/api/users.py", backend_code)
    endpoint_nodes = [n for n in nodes if n.symbol_type == SymbolType.ENDPOINT]
    assert len(endpoint_nodes) == 1
    ep = endpoint_nodes[0]
    assert ep.symbol_name == "get_user_profile"
    assert ep.metadata.get("endpoint_route") == "/v1/users/{user_id}"
    assert ep.metadata.get("http_method") == "GET"

    consumer_code = """
import requests

def fetch_external_user(uid: str):
    resp = requests.get(f"https://api.internal/v1/users/{uid}")
    return resp.json()
"""
    c_nodes, _ = parser.parse_file("repo_consumer", "src/client/user_client.py", consumer_code)
    assert len(c_nodes) == 1
    cn = c_nodes[0]
    assert cn.metadata.get("consumes_endpoint") == "/v1/users/{uid}"
    assert cn.metadata.get("consumes_http_method") == "GET"


def test_python_flask_route_parsing(parser):
    """Test Flask @app.route with explicit methods parameter."""
    flask_code = """
from flask import Flask, request
app = Flask(__name__)

@app.route("/api/v2/auth/login", methods=["POST"])
def login_handler():
    return {"token": "jwt_sample"}
"""
    nodes, _ = parser.parse_file("repo_auth", "app.py", flask_code)
    ep_nodes = [n for n in nodes if n.symbol_type == SymbolType.ENDPOINT]
    assert len(ep_nodes) == 1
    assert ep_nodes[0].metadata.get("endpoint_route") == "/api/v2/auth/login"
    assert ep_nodes[0].metadata.get("http_method") == "POST"


def test_typescript_express_and_axios_ky_parsing(parser):
    """Test TypeScript/JavaScript AST parsing for Express routes and fetch/axios/ky consumers."""
    ts_code = """
import axios from 'axios';
import ky from 'ky';

export async function submitOrder(orderId: string) {
    const res = await axios.post(`/api/v1/orders/${orderId}`);
    return res.data;
}

export const fetchAuditLog = async () => {
    return await ky.get('/api/v1/audit/logs').json();
};
"""
    nodes, _ = parser.parse_file("repo_frontend", "src/services/orderService.ts", ts_code)
    assert len(nodes) == 2
    order_func = next(n for n in nodes if n.symbol_name == "submitOrder")
    assert "/v1/orders/" in order_func.metadata.get("consumes_endpoint", "")
    assert order_func.metadata.get("consumes_http_method") == "POST"

    audit_func = next(n for n in nodes if n.symbol_name == "fetchAuditLog")
    assert "/v1/audit/logs" in audit_func.metadata.get("consumes_endpoint", "")
    assert audit_func.metadata.get("consumes_http_method") == "GET"


def test_go_gin_and_http_client_parsing(parser):
    """Test Go parser extracting Gin endpoints and net/http client requests."""
    go_backend = """
package main

import "github.com/gin-gonic/gin"

func SetupRoutes(r *gin.Engine) {
    r.GET("/v1/healthz", func(c *gin.Context) {
        c.JSON(200, gin.H{"status": "ok"})
    })
}
"""
    nodes, _ = parser.parse_file("repo_go_svc", "main.go", go_backend)
    assert len(nodes) >= 1
    route_func = nodes[0]
    assert route_func.metadata.get("endpoint_route") == "/v1/healthz"
    assert route_func.metadata.get("http_method") == "GET"

    go_consumer = """
package client

import "net/http"

func CheckHealth() (*http.Response, error) {
    return http.Get("http://health-svc/v1/healthz")
}
"""
    c_nodes, _ = parser.parse_file("repo_gateway", "client.go", go_consumer)
    assert len(c_nodes) >= 1
    assert c_nodes[0].metadata.get("consumes_endpoint") == "/v1/healthz"
    assert c_nodes[0].metadata.get("consumes_http_method") == "GET"


# =============================================================
# 2. Parameterized Route Matching Tests
# =============================================================

def test_route_normalization_helpers():
    """Verify route normalization and parameter abstraction."""
    assert CrossRepoLinker._normalize_route("https://api.corp.internal/api/v1/users/info") == "/v1/users/info"
    assert CrossRepoLinker._normalize_route("/api/v2/auth/token?env=prod") == "/v2/auth/token"

    # Parameterized normalization
    assert CrossRepoLinker._normalize_parameterized_route("/users/{id}") == "/users/{_param_}"
    assert CrossRepoLinker._normalize_parameterized_route("/users/:userId") == "/users/{_param_}"
    assert CrossRepoLinker._normalize_parameterized_route("/users/<int:id>") == "/users/{_param_}"
    assert CrossRepoLinker._normalize_parameterized_route("/users/${userId}") == "/users/{_param_}"


def test_parameterized_route_matching():
    """Verify route matcher matches concrete path instances against endpoint templates."""
    # Template: /users/{id} vs Concrete: /users/123
    assert CrossRepoLinker._route_matches("/users/{id}", "/users/123") is True
    # Template with prefix: /api/v1/orders/{orderId}/items vs Consumer: /v1/orders/999/items
    assert CrossRepoLinker._route_matches("/api/v1/orders/{orderId}/items", "/v1/orders/999/items") is True
    # Template Express: /posts/:postId/comments vs Consumer: /posts/42/comments
    assert CrossRepoLinker._route_matches("/posts/:postId/comments", "/posts/42/comments") is True
    # Non-matching routes
    assert CrossRepoLinker._route_matches("/users/{id}", "/orders/123") is False
    assert CrossRepoLinker._route_matches("/users/{id}", "/users/123/profile") is False


def test_cross_repo_linking_with_path_parameters(linker):
    """Verify CrossRepoLinker links consumer to endpoint with path parameters across repos."""
    producer_node = CodeNode(
        id="repo_backend:api.py:get_user:10",
        repo="repo_backend",
        file_path="src/api.py",
        symbol_name="get_user",
        symbol_type=SymbolType.ENDPOINT,
        start_line=10,
        end_line=20,
        metadata={"endpoint_route": "/api/v1/users/{user_id}", "http_method": "GET"}
    )

    consumer_node = CodeNode(
        id="repo_frontend:client.ts:fetchUser:15",
        repo="repo_frontend",
        file_path="src/client.ts",
        symbol_name="fetchUser",
        symbol_type=SymbolType.FUNCTION,
        start_line=15,
        end_line=25,
        metadata={"consumes_endpoint": "/v1/users/user_9921", "consumes_http_method": "GET"}
    )

    edges = linker.link_repositories([producer_node, consumer_node])
    assert len(edges) == 1
    edge = edges[0]
    assert edge.caller_id == consumer_node.id
    assert edge.callee_id == producer_node.id
    assert edge.edge_type == EdgeType.CONSUMES_API


# =============================================================
# 3. Cross-Repo Import Binding Tests
# =============================================================

def test_cross_repo_import_and_sdk_linkage(linker):
    """Verify CrossRepoLinker establishes edges for cross-repo imports and SDK calls."""
    sdk_node = CodeNode(
        id="repo_shared_sdk:auth_client.py:AuthClient:5",
        repo="repo_shared_sdk",
        file_path="src/auth_client.py",
        symbol_name="AuthClient",
        symbol_type=SymbolType.CLASS,
        start_line=5,
        end_line=40
    )

    consumer_node = CodeNode(
        id="repo_portal:login.py:perform_login:12",
        repo="repo_portal",
        file_path="src/login.py",
        symbol_name="perform_login",
        symbol_type=SymbolType.FUNCTION,
        start_line=12,
        end_line=30,
        code_content="client = AuthClient()\nclient.verify_session()",
        metadata={"file_imports": ["from repo_shared_sdk.auth_client import AuthClient"]}
    )

    edges = linker.link_repositories([sdk_node, consumer_node])
    assert any(e.caller_id == consumer_node.id and e.callee_id == sdk_node.id for e in edges)


# =============================================================
# 4. Ingestion Resilience Tests
# =============================================================

def test_github_ingester_repo_name_extraction():
    """Verify GitHub URL and local path sanitization."""
    assert GitHubRepoIngester.extract_repo_name("https://github.com/pallets/flask.git") == "flask"
    assert GitHubRepoIngester.extract_repo_name("https://github.com/fastapi/fastapi/") == "fastapi"
    assert GitHubRepoIngester.extract_repo_name("local/path/to/my_service") == "my_service"
