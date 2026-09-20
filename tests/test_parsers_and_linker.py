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


# =============================================================
# 5. False Positive Elimination & Contract Precision Tests
# =============================================================

def test_root_path_and_utility_methods_emit_zero_contracts(parser, linker):
    """Verify that utility functions and methods containing slashes emit zero false-positive contracts to root routes."""
    # 1. Producer exposes GET / (health_check)
    producer_node = CodeNode(
        id="ai-heuristic-evaluation:main.py:health_check:10",
        repo="ai-heuristic-evaluation",
        file_path="main.py",
        symbol_name="health_check",
        symbol_type=SymbolType.ENDPOINT,
        start_line=10,
        end_line=15,
        metadata={"endpoint_route": "/", "http_method": "GET"}
    )

    # 2. TypeScript file with various utility functions
    ts_utils = """
export function formatBytes(bytes: number, decimals = 2): string {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

export function toFirestore(data: any) {
    // Converts data to Firestore format / schema
    return { ...data, updatedAt: new Date() };
}

export function formatDate(d: Date): string {
    return `${d.getMonth() + 1}/${d.getDate()}/${d.getFullYear()}`;
}

export function isMacOS(): boolean {
    return navigator.platform.toUpperCase().indexOf('MAC') >= 0;
}
"""
    nodes, _ = parser.parse_file("frontend-web", "src/utils/formatters.ts", ts_utils)
    # Ensure none of these utilities were marked as consuming an API endpoint
    for node in nodes:
        assert "consumes_endpoint" not in node.metadata, f"Node {node.symbol_name} falsely identified as API consumer"

    # Link against producer node
    all_nodes = [producer_node] + nodes
    edges = linker.link_repositories(all_nodes)
    api_edges = [e for e in edges if e.edge_type == EdgeType.CONSUMES_API]
    assert len(api_edges) == 0, f"Expected 0 CONSUMES_API edges, found {len(api_edges)}"


def test_generic_and_builtin_symbols_no_cross_repo_calls(parser, linker):
    """Verify that generic identifiers (request, data, open, test) do not link across repo boundaries."""
    # Repo A defines a function or helper named 'request'
    ruxailab_node = CodeNode(
        id="RUXAILAB:request.py:request:5",
        repo="RUXAILAB",
        file_path="request.py",
        symbol_name="request",
        symbol_type=SymbolType.FUNCTION,
        start_line=5,
        end_line=12,
        code_content="def request(url):\n    return None"
    )

    # Repo B uses Flask's built-in request object and standard library open()
    sentiment_code = """
from flask import Flask, request, jsonify

app = Flask(__name__)

def analyze_sentiment():
    payload = request.get_json()
    with open("model_cache.txt") as f:
        data = f.read()
    return jsonify({"status": "ok"})
"""
    sentiment_nodes, _ = parser.parse_file("sentiment-analysis-api", "app.py", sentiment_code)
    all_nodes = [ruxailab_node] + sentiment_nodes

    edges = linker.link_repositories(all_nodes)
    # Ensure there is NO call edge linking sentiment-analysis-api to RUXAILAB's request symbol
    false_calls = [
        e for e in edges
        if e.edge_type == EdgeType.CALLS
        and "sentiment-analysis-api" in e.caller_id
        and "RUXAILAB" in e.callee_id
    ]
    assert len(false_calls) == 0, f"False cross-repo call edges found: {false_calls}"


def test_legitimate_cross_repo_contracts_preserved(parser, linker):
    """Verify that legitimate API contracts and SDK usages are properly linked."""
    producer_node = CodeNode(
        id="auth-service:auth.py:verify_token:20",
        repo="auth-service",
        file_path="src/auth.py",
        symbol_name="verify_token",
        symbol_type=SymbolType.ENDPOINT,
        start_line=20,
        end_line=30,
        metadata={"endpoint_route": "/v1/auth/verify", "http_method": "POST"}
    )

    client_code = """
import axios from 'axios';

export async function checkSession(token: string) {
    const res = await axios.post('/v1/auth/verify', { token });
    return res.data;
}
"""
    consumer_nodes, _ = parser.parse_file("portal-app", "src/services/auth.ts", client_code)
    assert len(consumer_nodes) >= 1
    consumer = [n for n in consumer_nodes if n.symbol_name == "checkSession"][0]
    assert consumer.metadata.get("consumes_endpoint") == "/v1/auth/verify"
    assert consumer.metadata.get("consumes_http_method") == "POST"

    edges = linker.link_repositories([producer_node, consumer])
    api_edges = [e for e in edges if e.edge_type == EdgeType.CONSUMES_API]
    assert len(api_edges) == 1
    assert api_edges[0].caller_id == consumer.id
    assert api_edges[0].callee_id == producer_node.id


