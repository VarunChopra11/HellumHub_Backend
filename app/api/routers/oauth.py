"""
OAuth 2.0 endpoints for Google Home Account Linking.

Google uses a standard Authorization Code flow to link user accounts:

  1. User is redirected to GET /oauth/authorize with:
       client_id, redirect_uri, state, response_type=code
     The user is authenticated via Google Sign-In. For Streamlined Account
     Linking, Google passes a google_id_token assertion which is verified
     directly (no email+password needed). Falls back to rejecting the request
     if no assertion is provided (user must link manually via the app).

  2. Google server-side exchanges the code at POST /oauth/token with:
       grant_type=authorization_code, code, client_id, client_secret
     Response: { access_token, token_type, expires_in, refresh_token }

  3. Google refreshes at POST /oauth/token with:
       grant_type=refresh_token, refresh_token, client_id, client_secret
     Response: { access_token, token_type, expires_in, refresh_token }

Reference:
  https://developers.google.com/assistant/smarthome/develop/account-linking
"""

from __future__ import annotations

import asyncio
import logging
import secrets
import time
from datetime import UTC, datetime, timedelta
from functools import partial
from typing import Annotated
from urllib.parse import urlencode

import jwt
from bson import ObjectId
from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import RedirectResponse

from app.api.deps import get_db, get_user_repo
from app.core.config import Settings, get_settings
from app.repositories.user_repository import UserRepository
from app.schemas.smarthome import OAuthTokenResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/oauth", tags=["oauth"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _issue_access_token(user_id: str, settings: Settings) -> str:
    now = int(time.time())
    return jwt.encode(
        {
            "sub": user_id,
            "iat": now,
            "exp": now + settings.consumer_jwt_ttl_seconds,
            "type": "access",
        },
        settings.consumer_jwt_secret,
        algorithm=settings.consumer_jwt_algorithm,
    )


async def _verify_google_token(token: str, client_id: str) -> dict:
    """Verify Google ID token offline, enforce email_verified."""
    from google.auth.transport import requests as google_requests
    from google.oauth2 import id_token as google_id_token

    loop = asyncio.get_event_loop()
    try:
        idinfo: dict = await loop.run_in_executor(
            None,
            partial(
                google_id_token.verify_oauth2_token,
                token,
                google_requests.Request(),
                client_id,
            ),
        )
    except Exception as exc:
        raise ValueError(f"invalid_google_token: {exc}") from exc

    if not idinfo.get("email_verified"):
        raise ValueError("google_email_not_verified")

    return idinfo


# ---------------------------------------------------------------------------
# Authorization endpoint  — GET /oauth/authorize
# ---------------------------------------------------------------------------

