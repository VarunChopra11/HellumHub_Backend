from collections.abc import AsyncIterator
from urllib.parse import urljoin

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import StreamingResponse

from app.api.deps import get_check_service, get_firmware_repo, get_release_repo
from app.repositories.firmware_repository import FirmwareRepository
from app.repositories.release_repository import ReleaseRepository
from app.schemas.check import FirmwareCheckResponse
from app.services.check_service import CheckService
from app.services.url_signer import UrlSigner
from app.utils.mac import normalize_mac

router = APIRouter(prefix="/smart_switch", tags=["smart_switch"])


def _build_firmware_url(request: Request, device_type: str, version: str) -> str:
    settings = request.app.state.settings
    path = f"/firmware/{device_type}/{version}/download"
    signer = UrlSigner(settings.signed_url_secret, settings.signed_url_ttl_seconds)
    query = signer.sign(path)
    base = settings.public_base_url.rstrip("/")
    full = urljoin(f"{base}/", path.lstrip("/"))
    return f"{full}?{query}" if query else full


def _client_ip(request: Request) -> str | None:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


@router.get("/check", response_model=FirmwareCheckResponse, response_model_exclude_none=True)
async def check_smart_switch(
    request: Request,
    response: Response,
    mac: str = Query(...),
    ver: str = Query(...),
    service: CheckService = Depends(get_check_service),
) -> FirmwareCheckResponse:
    response.headers["Cache-Control"] = "no-store"

    try:
        normalized_mac = normalize_mac(mac)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
            headers={"Cache-Control": "no-store"},
        ) from exc

    request_id = request.headers.get("x-request-id")
    try:
        return await service.evaluate(
            device_type="smart_switch",
            mac=normalized_mac,
            current_version=ver,
            request_id=request_id,
            last_ip=_client_ip(request),
            firmware_url_builder=lambda device_type, version: _build_firmware_url(
                request, device_type, version
            ),
        )
    except Exception:
        return await service.fallback_on_error(
            device_type="smart_switch",
            mac=normalized_mac,
            current_version=ver,
            request_id=request_id,
        )


async def _chunk_file(grid_out) -> AsyncIterator[bytes]:
    while True:
        chunk = await grid_out.readchunk()
        if not chunk:
            break
        yield chunk

firmware_router = APIRouter(prefix="/firmware", tags=["firmware"])


@firmware_router.get("/{device_type}/{version}/download")
async def download_firmware(
    request: Request,
    device_type: str,
    version: str,
    exp: int | None = None,
    sig: str | None = None,
    release_repo: ReleaseRepository = Depends(get_release_repo),
    firmware_repo: FirmwareRepository = Depends(get_firmware_repo),
):
    settings = request.app.state.settings
    path = request.url.path
    signer = UrlSigner(settings.signed_url_secret, settings.signed_url_ttl_seconds)

    if settings.signed_url_secret:
        if exp is None or sig is None or not signer.verify(path, exp, sig):
            raise HTTPException(status_code=403, detail="invalid_or_expired_signature")

    release = await release_repo.get_by_device_version(device_type, version)
    if not release or not release.get("firmware_file_id"):
        raise HTTPException(status_code=404, detail="firmware_not_found")

    grid_out = await firmware_repo.get_grid_out(release["firmware_file_id"])
    headers = {
        "Content-Disposition": f"attachment; filename={release.get('filename') or f'{device_type}_{version}.bin'}"
    }
    return StreamingResponse(
        _chunk_file(grid_out),
        media_type=release.get("mime") or "application/octet-stream",
        headers=headers,
    )
