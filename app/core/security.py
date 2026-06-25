"""
Admin authentication and authorization.

Admin routes are secured exclusively via Google Sign-In. The backend verifies
the Google ID token offline using the ``google-auth`` library, strictly enforces
``email_verified: true``, then validates the caller's identity against:

  1. The ``SUPER_ADMIN_EMAIL`` env variable — always granted root access.
  2. The ``admin_users`` MongoDB collection — accounts granted by the Super Admin.

No fallback authentication mechanism exists. If ``GOOGLE_CLIENT_ID`` is not
configured the service will return 503 rather than silently failing open.
"""

from __future__ import annotations

import asyncio
import logging
from functools import partial
from typing import Any

from fastapi import Depends, Header, HTTPException, Request, status

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)


class AdminPrincipal:
    """Represents an authenticated administrator."""

    def __init__(
        self,
        subject: str,
        role: str = "admin",
        claims: dict[str, Any] | None = None,
    ) -> None:
        self.subject = subject   # verified Google email address
        self.role = role         # "super_admin" | "admin"
        self.claims = claims or {}

    @property
    def is_super_admin(self) -> bool:
        return self.role == "super_admin"


async def _verify_google_id_token(
    token: str, google_client_id: str
) -> dict[str, Any]:
    """Verify a Google ID token offline using the google-auth library.

    Runs the synchronous verification in a thread-pool executor so it does not
    block the FastAPI event loop.

    Raises:
        ValueError: If the token is invalid, expired, or fails audience check.
    """
    from google.auth.transport import requests as google_requests
    from google.oauth2 import id_token as google_id_token

    loop = asyncio.get_event_loop()
    try:
        idinfo: dict[str, Any] = await loop.run_in_executor(
            None,
            partial(
                google_id_token.verify_oauth2_token,
                token,
                google_requests.Request(),
                google_client_id,
            ),
        )
    except Exception as exc:
        raise ValueError(f"Invalid Google ID token: {exc}") from exc

    # Strictly enforce email_verified — prevents spoofing with unverified emails
    if not idinfo.get("email_verified"):
        raise ValueError("Google account email is not verified.")

    return idinfo


async def admin_auth(
    request: Request,
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> AdminPrincipal:
    """FastAPI dependency for protecting admin routes.

    Requires a Google ID token in the ``Authorization: Bearer <token>`` header.
    The token is verified offline against ``GOOGLE_CLIENT_ID``, ``email_verified``
    is enforced, and the caller's email is matched against the Super Admin env
    variable or the ``admin_users`` MongoDB collection.
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="admin_auth_required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not settings.google_client_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="google_sso_not_configured",
        )

    token = authorization.split(" ", 1)[1].strip()
    try:
        idinfo = await _verify_google_id_token(token, settings.google_client_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    email: str = idinfo.get("email", "").lower().strip()
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="no_email_in_token",
        )

    # Super admin check (env variable — no DB lookup required)
    if settings.super_admin_email and email == settings.super_admin_email.lower().strip():
        logger.info("admin_auth_super_admin email=%s", email)
        return AdminPrincipal(subject=email, role="super_admin", claims=idinfo)

    # Regular admin check (MongoDB lookup)
    from app.db.mongo import mongo_state
    if mongo_state.db is not None:
        doc = await mongo_state.db.admin_users.find_one({"email": email})
        if doc:
            role = doc.get("role", "admin")
            logger.info("admin_auth_ok email=%s role=%s", email, role)
            return AdminPrincipal(subject=email, role=role, claims=idinfo)

    logger.warning("admin_auth_rejected email=%s", email)
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="insufficient_permissions",
    )