@router.get("/authorize")
async def authorize(
    request: Request,
    client_id: str = Query(...),
    redirect_uri: str = Query(...),
    state: str = Query(...),
    response_type: str = Query(...),
    # Streamlined Account Linking: Google passes a google_id_token assertion.
    # When present we verify it and skip manual login entirely.
    google_id_token: str | None = Query(default=None),
    db=Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> RedirectResponse:
    """Issue an authorization code after verifying the consumer's identity.

    Supports Google Streamlined Account Linking: if Google provides a
    ``google_id_token`` assertion, we verify it directly. Otherwise the
    request is rejected — consumers must authenticate via the frontend app
    first, then link from there.
    """
    if client_id != settings.oauth_client_id:
        raise HTTPException(status_code=400, detail="invalid_client_id")
    if redirect_uri not in settings.oauth_redirect_uris:
        raise HTTPException(status_code=400, detail="invalid_redirect_uri")
    if response_type != "code":
        raise HTTPException(status_code=400, detail="unsupported_response_type")

    # Authenticate via Google ID token assertion (Streamlined Linking)
    if google_id_token and settings.google_client_id:
        try:
            idinfo = await _verify_google_token(google_id_token, settings.google_client_id)
        except ValueError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc

        user_repo = UserRepository(db)
        user_doc = await user_repo.upsert_by_google_sub(
            google_sub=idinfo["sub"],
            email=idinfo.get("email", ""),
            display_name=idinfo.get("name"),
        )
    else:
        # No assertion provided — reject and instruct user to link via the app
        raise HTTPException(
            status_code=400,
            detail=(
                "google_id_token_required — link your account via the Hellum app first, "
                "then connect Google Home from within the app."
            ),
        )

    # Issue authorization code
    code = secrets.token_urlsafe(32)
    expires_at = datetime.now(UTC) + timedelta(seconds=settings.oauth_auth_code_ttl_seconds)
    await db.oauth_codes.insert_one(
        {
            "code": code,
            "user_id": user_doc["_id"],
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "expires_at": expires_at,
            "used": False,
        }
    )

    params = urlencode({"code": code, "state": state})
    target = f"{redirect_uri}?{params}"
    logger.info("oauth_code_issued user_id=%s", user_doc["_id"])
    return RedirectResponse(url=target, status_code=302)


# ---------------------------------------------------------------------------
# Token endpoint  — POST /oauth/token
# ---------------------------------------------------------------------------

@router.post("/token", response_model=OAuthTokenResponse)
async def token(
    grant_type: Annotated[str, Form()],
    client_id: Annotated[str, Form()],
    client_secret: Annotated[str, Form()],
    code: Annotated[str | None, Form()] = None,
    redirect_uri: Annotated[str | None, Form()] = None,
    refresh_token: Annotated[str | None, Form()] = None,
    db=Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> OAuthTokenResponse:
    """Exchange an authorization code or refresh token for access/refresh tokens."""
    if client_id != settings.oauth_client_id or client_secret != settings.oauth_client_secret:
        raise HTTPException(status_code=401, detail="invalid_client")

    if grant_type == "authorization_code":
        return await _handle_auth_code_grant(code, redirect_uri, db, settings)
    elif grant_type == "refresh_token":
        return await _handle_refresh_token_grant(refresh_token, db, settings)
    else:
        raise HTTPException(status_code=400, detail="unsupported_grant_type")


async def _handle_auth_code_grant(
    code: str | None, redirect_uri: str | None, db, settings: Settings
) -> OAuthTokenResponse:
    if not code:
        raise HTTPException(status_code=400, detail="missing_code")

    code_doc = await db.oauth_codes.find_one_and_update(
        {"code": code, "used": False},
        {"$set": {"used": True}},
    )
    if not code_doc:
        raise HTTPException(status_code=400, detail="invalid_or_expired_code")

    if code_doc["expires_at"].replace(tzinfo=UTC) < datetime.now(UTC):
        raise HTTPException(status_code=400, detail="invalid_or_expired_code")

    return await _mint_token_pair(str(code_doc["user_id"]), db, settings)


async def _handle_refresh_token_grant(
    refresh_token: str | None, db, settings: Settings
) -> OAuthTokenResponse:
    if not refresh_token:
        raise HTTPException(status_code=400, detail="missing_refresh_token")

    token_doc = await db.refresh_tokens.find_one({"token": refresh_token})
    if not token_doc:
        raise HTTPException(status_code=400, detail="invalid_refresh_token")

    if token_doc["expires_at"].replace(tzinfo=UTC) < datetime.now(UTC):
        raise HTTPException(status_code=400, detail="invalid_refresh_token")

    user_id = str(token_doc["user_id"])
    await db.refresh_tokens.delete_one({"token": refresh_token})
    return await _mint_token_pair(user_id, db, settings)


async def _mint_token_pair(user_id: str, db, settings: Settings) -> OAuthTokenResponse:
    access_token = _issue_access_token(user_id, settings)
    new_refresh = secrets.token_urlsafe(48)
    expires_at = datetime.now(UTC) + timedelta(seconds=settings.consumer_refresh_token_ttl_seconds)
    await db.refresh_tokens.insert_one(
        {"token": new_refresh, "user_id": ObjectId(user_id), "expires_at": expires_at}
    )
    return OAuthTokenResponse(
        access_token=access_token,
        expires_in=settings.consumer_jwt_ttl_seconds,
        refresh_token=new_refresh,
    )
