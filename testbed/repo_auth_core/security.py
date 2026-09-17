"""Security and cryptographic operations for repo_auth_core."""

import hmac
import hashlib
from typing import Dict, Any


def hash_password(password: str, salt: str = "secret_salt") -> str:
    """Computes SHA256 password hash."""
    return hashlib.sha256((password + salt).encode()).hexdigest()


def generate_session_cookie(user_id: str, secret_key: str) -> str:
    """Generates signed session cookie for user."""
    signature = hmac.new(secret_key.encode(), user_id.encode(), hashlib.sha256).hexdigest()
    return f"{user_id}.{signature}"


def verify_session_cookie(cookie: str, secret_key: str) -> bool:
    """Validates session cookie authenticity."""
    parts = cookie.split(".")
    if len(parts) != 2:
        return False
    user_id, signature = parts
    expected_sig = hmac.new(secret_key.encode(), user_id.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, expected_sig)