# =============================================================
# 6. Universal Polyglot Language Parsing Tests
# =============================================================

def test_php_laravel_parsing(parser):
    """Test PHP parser on Laravel controllers, routes, and HTTP clients."""
    php_code = """<?php
namespace App\\Http\\Controllers;

use Illuminate\\Support\\Facades\\Http;

class InvoiceController extends Controller
{
    public function generatePdf(int $id)
    {
        $response = Http::post('https://pdf-service.internal/v1/render', ['id' => $id]);
        return response()->json($response->json());
    }
}
"""
    nodes, _ = parser.parse_file("laravel-pdf-generator", "app/Http/Controllers/InvoiceController.php", php_code)
    assert len(nodes) >= 2
    cls = next(n for n in nodes if n.symbol_name == "InvoiceController")
    assert cls.symbol_type == SymbolType.CLASS

    method = next(n for n in nodes if n.symbol_name == "generatePdf")
    assert method.symbol_type == SymbolType.METHOD
    assert method.metadata.get("consumes_endpoint") == "/v1/render"
    assert method.metadata.get("consumes_http_method") == "POST"

    routes_code = """<?php
use Illuminate\\Support\\Facades\\Route;

Route::get('/api/v1/invoices', [InvoiceController::class, 'index']);
Route::post('/api/v1/invoices/create', [InvoiceController::class, 'create']);
"""
    r_nodes, _ = parser.parse_file("laravel-pdf-generator", "routes/api.php", routes_code)
    ep_nodes = [n for n in r_nodes if n.symbol_type == SymbolType.ENDPOINT]
    assert len(ep_nodes) == 2
    assert any(n.metadata.get("endpoint_route") == "/api/v1/invoices" for n in ep_nodes)


def test_rust_actix_and_reqwest_parsing(parser):
    """Test Rust parser for Actix-web endpoints and Reqwest client calls."""
    rust_code = """
use actix_web::{get, post, web, HttpResponse, Responder};

pub struct OrderRequest {
    pub order_id: String,
}

#[get("/api/v1/orders/{order_id}")]
pub async fn get_order(path: web::Path<String>) -> impl Responder {
    HttpResponse::Ok().body("order")
}

pub async fn notify_shipping(order_id: &str) {
    let client = reqwest::Client::new();
    client.post("https://shipping.internal/v1/dispatch").send().await;
}
"""
    nodes, _ = parser.parse_file("rust-orders", "src/main.rs", rust_code)
    assert any(n.symbol_name == "OrderRequest" and n.symbol_type == SymbolType.CLASS for n in nodes)

    ep = next(n for n in nodes if n.symbol_name == "get_order")
    assert ep.symbol_type == SymbolType.ENDPOINT
    assert ep.metadata.get("endpoint_route") == "/api/v1/orders/{order_id}"
    assert ep.metadata.get("http_method") == "GET"

    consumer = next(n for n in nodes if n.symbol_name == "notify_shipping")
    assert consumer.metadata.get("consumes_endpoint") == "/v1/dispatch"
    assert consumer.metadata.get("consumes_http_method") == "POST"


def test_csharp_aspnet_parsing(parser):
    """Test C# parser for ASP.NET Core controllers and routes."""
    cs_code = """
using Microsoft.AspNetCore.Mvc;
using System.Net.Http;

namespace Billing.Controllers
{
    [ApiController]
    public class BillingController : ControllerBase
    {
        [HttpGet("/api/v1/charges")]
        public async Task<IActionResult> ListCharges()
        {
            return Ok();
        }
    }
}
"""
    nodes, _ = parser.parse_file("billing-service", "Controllers/BillingController.cs", cs_code)
    assert any(n.symbol_name == "BillingController" and n.symbol_type == SymbolType.CLASS for n in nodes)
    ep = next(n for n in nodes if n.symbol_name == "ListCharges")
    assert ep.symbol_type == SymbolType.ENDPOINT
    assert ep.metadata.get("endpoint_route") == "/api/v1/charges"
    assert ep.metadata.get("http_method") == "GET"


