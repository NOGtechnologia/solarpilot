"""Anmeldung, Ersteinrichtung des Admins und Benutzerverwaltung."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.auth import (
    COOKIE,
    TOKEN_DAYS,
    create_token,
    hash_password,
    limiter,
    optional_user,
    require_admin,
    verify_password,
)
from app.config import get_settings
from app.db import get_session
from app.models import User
from app.services.settings_store import get_section

router = APIRouter(prefix="/api", tags=["auth"])


class Credentials(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class NewUser(Credentials):
    password: str = Field(min_length=8, max_length=256)
    is_admin: bool = False


def _user_out(u: User) -> dict:
    return {"id": u.id, "username": u.username, "is_admin": u.is_admin}


def _set_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        COOKIE,
        token,
        max_age=TOKEN_DAYS * 86400,
        httponly=True,
        samesite="lax",
        secure=get_settings().cookie_secure,
        path="/",
    )


@router.get("/auth/status")
def auth_status(
    user: User | None = Depends(optional_user), session: Session = Depends(get_session)
) -> dict:
    has_users = session.exec(select(User.id)).first() is not None
    return {
        "has_users": has_users,
        "authenticated": user is not None,
        "user": _user_out(user) if user else None,
        "public_dashboard": bool(get_section(session, "general").get("public_dashboard")),
        "language": get_section(session, "general").get("language", "de"),
    }


@router.post("/auth/setup")
def setup_admin(body: NewUser, response: Response, session: Session = Depends(get_session)) -> dict:
    if session.exec(select(User.id)).first() is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Admin existiert bereits")
    user = User(
        username=body.username.strip(), password_hash=hash_password(body.password), is_admin=True
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    _set_cookie(response, create_token(user))
    return {"user": _user_out(user)}


@router.post("/auth/login")
def login(
    body: Credentials, request: Request, response: Response, session: Session = Depends(get_session)
) -> dict:
    key = request.client.host if request.client else "?"
    if limiter.blocked(key):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Zu viele Fehlversuche")
    user = session.exec(select(User).where(User.username == body.username.strip())).first()
    if user is None or not verify_password(body.password, user.password_hash):
        limiter.fail(key)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Benutzername oder Passwort falsch")
    limiter.reset(key)
    token = create_token(user)
    _set_cookie(response, token)
    return {"user": _user_out(user), "token": token}


@router.post("/auth/logout")
def logout(response: Response) -> dict:
    response.delete_cookie(COOKIE, path="/")
    return {"ok": True}


@router.get("/users")
def list_users(_: User = Depends(require_admin), session: Session = Depends(get_session)) -> list:
    return [_user_out(u) for u in session.exec(select(User).order_by(User.id)).all()]


@router.post("/users")
def create_user(
    body: NewUser, _: User = Depends(require_admin), session: Session = Depends(get_session)
) -> dict:
    if session.exec(select(User).where(User.username == body.username.strip())).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Benutzername vergeben")
    u = User(
        username=body.username.strip(),
        password_hash=hash_password(body.password),
        is_admin=body.is_admin,
    )
    session.add(u)
    session.commit()
    session.refresh(u)
    return _user_out(u)


class PasswordChange(BaseModel):
    password: str = Field(min_length=8, max_length=256)


@router.put("/users/{user_id}/password")
def change_password(
    user_id: int,
    body: PasswordChange,
    admin: User = Depends(require_admin),
    session: Session = Depends(get_session),
) -> dict:
    u = session.get(User, user_id)
    if not u:
        raise HTTPException(404, "Unbekannter Benutzer")
    u.password_hash = hash_password(body.password)
    session.add(u)
    session.commit()
    return {"ok": True}


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int, admin: User = Depends(require_admin), session: Session = Depends(get_session)
) -> dict:
    if user_id == admin.id:
        raise HTTPException(400, "Eigenes Konto kann nicht gelöscht werden")
    u = session.get(User, user_id)
    if not u:
        raise HTTPException(404, "Unbekannter Benutzer")
    session.delete(u)
    session.commit()
    return {"ok": True}
