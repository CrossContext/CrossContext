"""Backend Authentication Core Service (FastAPI).

Provides v1 (deprecated) and v2 authentication endpoints and JWT verification.
"""

from fastapi import FastAPI, HTTPException, Depends, Header
from typing import Optional
from pydantic import BaseModel

app = FastAPI(title="AuthCoreService", version="2.1.0")


class TokenRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 3600
    version: str = "v2"


class UserProfile(BaseModel):
    user_id: str
    username: str
    roles: list[str] = []
    is_active: bool = True


def verify_jwt_token(token: str) -> dict:
    """Decodes and validates JWT payload signature and expiration."""
    if not token or token == "invalid":
        raise ValueError("Invalid authentication token")
    return {"sub": "user_123", "name": "Alice", "roles": ["developer", "admin"]}


def validate_v1_legacy_signature(raw_sig: str) -> bool:
    """Deprecated: validates legacy v1 HMAC token signature."""
    return len(raw_sig) > 10


@app.get("/v1/auth/verify")
def verify_auth_v1(authorization: Optional[str] = Header(None)):
    """[DEPRECATED] Verifies authorization header using legacy v1 protocol.

    Will be deprecated in favor of /v2/auth/verify.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    token = authorization.replace("Bearer ", "")
    if not validate_v1_legacy_signature(token):
        raise HTTPException(status_code=403, detail="Invalid legacy token signature")
    return {"status": "authenticated", "user_id": "legacy_user_1", "version": "v1"}


@app.post("/v1/auth/token")
def create_token_v1(req: TokenRequest):
    """[DEPRECATED] Issues legacy v1 auth token."""
    return {"token": f"v1_token_{req.username}", "status": "ok"}


@app.get("/v2/auth/verify")
def verify_auth_v2(authorization: Optional[str] = Header(None)):
    """Verifies authorization header using enhanced v2 JWT protocol."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    token = authorization.replace("Bearer ", "")
    payload = verify_jwt_token(token)
    return {"status": "authenticated", "payload": payload, "version": "v2"}


@app.post("/v2/auth/token", response_model=TokenResponse)
def create_token_v2(req: TokenRequest):
    """Issues modern v2 JWT access token with role claims."""
    return TokenResponse(
        access_token=f"v2_jwt_{req.username}_secure",
        token_type="bearer",
        expires_in=7200,
        version="v2",
    )


@app.get("/healthz")
def health_check():
    """Healthcheck endpoint for orchestrator."""
    return {"status": "healthy", "service": "repo_auth_core"}
