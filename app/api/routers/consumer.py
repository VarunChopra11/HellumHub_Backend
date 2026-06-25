"""
Consumer self-service API.

All routes under /api/v1/ serve the mobile/web frontend used by end-consumers.

Authentication flows:
  POST /api/v1/auth/google  — Exchange a Google ID token for a Hellum JWT pair.

Device provisioning (MQTT Binding Token flow):
  POST /api/v1/devices/binding-token — Request a binding token to give to an
                                        ESP32 during BLE provisioning.

Device management (after MQTT provisioning completes):
  GET    /api/v1/devices           — List own devices
  PATCH  /api/v1/devices/{mac}     — Rename a device
  DELETE /api/v1/devices/{mac}     — Release device ownership
"""

from __future__ import annotations

import asyncio
import logging
import secrets
import time
from datetime import UTC, datetime, timedelta
from functools import partial
from typing import Annotated

import jwt
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.api.deps import (
    get_current_consumer_user,
    get_db,
    get_smarthome_device_repo,
    get_user_repo,
)
from app.core.config import Settings, get_settings
from app.repositories.smarthome_device_repository import SmartHomeDeviceRepository
from app.repositories.user_repository import UserRepository
from app.schemas.smarthome import BindingTokenResponse, SmartHomeDeviceResponse, DeviceRenameRequest, EndpointResponse
from app.schemas.user import ConsumerTokenResponse, GoogleAuthRequest, UserResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["consumer"])


# ---------------------------------------------------------------------------
# Google ID token verification helper (runs in thread pool — synchronous lib)
# ---------------------------------------------------------------------------

async def _verify_google_id_token(token: str, client_id: str) -> dict:
    """Verify a Google ID token offline. Enforces email_verified."""
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
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"invalid_google_id_token: {exc}",
        ) from exc

    if not idinfo.get("email_verified"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="google_email_not_verified",
        )

    return idinfo


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------

def _issue_access_token(user_id: str, settings: Settings) -> str:
    now = int(time.time())
    return jwt.encode(
        {"sub": user_id, "iat": now, "exp": now + settings.consumer_jwt_ttl_seconds, "type": "access"},
        settings.consumer_jwt_secret,
        algorithm=settings.consumer_jwt_algorithm,
    )


def _issue_refresh_token() -> str:
    return secrets.token_urlsafe(48)


async def _mint_token_pair(user_id: str, db, settings: Settings) -> ConsumerTokenResponse:
    """Mint a fresh access + refresh token pair and persist the refresh token."""
    access_token = _issue_access_token(user_id, settings)
    refresh = _issue_refresh_token()
    expires_at = datetime.now(UTC) + timedelta(seconds=settings.consumer_refresh_token_ttl_seconds)
    await db.refresh_tokens.insert_one(
        {"token": refresh, "user_id": ObjectId(user_id), "expires_at": expires_at}
    )
    return ConsumerTokenResponse(
        access_token=access_token,
        expires_in=settings.consumer_jwt_ttl_seconds,
        refresh_token=refresh,
    )


# ---------------------------------------------------------------------------
# POST /api/v1/auth/google
# ---------------------------------------------------------------------------

@router.post("/auth/google", response_model=ConsumerTokenResponse)
async def google_sign_in(
    body: GoogleAuthRequest,
    settings: Settings = Depends(get_settings),
    user_repo: UserRepository = Depends(get_user_repo),
    db=Depends(get_db),
) -> ConsumerTokenResponse:
    """Exchange a Google ID token for a Hellum JWT access + refresh token pair.

    The frontend should call Google Sign-In (any platform SDK), obtain the
    ``id_token`` from the credential response, and POST it here. This endpoint
    verifies the token against our Google Client ID, enforces email_verified,
    and upserts the user in MongoDB.
    """
    if not settings.google_client_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="google_sso_not_configured",
        )

    idinfo = await _verify_google_id_token(body.id_token, settings.google_client_id)

    google_sub: str = idinfo["sub"]
    email: str = idinfo.get("email", "")
    display_name: str | None = idinfo.get("name")

    user_doc = await user_repo.upsert_by_google_sub(
        google_sub=google_sub,
        email=email,
        display_name=display_name,
    )

    user_id = str(user_doc["_id"])
    logger.info("consumer_google_sign_in user_id=%s email=%s", user_id, email)
    return await _mint_token_pair(user_id, db, settings)


# ---------------------------------------------------------------------------
# POST /api/v1/auth/refresh
# ---------------------------------------------------------------------------

@router.post("/auth/refresh", response_model=ConsumerTokenResponse)
async def refresh_token(
    refresh_token: str,
    settings: Settings = Depends(get_settings),
    db=Depends(get_db),
) -> ConsumerTokenResponse:
    """Rotate a refresh token and return a new token pair."""
    token_doc = await db.refresh_tokens.find_one({"token": refresh_token})
    if not token_doc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_refresh_token")

    if token_doc["expires_at"].replace(tzinfo=UTC) < datetime.now(UTC):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="refresh_token_expired")

    user_id = str(token_doc["user_id"])
    await db.refresh_tokens.delete_one({"token": refresh_token})
    return await _mint_token_pair(user_id, db, settings)


