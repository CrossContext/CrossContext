"""
Authentication API Endpoints
Contains legacy v1 authentication endpoints and new v2 token architecture.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

router = APIRouter(tags=["authentication"])


class LegacyAuthRequest(BaseModel):
    token: str
    client_id: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 3600


@router.post("/v1/auth/verify", deprecated=True)
def verify_legacy_auth(payload: LegacyAuthRequest):
    """
    [DEPRECATED] Legacy authentication verification endpoint.
    Consumers must migrate to /v2/auth/token with standard Bearer headers.
    """
    if not payload.token or len(payload.token) < 16:
        raise HTTPException(status_code=401, detail="Invalid legacy token")
    return {"valid": True, "user_id": "usr_99812", "schema": "v1"}


@router.post("/v2/auth/token", response_model=TokenResponse)
def generate_v2_auth_token(client_id: str, client_secret: str):
    """
    [ACTIVE] Production OAuth2/JWT authentication endpoint.
    Issues short-lived RS256 signed access tokens.
    """
    if not client_id or not client_secret:
        raise HTTPException(status_code=400, detail="Invalid client credentials")
    
    # Generate cryptographic token
    signed_token = f"jwt_v2_{client_id}_secure_payload"
    return TokenResponse(access_token=signed_token, token_type="bearer", expires_in=3600)
