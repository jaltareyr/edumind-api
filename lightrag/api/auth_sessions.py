"""Session-based authentication utilities for EduMind Web UI."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import hashlib
import secrets
import threading
from typing import Dict, Optional

from fastapi import Depends, HTTPException, Request, Response, status

# ---------------------------------------------------------------------------
# Public constants
# ---------------------------------------------------------------------------

SESSION_COOKIE_NAME = "edumind_session"
SESSION_MAX_AGE_SECONDS = 60 * 60 * 8  # 8 hours


# ---------------------------------------------------------------------------
# Models and helpers
# ---------------------------------------------------------------------------


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class AuthenticatedUser:
    id: str
    username: str
    full_name: str
    role: str


_HARDCODED_USERS: Dict[str, Dict[str, str]] = {
    "admin": {
        "id": "user-admin-001",
        "password_hash": _hash_password("admin-super-2024"),
        "full_name": "Edumind Administrator",
        "role": "admin",
    },
    "maya": {
        "id": "user-mentor-maya",
        "password_hash": _hash_password("maya-leads-learning"),
        "full_name": "Maya Flores",
        "role": "member",
    },
    "ryan": {
        "id": "user-curriculum-ryan",
        "password_hash": _hash_password("ryan-guides-2024"),
        "full_name": "Ryan Chen",
        "role": "member",
    },
    "alex": {
        "id": "user-designer-alex",
        "password_hash": _hash_password("alex-builds-ideas"),
        "full_name": "Alex Morgan",
        "role": "member",
    },
    "lee": {
        "id": "user-analyst-lee",
        "password_hash": _hash_password("lee-cares-edu"),
        "full_name": "Jordan Lee",
        "role": "member",
    },
    "ivy": {
        "id": "user-research-ivy",
        "password_hash": _hash_password("ivy-discovers-joy"),
        "full_name": "Ivy Das",
        "role": "member",
    },
}


def authenticate_user(username: str, password: str) -> Optional[AuthenticatedUser]:
    """Validate credentials against the hard-coded accounts."""

    record = _HARDCODED_USERS.get(username.strip().lower())
    if not record:
        return None

    if _hash_password(password) != record["password_hash"]:
        return None

    return AuthenticatedUser(
        id=record["id"],
        username=username.strip().lower(),
        full_name=record["full_name"],
        role=record["role"],
    )


# ---------------------------------------------------------------------------
# Session manager
# ---------------------------------------------------------------------------


class SessionManager:
    """Naive in-memory session manager sufficient for local development."""

    def __init__(self) -> None:
        self._sessions: Dict[str, Dict[str, object]] = {}
        self._lock = threading.Lock()

    def _is_expired(self, expires_at: datetime) -> bool:
        return datetime.utcnow() >= expires_at

    def create_session(self, user: AuthenticatedUser) -> str:
        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(seconds=SESSION_MAX_AGE_SECONDS)
        with self._lock:
            self._sessions[token] = {
                "user": user,
                "expires_at": expires_at,
            }
        return token

    def get_session(self, token: str) -> Optional[AuthenticatedUser]:
        if not token:
            return None

        with self._lock:
            payload = self._sessions.get(token)
            if not payload:
                return None

            expires_at = payload["expires_at"]
            if self._is_expired(expires_at):
                # Clean up expired session
                self._sessions.pop(token, None)
                return None

            # Refresh expiry on access
            payload["expires_at"] = datetime.utcnow() + timedelta(
                seconds=SESSION_MAX_AGE_SECONDS
            )
            return payload["user"]

    def revoke_session(self, token: str) -> None:
        if not token:
            return
        with self._lock:
            self._sessions.pop(token, None)


session_manager = SessionManager()


# ---------------------------------------------------------------------------
# Dependencies and helpers for FastAPI routers
# ---------------------------------------------------------------------------


def set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=SESSION_MAX_AGE_SECONDS,
        httponly=True,
        secure=False,
        samesite="lax",
        path="/",
    )


def clear_auth_cookie(response: Response) -> None:
    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")


def get_current_user(request: Request) -> AuthenticatedUser:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    user = session_manager.get_session(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    request.state.current_user = user
    request.state.session_token = token
    return user


def require_authenticated_user(user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
    return user


def require_admin(user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator privileges required",
        )
    return user


def serialize_user(user: AuthenticatedUser) -> Dict[str, str]:
    return asdict(user)

