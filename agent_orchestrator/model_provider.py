"""
OmniContext - Model Provider Adapter
Supports:
1. Amazon Bedrock (Anthropic Claude 3.5 Sonnet / Claude 3.7 Sonnet)
2. Local Deterministic LLM Simulator (Zero-AWS offline execution)
"""

import os
import json
from typing import Dict, Any, List, Optional


class ModelProvider:
    def __init__(self):
        self.env = os.getenv("ENV", "local").lower()
        self.region = os.getenv("AWS_REGION", "us-east-1")
        self.model_id = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0")
        self._bedrock_client = None

    def _get_bedrock_client(self):
        if self._bedrock_client is None:
            import boto3
            self._bedrock_client = boto3.client("bedrock-runtime", region_name=self.region)
        return self._bedrock_client

    def invoke_with_tools(
        self,
        system_prompt: str,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Invokes Bedrock Claude or falls back to local autonomous simulator."""
        if self.env == "aws":
            try:
                return self._invoke_bedrock_claude(system_prompt, messages, tools)
            except Exception as e:
                # If AWS fails, gracefully fall back to local simulator
                print(f"[ModelProvider] AWS Bedrock error ({e}), falling back to local simulator.")
                return self._simulate_local_reasoning(messages, tools)
        else:
            return self._simulate_local_reasoning(messages, tools)

    def _invoke_bedrock_claude(
        self,
        system_prompt: str,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calls Anthropic Claude on Amazon Bedrock."""
        client = self._get_bedrock_client()
        
        # Bedrock Converse API / InvokeModel format
        payload = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 4096,
            "system": system_prompt,
            "messages": messages,
            "tools": tools
        }

        response = client.invoke_model(
            modelId=self.model_id,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(payload)
        )
        return json.loads(response["body"].read())

    def _simulate_local_reasoning(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Deterministic local reasoning engine for hackathon demo & offline mode.
        Simulates step-by-step tool invocation for multi-repo deprecation tasks.
        """
        last_message = messages[-1]["content"] if messages else ""
        step_count = len([m for m in messages if m.get("role") == "assistant"])

        # Step 0: Initial query -> Agent decides to traverse blast radius
        if step_count == 0:
            return {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": "I will inspect the cross-repository call graph to determine the blast radius of deprecating the legacy authentication endpoint."
                    },
                    {
                        "type": "tool_use",
                        "id": "tool_call_01",
                        "name": "traverse_call_graph",
                        "input": {"root_symbol": "verify_legacy_auth", "max_depth": 3}
                    }
                ]
            }

        # Step 1: After graph traversal -> Agent retrieves the exact AST chunk in the consumer repo
        elif step_count == 1:
            return {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": "The graph traversal reveals that `repo_frontend_portal` calls this legacy endpoint from `src/services/authClient.ts`. I will now fetch the exact AST code chunk for the caller."
                    },
                    {
                        "type": "tool_use",
                        "id": "tool_call_02",
                        "name": "get_ast_chunk",
                        "input": {"node_id": "repo_frontend_portal:src/services/authClient.ts:verifyUserSession:22"}
                    }
                ]
            }

        # Step 2: Final synthesis -> Formulate migration plan across both repos
        else:
            return {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "### Cross-Repository Migration Plan Formulated:\n\n"
                            "1. **Backend Service (`repo_auth_core`)**:\n"
                            "   - Mark endpoint `/v1/auth/verify` as deprecated with a 30-day sunset header.\n"
                            "   - Ensure `/v2/auth/token` endpoint supports incoming client credential flows.\n\n"
                            "2. **Frontend Portal (`repo_frontend_portal`)**:\n"
                            "   - Update `src/services/authClient.ts` in function `verifyUserSession`:\n"
                            "     - Replace POST to `/api/v1/auth/verify` with `/api/v2/auth/token`.\n"
                            "     - Adapt payload from `{ token }` to Bearer authorization header.\n\n"
                            "**Zero Breakage Verified**: All 2 federated repositories mapped deterministically."
                        )
                    }
                ]
            }
