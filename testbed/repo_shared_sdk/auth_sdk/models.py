"""Shared data contracts for internal microservices consuming AuthCore."""

from dataclasses import dataclass
from typing import Optional, List


@dataclass
class ClientSession:
    user_id: str
    token: str
    is_valid: bool
    roles: List[str]


@dataclass
class AuthConfig:
    endpoint_url: str = "http://localhost:8000"
    timeout_seconds: int = 5
    retry_attempts: int = 3
