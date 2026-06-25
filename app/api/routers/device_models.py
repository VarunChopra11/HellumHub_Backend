"""
Device Model Catalog admin endpoints.

Admins can define any hardware model here. When a consumer provisions a device
via the MQTT Binding Token flow, the backend copies the endpoint definitions
from the matching model in this catalog into the smarthome_devices document.

No models are pre-seeded — the catalog starts empty and grows as new hardware
is introduced.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_device_model_repo
from app.core.security import AdminPrincipal, admin_auth
from app.repositories.device_model_repository import DeviceModelRepository
from app.schemas.smarthome import (
    DeviceModelCreate,
    DeviceModelResponse,
    DeviceModelUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin/device-models",
    tags=["admin_device_models"],
    dependencies=[Depends(admin_auth)],
)


def _to_response(doc: dict) -> DeviceModelResponse:
    return DeviceModelResponse(
        id=str(doc["_id"]),
        model_id=doc["model_id"],
        display_name=doc["display_name"],
        manufacturer=doc.get("manufacturer", ""),
        hw_version=doc.get("hw_version", "1.0"),
        endpoints=doc.get("endpoints", []),
        created_at=doc["created_at"],
    )


@router.get("", response_model=list[DeviceModelResponse])
async def list_device_models(
    principal: AdminPrincipal = Depends(admin_auth),
    repo: DeviceModelRepository = Depends(get_device_model_repo),
) -> list[DeviceModelResponse]:
    """List all device models in the catalog."""
    docs = await repo.list_all()
    return [_to_response(d) for d in docs]


@router.post("", response_model=DeviceModelResponse, status_code=status.HTTP_201_CREATED)
async def create_device_model(
    payload: DeviceModelCreate,
    principal: AdminPrincipal = Depends(admin_auth),
    repo: DeviceModelRepository = Depends(get_device_model_repo),
) -> DeviceModelResponse:
    """Register a new device model in the catalog."""
    try:
        doc = await repo.create(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    logger.info(
        "device_model_created model_id=%s endpoints=%d by=%s",
        payload.model_id, len(payload.endpoints), principal.subject,
    )
    return _to_response(doc)


@router.get("/{model_id}", response_model=DeviceModelResponse)
async def get_device_model(
    model_id: str,
    principal: AdminPrincipal = Depends(admin_auth),
    repo: DeviceModelRepository = Depends(get_device_model_repo),
) -> DeviceModelResponse:
    """Get a specific device model by its model_id slug."""
    doc = await repo.get_by_model_id(model_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="device_model_not_found")
    return _to_response(doc)


@router.patch("/{model_id}", response_model=DeviceModelResponse)
async def update_device_model(
    model_id: str,
    payload: DeviceModelUpdate,
    principal: AdminPrincipal = Depends(admin_auth),
    repo: DeviceModelRepository = Depends(get_device_model_repo),
) -> DeviceModelResponse:
    """Partially update a device model (display name, endpoints, etc.)."""
    updates = payload.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="no_fields_to_update")

    doc = await repo.update(model_id, updates)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="device_model_not_found")

    logger.info("device_model_updated model_id=%s by=%s", model_id, principal.subject)
    return _to_response(doc)


@router.delete("/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_device_model(
    model_id: str,
    principal: AdminPrincipal = Depends(admin_auth),
    repo: DeviceModelRepository = Depends(get_device_model_repo),
) -> None:
    """Delete a device model from the catalog.

    Note: Existing provisioned devices that reference this model_id retain their
    endpoint list (it is copied at provisioning time), so deletion is safe.
    """
    deleted = await repo.delete(model_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="device_model_not_found")
    logger.info("device_model_deleted model_id=%s by=%s", model_id, principal.subject)
