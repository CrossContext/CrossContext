"""
Tests for AWS Bedrock Connector & OpenSearch Serverless Adapter
"""

import pytest
from agent_orchestrator.bedrock_client import BedrockClient
from mcp_server.storage.opensearch_store import OpenSearchVectorStore
from common.models import CodeNode, SymbolType


def test_bedrock_client_connection_check():
    client = BedrockClient(region_name="us-east-1")
    status = client.check_connection()
    assert "connected" in status
    assert "mode" in status
    assert "region" in status
    assert status["region"] == "us-east-1"


def test_bedrock_titan_embedding_generation():
    client = BedrockClient(region_name="us-east-1")
    vec = client.generate_embedding("def verify_legacy_auth(): pass", dimensions=256)
    assert isinstance(vec, list)
    assert len(vec) == 256
    assert all(isinstance(x, (float, int)) for x in vec)


def test_opensearch_vector_store_fallback():
    store = OpenSearchVectorStore(endpoint="", region="us-east-1", vector_dim=128)
    
    node1 = CodeNode(
        id="repo_auth_core:auth.py:verify_legacy_auth:24",
        repo="repo_auth_core",
        file_path="src/api/auth.py",
        symbol_name="verify_legacy_auth",
        symbol_type=SymbolType.ENDPOINT,
        start_line=24,
        end_line=32,
        docstring="Legacy auth endpoint"
    )

    vector1 = [0.1] * 128
    store.index_nodes_with_embeddings([(node1, vector1)])

    query_vec = [0.1] * 128
    results = store.search_similar(query_vec, limit=3)

    assert len(results) >= 1
    assert results[0]["symbol_name"] == "verify_legacy_auth"
    assert results[0]["repo"] == "repo_auth_core"
