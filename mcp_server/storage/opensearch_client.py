"""
CrossContext - Dual-Mode Vector Store Adapter
Supports both:
1. Cloud Mode (ENV=aws): Amazon OpenSearch Serverless (AOSS) + Amazon Titan Text Embeddings v2
2. Local Mode (ENV=local): In-memory cosine similarity & lexical cache (Zero AWS credentials needed)
"""

import os
import json
import math
import time
from typing import List, Dict, Any, Optional
from pathlib import Path

from common.models import CodeNode, SymbolType


class TitanEmbeddingClient:
    """Invokes Amazon Bedrock Titan Text Embeddings v2 with circuit breaker fallback."""
    def __init__(self, region_name: str = "us-east-1"):
        self.region_name = region_name
        self.model_id = os.getenv("BEDROCK_EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v2:0")
        self._client = None
        self._bedrock_available: Optional[bool] = None
        self._last_error_time: float = 0

    def _get_client(self):
        if self._client is None:
            import boto3
            self._client = boto3.client("bedrock-runtime", region_name=self.region_name)
        return self._client

    def generate_embedding(self, text: str, dimensions: int = 1024) -> List[float]:
        # Circuit breaker: If Bedrock failed recently (within 60s), use fast deterministic fallback
        if self._bedrock_available is False:
            if time.time() - self._last_error_time < 60:
                return self._fallback_pseudo_embedding(text, dimensions)
            else:
                self._bedrock_available = None  # Reset circuit breaker

        try:
            client = self._get_client()
            payload = {
                "inputText": text[:8192],  # Titan v2 input limit
                "dimensions": dimensions,
                "normalize": True
            }
            response = client.invoke_model(
                modelId=self.model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(payload)
            )
            body = json.loads(response["body"].read())
            self._bedrock_available = True
            return body["embedding"]
        except Exception:
            # Trip circuit breaker on failure to prevent 3000+ sequential HTTP timeouts
            self._bedrock_available = False
            self._last_error_time = time.time()
            return self._fallback_pseudo_embedding(text, dimensions)

    @staticmethod
    def _fallback_pseudo_embedding(text: str, dimensions: int = 1024) -> List[float]:
        """Generates deterministic unit vector based on character frequencies."""
        vec = [0.0] * dimensions
        for i, char in enumerate(text):
            idx = (ord(char) * (i + 1)) % dimensions
            vec[idx] += 1.0
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]


