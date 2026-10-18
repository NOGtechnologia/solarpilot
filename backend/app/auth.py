"""Login: scrypt-Passwort-Hashes, JWT im httpOnly-Cookie (oder Bearer-Header)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import time
from collections import defaultdict, deque

import jwt
from fastapi import Depends, HTTPException, Request, WebSocket, status
from sqlmodel import Session, select

from .config import get_settings
from .db import get_session
from .models import User
from .services.settings_store import get_section

COOKIE = "sp_token"
TOKEN_DAYS = 30
SCRYPT_N, SCRYPT_R, SCRYPT_P = 2**14, 8, 1


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.scrypt(password.encode(), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=32)
    b = base64.b64encode
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${b(salt).decode()}${b(dk).decode()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, n, r, p, salt_b64, dk_b64 = stored.split("$")
        salt, dk = base64.b64decode(salt_b64), base64.b64decode(dk_b64)
        test = hashlib.scrypt(
            password.encode(), salt=salt, n=int(n), r=int(r), p=int(p), dklen=len(dk)
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(test, dk)


def _secret() -> str:
    return hashlib.sha256(f"jwt:{get_settings().resolved_secret()}".encode()).hexdigest()


def create_token(user: User) -> str:
    now = int(time.time())
    payload = {
        "sub": str(user.id),
        "name": user.username,
        "adm": user.is_admin,
        "iat": now,
        "exp": now + TOKEN_DAYS * 86400,
    }
    return jwt.encode(payload, _secret(), algorithm="HS256")


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, _secret(), algorithms=["HS256"])
    except jwt.PyJWTError:
        return None


def _token_from(headers, cookies) -> str | None:
    auth = headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return cookies.get(COOKIE)


def user_from_token(session: Session, token: str | None) -> User | None:
    if not token:
        return None
    data = decode_token(token)
    if not data:
        return None
    user = session.get(User, int(data["sub"]))
    return user


def optional_user(request: Request, session: Session = Depends(get_session)) -> User | None:
    return user_from_token(session, _token_from(request.headers, request.cookies))


def require_user(user: User | None = Depends(optional_user)) -> User:
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Nicht angemeldet")
    return user


def require_admin(user: User = Depends(require_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Nur für Administratoren")
    return user


def require_viewer(
    user: User | None = Depends(optional_user), session: Session = Depends(get_session)
) -> User | None:
    """Lesender Zugriff: angemeldet oder öffentliches Dashboard aktiviert."""
    if user is not None:
        return user
    if get_section(session, "general").get("public_dashboard"):
        return None
    if session.exec(select(User.id)).first() is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Einrichtung erforderlich")
    raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Nicht angemeldet")


def ws_allowed(ws: WebSocket, session: Session) -> bool:
    token = ws.query_params.get("token") or _token_from(ws.headers, ws.cookies)
    if user_from_token(session, token):
        return True
    return bool(get_section(session, "general").get("public_dashboard"))


class LoginLimiter:
    """Max. 10 Fehlversuche pro IP in 15 Minuten."""

    def __init__(self, limit: int = 10, window_s: int = 900) -> None:
        self.limit, self.window = limit, window_s
        self.fails: dict[str, deque[float]] = defaultdict(deque)

    def _prune(self, key: str) -> deque[float]:
        q = self.fails[key]
        cutoff = time.time() - self.window
        while q and q[0] < cutoff:
            q.popleft()
        return q

    def blocked(self, key: str) -> bool:
        return len(self._prune(key)) >= self.limit

    def fail(self, key: str) -> None:
        self._prune(key).append(time.time())

    def reset(self, key: str) -> None:
        self.fails.pop(key, None)


limiter = LoginLimiter()
