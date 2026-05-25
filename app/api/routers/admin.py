from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.api.deps import get_admin_service, get_release_repo, get_override_repo
from app.core.security import AdminPrincipal, admin_auth
from app.schemas.admin import (
    AdminMessageResponse,
    CreateReleaseRequest,
    FirmwareUploadResponse,
    OverrideResponse,
    OverrideUpsertRequest,
    ReleaseListResponse,
    ReleaseResponse,
    RolloutUpdateRequest,
    ToggleReleaseRequest,
)
from app.services.admin_service import AdminService
from app.utils.mac import normalize_mac

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(admin_auth)])


def _release_to_response(doc: dict) -> ReleaseResponse:
    return ReleaseResponse(
        id=str(doc["_id"]),
        device_type=doc["device_type"],
        version=doc["version"],
        rollout_percentage=int(doc.get("rollout_percentage", 100)),
        enabled=bool(doc.get("enabled", False)),
        notes=doc.get("notes"),
        firmware_file_id=doc.get("firmware_file_id"),
        sha256=doc.get("sha256"),
        size=doc.get("size"),
        created_at=doc.get("created_at", datetime.now(UTC)),
        updated_at=doc.get("updated_at", datetime.now(UTC)),
    )


@router.post("/releases", response_model=ReleaseResponse, status_code=status.HTTP_201_CREATED)
async def create_release(
    payload: CreateReleaseRequest,
    principal: AdminPrincipal = Depends(admin_auth),
    service: AdminService = Depends(get_admin_service),
):
    _ = principal
    try:
        doc = await service.create_release(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _release_to_response(doc)


@router.get("/releases/{device_type}", response_model=ReleaseListResponse)
async def list_releases(
    device_type: str,
    principal: AdminPrincipal = Depends(admin_auth),
    release_repo=Depends(get_release_repo),
):
    _ = principal
    docs = await release_repo.list_by_device(device_type)
    return ReleaseListResponse(releases=[_release_to_response(d) for d in docs])


@router.post("/releases/{release_id}/firmware", response_model=FirmwareUploadResponse)
async def upload_release_firmware(
    release_id: str,
    file: UploadFile = File(...),
    principal: AdminPrincipal = Depends(admin_auth),
    service: AdminService = Depends(get_admin_service),
):
    _ = principal
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="empty_file")
    if not file.filename or not file.filename.endswith(".bin"):
        raise HTTPException(status_code=400, detail="firmware_must_be_bin")

    try:
        uploaded = await service.upload_firmware_for_release(
            release_id=release_id,
            content=content,
            filename=file.filename,
            mime=file.content_type or "application/octet-stream",
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return FirmwareUploadResponse(**uploaded)


@router.patch("/releases/{release_id}/enabled", response_model=ReleaseResponse)
async def set_release_enabled(
    release_id: str,
    payload: ToggleReleaseRequest,
    principal: AdminPrincipal = Depends(admin_auth),
    service: AdminService = Depends(get_admin_service),
):
    _ = principal
    try:
        doc = await service.set_release_enabled(release_id, payload.enabled)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _release_to_response(doc)


@router.patch("/releases/{release_id}/rollout", response_model=ReleaseResponse)
async def set_release_rollout(
    release_id: str,
    payload: RolloutUpdateRequest,
    principal: AdminPrincipal = Depends(admin_auth),
    service: AdminService = Depends(get_admin_service),
):
    _ = principal
    try:
        doc = await service.set_rollout_percentage(release_id, payload.rollout_percentage)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _release_to_response(doc)


@router.put("/overrides/{device_type}/{mac}", response_model=OverrideResponse)
async def upsert_override(
    device_type: str,
    mac: str,
    payload: OverrideUpsertRequest,
    principal: AdminPrincipal = Depends(admin_auth),
    override_repo=Depends(get_override_repo),
):
    _ = principal
    try:
        normalized = normalize_mac(mac)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    doc = await override_repo.upsert_override(
        device_type=device_type,
        mac=normalized,
        version=payload.version,
        reason=payload.reason,
    )
    return OverrideResponse(
        id=str(doc["_id"]),
        device_type=doc["device_type"],
        mac=doc["mac"],
        version=doc["version"],
        reason=doc.get("reason"),
        updated_at=doc["updated_at"],
    )


@router.delete("/overrides/{device_type}/{mac}", response_model=AdminMessageResponse)
async def delete_override(
    device_type: str,
    mac: str,
    principal: AdminPrincipal = Depends(admin_auth),
    override_repo=Depends(get_override_repo),
):
    _ = principal
    try:
        normalized = normalize_mac(mac)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    deleted = await override_repo.delete_override(device_type, normalized)
    if not deleted:
        raise HTTPException(status_code=404, detail="override_not_found")
    return AdminMessageResponse(message="override_deleted")