def test_ruby_rails_parsing(parser):
    """Test Ruby parser for controllers, methods, and routes."""
    rb_code = """
class PaymentsController < ApplicationController
  def process_payment
    response = Faraday.post("https://gateway.internal/v1/charge")
    render json: response.body
  end
end
"""
    nodes, _ = parser.parse_file("ruby-app", "app/controllers/payments_controller.rb", rb_code)
    cls = next(n for n in nodes if n.symbol_name == "PaymentsController")
    assert cls.symbol_type == SymbolType.CLASS
    m = next(n for n in nodes if n.symbol_name == "process_payment")
    assert m.metadata.get("consumes_endpoint") == "/v1/charge"
    assert m.metadata.get("consumes_http_method") == "POST"


def test_clojure_parsing(parser):
    """Test Clojure parser for defn, Compojure routes, and clj-http."""
    clj_code = """
(ns my-service.routes
  (:require [clj-http.client :as client]))

(defn calculate-metrics [a b]
  (+ a b))

(GET "/api/v1/health" []
  {:status 200 :body "OK"})
"""
    nodes, _ = parser.parse_file("clj-service", "src/routes.clj", clj_code)
    assert any(n.symbol_name == "calculate-metrics" and n.symbol_type == SymbolType.FUNCTION for n in nodes)
    assert any(n.symbol_type == SymbolType.ENDPOINT and n.metadata.get("endpoint_route") == "/api/v1/health" for n in nodes)


def test_c_cpp_parsing(parser):
    """Test C/C++ parser for classes, structs, and functions."""
    cpp_code = """
#include <iostream>

class EngineCore {
public:
    void initialize();
};

void run_diagnostics(int code) {
    std::cout << code << std::endl;
}
"""
    nodes, _ = parser.parse_file("cpp-engine", "src/engine.cpp", cpp_code)
    assert any(n.symbol_name == "EngineCore" and n.symbol_type == SymbolType.CLASS for n in nodes)
    assert any(n.symbol_name == "run_diagnostics" and n.symbol_type == SymbolType.FUNCTION for n in nodes)


def test_universal_polyglot_fallback_parsing(parser):
    """Test universal fallback parser on Shell, Dart, and Elixir code."""
    shell_code = """
#!/usr/bin/env bash

function deploy_service() {
    echo "Deploying..."
    curl "https://k8s.internal/v1/deploy"
}
"""
    nodes, _ = parser.parse_file("infra-scripts", "deploy.sh", shell_code)
    assert any(n.symbol_name == "deploy_service" for n in nodes)


def test_cross_language_api_contract_linkage(parser, linker):
    """Verify cross-language contract: PHP client calls Go endpoint, TypeScript calls Clojure endpoint."""
    # 1. Producer in Go: /v1/render
    go_code = """
package main

import "github.com/gin-gonic/gin"

func main() {
    r := gin.Default()
    r.POST("/v1/render", renderHandler)
}

func renderHandler(c *gin.Context) {
    c.JSON(200, gin.H{"status": "ok"})
}
"""
    go_nodes, _ = parser.parse_file("go-renderer", "main.go", go_code)

    # 2. Consumer in PHP: calls /v1/render
    php_code = """<?php
class PdfService {
    public function renderDocument() {
        return Http::post("https://go-renderer.internal/v1/render", []);
    }
}
"""
    php_nodes, _ = parser.parse_file("php-portal", "PdfService.php", php_code)

    edges = linker.link_repositories(go_nodes + php_nodes)
    api_edges = [
        e for e in edges
        if e.edge_type == EdgeType.CONSUMES_API
        and "php-portal" in e.caller_id
        and "go-renderer" in e.callee_id
    ]
    assert len(api_edges) >= 1


