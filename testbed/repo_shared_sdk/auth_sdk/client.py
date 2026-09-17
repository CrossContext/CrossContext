"""Shared Python SDK for AuthCore Service."""

import requests
from typing import Dict, Any, Optional


class AuthCoreClient:
    """Client library for internal microservices to verify auth tokens."""

    def __init__(self, endpoint_url: str = "http://localhost:8000"):
        self.endpoint_url = endpoint_url.rstrip("/")

    def verify_token(self, token: str) -> Dict[str, Any]:
        """Calls backend /v1/auth/verify to check token validity."""
        url = f"{self.endpoint_url}/v1/auth/verify"
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.get(url, headers=headers, timeout=5)
        resp.raise_for_status()
        return resp.json()

    def get_user_claims(self, token: str) -> Dict[str, Any]:
        """Fetches claims using verify_token."""
        result = self.verify_token(token)
        return result.get("payload", {})
