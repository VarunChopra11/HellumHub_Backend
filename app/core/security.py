import time
from typing import Any

import jwt
from fastapi import Depends, Header, HTTPException, status

from app.core.config import Settings, get_settings


class AdminPrincipal:
    def __init__(self, subject: str, claims: dict[str, Any] | None = None) -> None:
        self.subject = subject
        self.claims = claims or {}


def _verify_jwt(token: str, settings: Settings) -> AdminPrincipal:
    if not settings.jwt_secret:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="JWT not configured")

    kwargs: dict[str, Any] = {}
    if settings.jwt_audience:
        kwargs["audience"] = settings.jwt_audience

    try:
        claims = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm], **kwargs)
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid JWT") from exc

    exp = claims.get("exp")
    if exp is not None and float(exp) < time.time():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Expired JWT")

    subject = str(claims.get("sub", "admin"))
    return AdminPrincipal(subject=subject, claims=claims)


async def admin_auth(
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> AdminPrincipal:
    if settings.admin_api_key and x_api_key == settings.admin_api_key:
        return AdminPrincipal(subject="apikey-admin")

    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        return _verify_jwt(token, settings)

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
