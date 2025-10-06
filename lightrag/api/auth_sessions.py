"""Cookie-based authentication helpers for EduMind Web UI."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Dict, Optional

from fastapi import HTTPException, Request, Response, status

from .auth import auth_handler

SESSION_COOKIE_NAME = "edumind_session"
SESSION_MAX_AGE_SECONDS = 60 * 60 * 8  # 8 hours


USERS: Dict[str, Dict[str, str]] = {
        "admin": {
            "id": "user-admin-001",
            "password": "admin-super-2024",
            "full_name": "Edumind Administrator",
            "role": "admin",
        },
        "maya": {
            "id": "user-mentor-maya",
            "password": "maya-leads-learning",
            "full_name": "Maya Flores",
            "role": "member",
        },
        "ryan": {
            "id": "user-curriculum-ryan",
            "password": "ryan-guides-2024",
            "full_name": "Ryan Chen",
            "role": "member",
        },
        "alex": {
            "id": "user-designer-alex",
            "password": "alex-builds-ideas",
            "full_name": "Alex Morgan",
            "role": "member",
        },
        "lee": {
            "id": "user-analyst-lee",
            "password": "lee-cares-edu",
            "full_name": "Jordan Lee",
            "role": "member",
        },
        "ivy": {
            "id": "user-research-ivy",
            "password": "ivy-discovers-joy",
            "full_name": "Ivy Das",
            "role": "member",
        },
    }


@dataclass(frozen=True)
class AuthenticatedUser:
    id: str
    username: str
    full_name: str
    role: str


def authenticate_user(username: str, password: str) -> Optional[AuthenticatedUser]:
    normalised = username.strip().lower()

    record = USERS.get(normalised)
    if not record:
        return None

    if password != record["password"]:
        return None

    return AuthenticatedUser(
        id=record["id"],
        username=normalised,
        full_name=record["full_name"],
        role=record["role"],
    )


def _generate_session_token(user: AuthenticatedUser) -> str:
    metadata = {
        "id": user.id,
        "full_name": user.full_name,
        "issued_at": datetime.utcnow().isoformat(),
    }
    expire_hours = max(1, SESSION_MAX_AGE_SECONDS // 3600)
    return auth_handler.create_token(
        username=user.username,
        role=user.role,
        metadata=metadata,
        custom_expire_hours=expire_hours,
    )


def _user_from_token(token: str) -> AuthenticatedUser:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
        )

    payload = auth_handler.validate_token(token)
    username = payload.get("username") or payload.get("sub")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session token"
        )

    metadata = payload.get("metadata", {}) or {}
    return AuthenticatedUser(
        id=metadata.get("id", username),
        username=username,
        full_name=metadata.get("full_name", username.title()),
        role=payload.get("role", "member"),
    )


def get_user_from_token(token: str) -> AuthenticatedUser:
    return _user_from_token(token)


def set_auth_cookie(response: Response, user: AuthenticatedUser) -> None:
    token = _generate_session_token(user)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=SESSION_MAX_AGE_SECONDS,
        expires=SESSION_MAX_AGE_SECONDS,
        httponly=True,
        secure=False,
        samesite="lax",
        path="/",
    )


def clear_auth_cookie(response: Response) -> None:
    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")


def get_current_user(request: Request) -> AuthenticatedUser:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    user = get_user_from_token(token)
    request.state.current_user = user
    request.state.session_token = token
    return user


def require_authenticated_user(request: Request) -> AuthenticatedUser:
    return get_current_user(request)


def require_admin(request: Request) -> AuthenticatedUser:
    user = get_current_user(request)
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator privileges required",
        )
    return user


def serialize_user(user: AuthenticatedUser) -> Dict[str, str]:
    return asdict(user)
