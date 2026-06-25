"""
Admin endpoints for Smart Home device management.

Consumer user management (POST /admin/users) has been removed — consumers now
self-register via Google Sign-In at POST /api/v1/auth/google.

Remaining admin responsibility:
  - List and manage provisioned Smart Board devices
  - (Device model CRUD is in admin_roles.py and device_models.py)
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_smarthome_device_repo
from app.core.security import AdminPrincipal, admin_auth
from app.repositories.smarthome_device_repository import SmartHomeDeviceRepository
from app.schemas.smarthome import SmartHomeDeviceResponse, EndpointResponse

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin",
    tags=["admin_smarthome"],
    dependencies=[Depends(admin_auth)],
)


# ---------------------------------------------------------------------------
# Smart Home Device management
# ---------------------------------------------------------------------------

@router.get("/smarthome-devices", response_model=list[SmartHomeDeviceResponse])
async def list_smarthome_devices(
    principal: AdminPrincipal = Depends(admin_auth),
    device_repo: SmartHomeDeviceRepository = Depends(get_smarthome_device_repo),
) -> list[SmartHomeDeviceResponse]:
    """List all provisioned Smart Home devices across all users."""
    docs = await device_repo.list_all()
    return [_doc_to_response(d) for d in docs]


@router.delete(
    "/smarthome-devices/{mac}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def admin_delete_device(
    mac: str,
    principal: AdminPrincipal = Depends(admin_auth),
    device_repo: SmartHomeDeviceRepository = Depends(get_smarthome_device_repo),
) -> None:
    """Force-delete a provisioned device (admin override, bypasses ownership check)."""
    doc = await device_repo.get_by_mac(mac.lower())
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="device_not_found")
    # Admin bypass — delete without user_id check
    await device_repo.collection.delete_one({"mac": mac.lower()})
    logger.info("admin_device_deleted mac=%s by=%s", mac, principal.subject)


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