class DualModeVectorStore:
    """
    Dual-mode storage adapter. Automatically detects ENV='aws' vs ENV='local'.
    Allows seamless local execution while maintaining full Amazon OpenSearch Serverless compatibility.
    """
    def __init__(self):
        self.env = os.getenv("ENV", "local").lower()
        self.aoss_endpoint = os.getenv("AOSS_ENDPOINT", "")
        self.index_name = os.getenv("AOSS_INDEX_NAME", "crosscontext-code-index")
        self.region = os.getenv("AWS_REGION", "us-east-1")
        
        self.embedding_client = TitanEmbeddingClient(region_name=self.region)
        
        # Local fallback in-memory store
        self._local_documents: Dict[str, Dict[str, Any]] = {}
        self._local_vectors: Dict[str, List[float]] = {}

    def index_node(self, node: CodeNode) -> bool:
        """Indexes a CodeNode with dense vector representations."""
        return self.index_nodes([node])

    def index_nodes(self, nodes: List[CodeNode], progress_cb: Optional[Any] = None) -> bool:
        """Batch indexes CodeNodes into OpenSearch Serverless or Local store."""
        if not nodes:
            return True

        if self.env == "aws" and self.aoss_endpoint:
            return self._index_opensearch(nodes)
        else:
            return self._index_local(nodes, progress_cb=progress_cb)

    def _index_local(self, nodes: List[CodeNode], progress_cb: Optional[Any] = None) -> bool:
        """Parallel local memory indexing with Amazon Bedrock Titan Text Embeddings v2."""
        from concurrent.futures import ThreadPoolExecutor, as_completed

        # Register all documents in memory for fast lexical search
        for node in nodes:
            searchable_text = f"{node.symbol_name} {node.signature} {node.docstring}\n{node.code_content}"
            self._local_documents[node.id] = {
                "node": node,
                "text": searchable_text.lower()
            }

        # Select primary architecture symbols (endpoints, classes, functions) for Titan v2 embeddings
        primary_nodes = [
            n for n in nodes
            if n.symbol_type in (SymbolType.ENDPOINT, SymbolType.CLASS, SymbolType.FUNCTION)
        ]
        target_nodes = primary_nodes[:60] if len(primary_nodes) > 60 else primary_nodes
        total_targets = len(target_nodes)

        if not total_targets:
            return True

        def _embed_node(node: CodeNode):
            text = f"{node.symbol_name} {node.signature} {node.docstring}\n{node.code_content}"
            vec = self.embedding_client.generate_embedding(text)
            return node.id, vec

        completed = 0
        if progress_cb:
            progress_cb("embedding", f"Generating Amazon Titan v2 embeddings (0/{total_targets})...", 0.9)
        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = [executor.submit(_embed_node, n) for n in target_nodes]
            for future in as_completed(futures):
                try:
                    nid, vec = future.result()
                    self._local_vectors[nid] = vec
                    completed += 1
                    if progress_cb and (completed % 5 == 0 or completed == total_targets):
                        progress_cb(
                            "embedding",
                            f"Generating Amazon Titan v2 embeddings ({completed}/{total_targets})...",
                            0.7 + (0.25 * (completed / total_targets))
                        )
                except Exception:
                    pass

        return True

    def _index_opensearch(self, nodes: List[CodeNode]) -> bool:
        """Indexes into Amazon OpenSearch Serverless collection via requests / opensearch-py."""
        # Note: In AWS mode, constructs OpenSearch bulk payload
        # Falls back to local if AOSS is not reachable
        try:
            from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
            import boto3

            credentials = boto3.Session().get_credentials()
            auth = AWSV4SignerAuth(credentials, self.region, "aoss")
            host = self.aoss_endpoint.replace("https://", "").replace("http://", "").strip("/")
            
            client = OpenSearch(
                hosts=[{"host": host, "port": 443}],
                http_auth=auth,
                use_ssl=True,
                verify_certs=True,
                connection_class=RequestsHttpConnection,
                timeout=30
            )

            actions = []
            for node in nodes:
                text = f"{node.symbol_name} {node.signature} {node.docstring}\n{node.code_content}"
                embedding = self.embedding_client.generate_embedding(text)
                doc = {
                    "node_id": node.id,
                    "repo": node.repo,
                    "file_path": node.file_path,
                    "symbol_name": node.symbol_name,
                    "symbol_type": node.symbol_type.value,
                    "start_line": node.start_line,
                    "end_line": node.end_line,
                    "signature": node.signature,
                    "docstring": node.docstring,
                    "code_content": node.code_content,
                    "vector_embedding": embedding
                }
                client.index(index=self.index_name, id=node.id, body=doc)
            return True
        except Exception:
            # Fallback to local storage if AWS network/auth fails
            return self._index_local(nodes)

    def search_semantic(self, query: str, repo: Optional[str] = None, limit: int = 5) -> List[CodeNode]:
        """
        Executes dense vector semantic search against either OpenSearch Serverless
        or the local vector memory store.
        """
        if self.env == "aws" and self.aoss_endpoint:
            results = self._search_opensearch(query, repo=repo, limit=limit)
            if results:
                return results

        return self._search_local(query, repo=repo, limit=limit)

    def _search_local(self, query: str, repo: Optional[str] = None, limit: int = 5) -> List[CodeNode]:
        """In-memory cosine similarity search."""
        if not self._local_vectors:
            return []

        query_vec = self.embedding_client.generate_embedding(query)
        scored_nodes = []

        for node_id, doc in self._local_documents.items():
            node: CodeNode = doc["node"]
            if repo and node.repo != repo:
                continue

            node_vec = self._local_vectors[node_id]
            # Cosine similarity
            dot = sum(q * n for q, n in zip(query_vec, node_vec))
            # Keyword bonus for exact substring matches
            if any(term in doc["text"] for term in query.lower().split()):
                dot += 0.3
            scored_nodes.append((dot, node))

        scored_nodes.sort(key=lambda x: x[0], reverse=True)
        return [node for _, node in scored_nodes[:limit]]

    def _search_opensearch(self, query: str, repo: Optional[str] = None, limit: int = 5) -> List[CodeNode]:
        """Executes k-NN query on Amazon OpenSearch Serverless."""
        try:
            from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
            import boto3

            credentials = boto3.Session().get_credentials()
            auth = AWSV4SignerAuth(credentials, self.region, "aoss")
            host = self.aoss_endpoint.replace("https://", "").replace("http://", "").strip("/")

            client = OpenSearch(
                hosts=[{"host": host, "port": 443}],
                http_auth=auth,
                use_ssl=True,
                verify_certs=True,
                connection_class=RequestsHttpConnection,
                timeout=15
            )

            query_vec = self.embedding_client.generate_embedding(query)
            query_body = {
                "size": limit,
                "query": {
                    "knn": {
                        "vector_embedding": {
                            "vector": query_vec,
                            "k": limit
                        }
                    }
                }
            }
            if repo:
                query_body["query"] = {
                    "bool": {
                        "must": [{"term": {"repo": repo}}],
                        "should": [query_body["query"]]
                    }
                }

            res = client.search(index=self.index_name, body=query_body)
            hits = res.get("hits", {}).get("hits", [])
            results = []
            for hit in hits:
                src = hit["_source"]
                results.append(CodeNode(
                    id=src["node_id"],
                    repo=src["repo"],
                    file_path=src["file_path"],
                    symbol_name=src["symbol_name"],
                    symbol_type=SymbolType(src.get("symbol_type", "function")),
                    start_line=src["start_line"],
                    end_line=src["end_line"],
                    signature=src.get("signature", ""),
                    docstring=src.get("docstring", ""),
                    code_content=src.get("code_content", "")
                ))
            return results
        except Exception:
            return []

    def get_stats(self) -> Dict[str, Any]:
        return {
            "mode": self.env,
            "local_indexed_symbols": len(self._local_documents),
            "aoss_configured": bool(self.aoss_endpoint),
            "embedding_model": self.embedding_client.model_id
        }
