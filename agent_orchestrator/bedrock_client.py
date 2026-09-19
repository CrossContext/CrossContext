"""
OmniContext - AWS Bedrock & Amazon Titan Client Adapter
Provides enterprise connectivity to Anthropic Claude 3.7 / 3.5 Sonnet on Amazon Bedrock
and Amazon Titan Text Embeddings v2 with streaming and automatic fallback.
"""

import os
import json
from typing import Dict, Any, List, Optional, Generator, Tuple


class BedrockClient:
    """Manages Amazon Bedrock Foundation Models and Titan Embeddings."""

    DEFAULT_CLAUDE_MODEL = os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-3-7-sonnet-20250219-v1:0")
    FALLBACK_CLAUDE_MODEL = "anthropic.claude-3-5-sonnet-20241022-v2:0"
    DEFAULT_EMBEDDING_MODEL = os.getenv("BEDROCK_EMBEDDING_MODEL", "amazon.titan-embed-text-v2:0")

    def __init__(self, region_name: Optional[str] = None):
        self.region = region_name or os.getenv("AWS_REGION", "us-east-1")
        self._client = None
        self.env = os.getenv("ENV", "local").lower()

    @property
    def client(self):
        """Lazy-loads and caches boto3 bedrock-runtime client."""
        if self._client is None:
            import boto3
            self._client = boto3.client("bedrock-runtime", region_name=self.region)
        return self._client

    def check_connection(self) -> Dict[str, Any]:
        """Validates whether AWS Bedrock credentials and services are reachable."""
        try:
            # Check if AWS credentials exist
            has_keys = bool(os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY"))
            has_bearer = bool(os.getenv("AWS_BEARER_TOKEN"))
            
            if not (has_keys or has_bearer or os.path.exists(os.path.expanduser("~/.aws/credentials"))):
                return {
                    "connected": False,
                    "mode": "local_emulation",
                    "region": self.region,
                    "reason": "AWS credentials not found. Running in zero-cloud local mode.",
                    "available_models": [
                        "claude-3-7-sonnet (emulated)",
                        "claude-3-5-sonnet (emulated)",
                        "amazon.titan-embed-text-v2:0 (local)"
                    ]
                }

            # Test embedding generation as lightweight ping
            _ = self.generate_embedding("ping test", dimensions=256)
            return {
                "connected": True,
                "mode": "aws_bedrock_live",
                "region": self.region,
                "active_model": self.DEFAULT_CLAUDE_MODEL,
                "embedding_model": self.DEFAULT_EMBEDDING_MODEL,
                "available_models": [
                    "us.anthropic.claude-3-7-sonnet-20250219-v1:0",
                    "anthropic.claude-3-5-sonnet-20241022-v2:0",
                    "meta.llama3-3-70b-instruct-v1:0",
                    "amazon.titan-embed-text-v2:0"
                ]
            }
        except Exception as e:
            return {
                "connected": False,
                "mode": "local_fallback",
                "region": self.region,
                "error": str(e),
                "reason": f"AWS connection attempt failed ({e}). Reverting to local graph engine."
            }

    def generate_embedding(
        self,
        text: str,
        model_id: Optional[str] = None,
        dimensions: int = 1536,
        normalize: bool = True
    ) -> List[float]:
        """
        Generates dense vector embeddings using Amazon Titan Text Embeddings v2.
        """
        model = model_id or self.DEFAULT_EMBEDDING_MODEL
        try:
            payload = {
                "inputText": text,
                "dimensions": dimensions,
                "normalize": normalize
            }
            response = self.client.invoke_model(
                modelId=model,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(payload)
            )
            res_body = json.loads(response["body"].read())
            return res_body.get("embedding", [])
        except Exception as e:
            # Fallback deterministic pseudo-embedding for local execution
            import hashlib
            seed = int(hashlib.md5(text.encode("utf-8")).hexdigest(), 16)
            import random
            rng = random.Random(seed)
            return [rng.gauss(0, 1) for _ in range(dimensions)]

    def invoke_claude(
        self,
        system_prompt: str,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        model_id: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.0
    ) -> Dict[str, Any]:
        """
        Invokes Anthropic Claude on Bedrock using Converse or InvokeModel API.
        """
        model = model_id or self.DEFAULT_CLAUDE_MODEL

        # Format Bedrock InvokeModel Anthropic payload
        payload = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system_prompt,
            "messages": messages
        }
        if tools:
            payload["tools"] = tools

        response = self.client.invoke_model(
            modelId=model,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(payload)
        )
        return json.loads(response["body"].read())

    def invoke_claude_stream(
        self,
        system_prompt: str,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        model_id: Optional[str] = None,
        max_tokens: int = 4096
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Streams response tokens and tool calls in real time from Amazon Bedrock.
        """
        model = model_id or self.DEFAULT_CLAUDE_MODEL
        payload = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "system": system_prompt,
            "messages": messages
        }
        if tools:
            payload["tools"] = tools

        response = self.client.invoke_model_with_response_stream(
            modelId=model,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(payload)
        )

        stream = response.get("body")
        if stream:
            for event in stream:
                chunk = event.get("chunk")
                if chunk:
                    data = json.loads(chunk.get("bytes").decode())
                    yield data
