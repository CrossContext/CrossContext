"""
OmniContext - Amazon OpenSearch Serverless (AOSS) Vector Store Adapter
Manages high-performance k-NN vector embeddings and hybrid AST retrieval on AWS.
"""

import os
import math
from typing import List, Dict, Any, Optional, Tuple
from common.models import CodeNode, SymbolType


class OpenSearchVectorStore:
    """Manages vector embeddings and hybrid search on Amazon OpenSearch Serverless."""

    INDEX_NAME = os.getenv("OPENSEARCH_INDEX", "omnicontext-symbols-v1")

    def __init__(
        self,
        endpoint: Optional[str] = None,
        region: Optional[str] = None,
        vector_dim: int = 1536
    ):
        self.endpoint = endpoint or os.getenv("OPENSEARCH_ENDPOINT", "")
        self.region = region or os.getenv("AWS_REGION", "us-east-1")
        self.vector_dim = vector_dim
        self._client = None
        self._local_fallback_store: List[Dict[str, Any]] = []

    @property
    def client(self):
        """Initializes OpenSearch client with AWS SigV4 authentication if endpoint is present."""
        if self._client is None and self.endpoint:
            from opensearchpy import OpenSearch, RequestsHttpConnection
            from requests_aws4auth import AWS4Auth
            import boto3

            credentials = boto3.Session().get_credentials()
            awsauth = AWS4Auth(
                credentials.access_key,
                credentials.secret_key,
                self.region,
                "aoss" if "aoss" in self.endpoint else "es",
                session_token=credentials.token
            )

            self._client = OpenSearch(
                hosts=[{'host': self.endpoint.replace("https://", "").rstrip("/"), 'port': 443}],
                http_auth=awsauth,
                use_ssl=True,
                verify_certs=True,
                connection_class=RequestsHttpConnection,
                timeout=30
            )
        return self._client

    def ensure_index(self):
        """Creates the k-NN vector index on OpenSearch Serverless if not exists."""
        if not self.endpoint or not self.client:
            return

        index_body = {
            "settings": {
                "index": {
                    "knn": True,
                    "knn.algo_param.ef_search": 100
                }
            },
            "mappings": {
                "properties": {
                    "symbol_vector": {
                        "type": "knn_vector",
                        "dimension": self.vector_dim,
                        "method": {
                            "name": "hnsw",
                            "space_type": "cosinesimil",
                            "engine": "nmslib",
                            "parameters": {
                                "ef_construction": 128,
                                "m": 16
                            }
                        }
                    },
                    "symbol_name": {"type": "keyword"},
                    "repo": {"type": "keyword"},
                    "file_path": {"type": "keyword"},
                    "symbol_type": {"type": "keyword"},
                    "docstring": {"type": "text"},
                    "code_content": {"type": "text"},
                    "start_line": {"type": "integer"},
                    "end_line": {"type": "integer"},
                }
            }
        }

        try:
            if not self.client.indices.exists(index=self.INDEX_NAME):
                self.client.indices.create(index=self.INDEX_NAME, body=index_body)
        except Exception as e:
            print(f"[OpenSearchStore] Notice: {e}")

    def index_nodes_with_embeddings(self, nodes_with_vectors: List[Tuple[CodeNode, List[float]]]):
        """Indexes symbols with their dense vector embeddings."""
        if self.endpoint and self.client:
            try:
                for node, vector in nodes_with_vectors:
                    doc = {
                        "symbol_vector": vector,
                        "symbol_name": node.symbol_name,
                        "repo": node.repo,
                        "file_path": node.file_path,
                        "symbol_type": node.symbol_type.value if hasattr(node.symbol_type, "value") else str(node.symbol_type),
                        "docstring": node.docstring or "",
                        "code_content": node.code_content or "",
                        "start_line": node.start_line,
                        "end_line": node.end_line,
                    }
                    self.client.index(index=self.INDEX_NAME, id=node.id, body=doc)
                return
            except Exception as e:
                print(f"[OpenSearchStore] OpenSearch index failed ({e}), falling back to local memory store.")

        # Local in-memory fallback
        for node, vector in nodes_with_vectors:
            self._local_fallback_store.append({
                "node": node,
                "vector": vector,
                "id": node.id
            })

    def search_similar(
        self,
        query_vector: List[float],
        repo_filter: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Searches for symbols by vector cosine similarity."""
        if self.endpoint and self.client:
            try:
                query: Dict[str, Any] = {
                    "size": limit,
                    "query": {
                        "knn": {
                            "symbol_vector": {
                                "vector": query_vector,
                                "k": limit
                            }
                        }
                    }
                }
                if repo_filter:
                    query["query"] = {
                        "bool": {
                            "must": [{"knn": {"symbol_vector": {"vector": query_vector, "k": limit}}}],
                            "filter": [{"term": {"repo": repo_filter}}]
                        }
                    }

                response = self.client.search(index=self.INDEX_NAME, body=query)
                hits = response.get("hits", {}).get("hits", [])
                results = []
                for h in hits:
                    src = h["_source"]
                    results.append({
                        "id": h["_id"],
                        "symbol_name": src["symbol_name"],
                        "repo": src["repo"],
                        "file_path": src["file_path"],
                        "symbol_type": src["symbol_type"],
                        "docstring": src["docstring"],
                        "code_content": src["code_content"],
                        "score": h["_score"]
                    })
                return results
            except Exception as e:
                print(f"[OpenSearchStore] Search error ({e}), using local fallback.")

        # Local cosine similarity calculation
        def cosine_similarity(v1: List[float], v2: List[float]) -> float:
            if not v1 or not v2 or len(v1) != len(v2):
                return 0.0
            dot = sum(a * b for a, b in zip(v1, v2))
            norm1 = math.sqrt(sum(a * a for a in v1))
            norm2 = math.sqrt(sum(b * b for b in v2))
            return dot / (norm1 * norm2) if norm1 > 0 and norm2 > 0 else 0.0

        scored = []
        for item in self._local_fallback_store:
            node: CodeNode = item["node"]
            if repo_filter and node.repo != repo_filter:
                continue
            sim = cosine_similarity(query_vector, item["vector"])
            scored.append({
                "id": node.id,
                "symbol_name": node.symbol_name,
                "repo": node.repo,
                "file_path": node.file_path,
                "symbol_type": node.symbol_type.value if hasattr(node.symbol_type, "value") else str(node.symbol_type),
                "docstring": node.docstring or "",
                "code_content": node.code_content or "",
                "score": sim
            })

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:limit]