# ---------------------------------------------------------------------------
# GET /api/v1/me
# ---------------------------------------------------------------------------

@router.get("/me", response_model=UserResponse)
async def get_me(
    user_id: str = Depends(get_current_consumer_user),
    user_repo: UserRepository = Depends(get_user_repo),
) -> UserResponse:
    """Return the authenticated consumer's profile."""
    doc = await user_repo.get_by_id(user_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user_not_found")
    return UserResponse(
        id=str(doc["_id"]),
        google_sub=doc["google_sub"],
        email=doc["email"],
        display_name=doc.get("display_name"),
        created_at=doc["created_at"],
    )


# ---------------------------------------------------------------------------
# POST /api/v1/devices/binding-token
# ---------------------------------------------------------------------------

@router.post("/devices/binding-token", response_model=BindingTokenResponse)
async def request_binding_token(
    user_id: str = Depends(get_current_consumer_user),
    settings: Settings = Depends(get_settings),
    db=Depends(get_db),
) -> BindingTokenResponse:
    """Generate a one-time MQTT Binding Token for device provisioning.

    Flow:
      1. Consumer calls this endpoint (requires JWT) → gets ``binding_token``.
      2. Consumer app does BLE PoP handshake with ESP32, passes Wi-Fi creds
         + ``binding_token`` to the device.
      3. ESP32 connects to Wi-Fi, publishes to ``smarthome/register`` with its
         MAC + ``binding_token`` + ``device_model``.
      4. MQTT bridge validates the token, creates the device document in MongoDB,
         and permanently links it to this user.
    """
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(UTC) + timedelta(seconds=settings.binding_token_ttl_seconds)

    await db.binding_tokens.insert_one(
        {
            "token": token,
            "user_id": ObjectId(user_id),
            "expires_at": expires_at,
            "used": False,
        }
    )

    logger.info("binding_token_issued user_id=%s expires_in=%ds", user_id, settings.binding_token_ttl_seconds)
    return BindingTokenResponse(
        binding_token=token,
        expires_in=settings.binding_token_ttl_seconds,
    )


# ---------------------------------------------------------------------------
# GET /api/v1/devices
# ---------------------------------------------------------------------------

@router.get("/devices", response_model=list[SmartHomeDeviceResponse])
async def list_devices(
    user_id: str = Depends(get_current_consumer_user),
    device_repo: SmartHomeDeviceRepository = Depends(get_smarthome_device_repo),
) -> list[SmartHomeDeviceResponse]:
    """List all Smart Home devices provisioned by the authenticated consumer."""
    docs = await device_repo.get_devices_for_user(user_id)
    return [_doc_to_response(d) for d in docs]


# ---------------------------------------------------------------------------
# PATCH /api/v1/devices/{mac}
# ---------------------------------------------------------------------------

@router.patch("/devices/{mac}", response_model=SmartHomeDeviceResponse)
async def rename_device(
    mac: str,
    body: DeviceRenameRequest,
    user_id: str = Depends(get_current_consumer_user),
    device_repo: SmartHomeDeviceRepository = Depends(get_smarthome_device_repo),
) -> SmartHomeDeviceResponse:
    """Rename an owned device."""
    updated = await device_repo.rename_device(mac=mac.lower(), user_id=user_id, name=body.name)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="device_not_found")

    doc = await device_repo.get_by_mac(mac.lower())
    return _doc_to_response(doc)


# ---------------------------------------------------------------------------
# DELETE /api/v1/devices/{mac}
# ---------------------------------------------------------------------------

@router.delete("/devices/{mac}", status_code=status.HTTP_204_NO_CONTENT)
async def release_device(
    mac: str,
    user_id: str = Depends(get_current_consumer_user),
    device_repo: SmartHomeDeviceRepository = Depends(get_smarthome_device_repo),
) -> None:
    """Release ownership of a provisioned device (removes it from the user's account)."""
    deleted = await device_repo.delete_device(mac=mac.lower(), user_id=user_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="device_not_found")
    logger.info("consumer_device_released mac=%s user_id=%s", mac, user_id)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _doc_to_response(doc: dict) -> SmartHomeDeviceResponse:
    return SmartHomeDeviceResponse(
        id=str(doc["_id"]),
        mac=doc["mac"],
        user_id=str(doc["user_id"]),
        name=doc.get("name", doc["mac"]),
        device_model=doc.get("device_model", "unknown"),
        endpoints=[
            EndpointResponse(
                id=e["id"],
                name=e["name"],
                google_type=e["google_type"],
                state=bool(e.get("state", False)),
            )
            for e in doc.get("endpoints", [])
        ],
        created_at=doc["created_at"],
    )
