"""Authentication routes for session-based sign-in."""

from __future__ import annotations

from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from lightrag.api.auth_sessions import (
    AuthenticatedUser,
    authenticate_user,
    clear_auth_cookie,
    get_current_user,
    session_manager,
    set_auth_cookie,
    serialize_user,
)


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class LoginResponse(BaseModel):
    user: Dict[str, str]


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest, response: Response) -> LoginResponse:
    user = authenticate_user(payload.username, payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    token = session_manager.create_session(user)
    set_auth_cookie(response, token)
    return LoginResponse(user=serialize_user(user))


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    response: Response,
    request: Request,
    _: AuthenticatedUser = Depends(get_current_user),
) -> dict:
    token = getattr(request.state, "session_token", None)
    if token:
        session_manager.revoke_session(token)
    clear_auth_cookie(response)
    response.status_code = status.HTTP_200_OK
    return {"status": "signed_out"}


@router.get("/me", response_model=LoginResponse)
async def me(user: AuthenticatedUser = Depends(get_current_user)) -> LoginResponse:
    return LoginResponse(user=serialize_user(user))
