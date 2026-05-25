import logging
from datetime import UTC, datetime
from typing import Any

from app.repositories.audit_repository import AuditRepository
from app.repositories.device_repository import DeviceRepository
from app.repositories.override_repository import OverrideRepository
from app.repositories.release_repository import ReleaseRepository
from app.schemas.check import FirmwareCheckResponse
from app.utils.rollout import in_rollout
from app.utils.semver_utils import is_greater, parse_version

logger = logging.getLogger(__name__)


class CheckService:
    def __init__(
        self,
        *,
        device_repo: DeviceRepository,
        release_repo: ReleaseRepository,
        override_repo: OverrideRepository,
        audit_repo: AuditRepository,
    ) -> None:
        self.device_repo = device_repo
        self.release_repo = release_repo
        self.override_repo = override_repo
        self.audit_repo = audit_repo

    async def evaluate(
        self,
        *,
        device_type: str,
        mac: str,
        current_version: str,
        request_id: str | None,
        last_ip: str | None,
        firmware_url_builder,
    ) -> FirmwareCheckResponse:
        try:
            parse_version(current_version)
        except ValueError:
            return await self._finalize(
                device_type=device_type,
                mac=mac,
                current_version=current_version,
                result="invalid_version",
                request_id=request_id,
                response=FirmwareCheckResponse(update_available=False),
                message="invalid_semver",
            )

        device = await self.device_repo.upsert_last_seen(
            mac=mac,
            device_type=device_type,
            current_version=current_version,
            last_ip=last_ip,
        )

        if bool(device.get("blocked", False)):
            return await self._finalize(
                device_type=device_type,
                mac=mac,
                current_version=current_version,
                result="blocked",
                request_id=request_id,
                response=FirmwareCheckResponse(update_available=False),
            )

        override = await self.override_repo.get_override(device_type, mac)
        if override:
            pinned = str(override["version"])
            try:
                parse_version(pinned)
                if is_greater(pinned, current_version):
                    release = await self.release_repo.get_by_device_version(device_type, pinned)
                    if release and release.get("firmware_file_id"):
                        response = FirmwareCheckResponse(
                            update_available=True,
                            version=pinned,
                            firmware_url=firmware_url_builder(device_type, pinned),
                            sha256=release.get("sha256"),
                            size=release.get("size"),
                        )
                        return await self._finalize(
                            device_type=device_type,
                            mac=mac,
                            current_version=current_version,
                            result="update_available",
                            chosen_version=pinned,
                            chosen_release_id=str(release["_id"]),
                            request_id=request_id,
                            response=response,
                            message="override",
                        )
            except ValueError:
                return await self._finalize(
                    device_type=device_type,
                    mac=mac,
                    current_version=current_version,
                    result="override_invalid",
                    request_id=request_id,
                    response=FirmwareCheckResponse(update_available=False),
                )

        release = await self.release_repo.get_active_latest(device_type)
        if not release:
            return await self._finalize(
                device_type=device_type,
                mac=mac,
                current_version=current_version,
                result="no_active_release",
                request_id=request_id,
                response=FirmwareCheckResponse(update_available=False),
            )

        target_version = str(release["version"])
        if not is_greater(target_version, current_version):
            return await self._finalize(
                device_type=device_type,
                mac=mac,
                current_version=current_version,
                result="version_not_greater",
                request_id=request_id,
                response=FirmwareCheckResponse(update_available=False),
            )

        rollout_percentage = int(release.get("rollout_percentage", 100))
        if not in_rollout(mac, rollout_percentage):
            return await self._finalize(
                device_type=device_type,
                mac=mac,
                current_version=current_version,
                result="rollout_not_included",
                request_id=request_id,
                response=FirmwareCheckResponse(update_available=False),
            )

        response = FirmwareCheckResponse(
            update_available=True,
            version=target_version,
            firmware_url=firmware_url_builder(device_type, target_version),
            sha256=release.get("sha256"),
            size=release.get("size"),
        )
        return await self._finalize(
            device_type=device_type,
            mac=mac,
            current_version=current_version,
            result="update_available",
            chosen_version=target_version,
            chosen_release_id=str(release["_id"]),
            request_id=request_id,
            response=response,
        )

    async def fallback_on_error(
        self,
        *,
        device_type: str,
        mac: str,
        current_version: str,
        request_id: str | None,
    ) -> FirmwareCheckResponse:
        logger.exception("check_path_error device_type=%s mac=%s", device_type, mac)
        return await self._finalize(
            device_type=device_type,
            mac=mac,
            current_version=current_version,
            result="error_fallback",
            request_id=request_id,
            response=FirmwareCheckResponse(update_available=False),
            message="internal_error",
        )

    async def _finalize(
        self,
        *,
        device_type: str,
        mac: str,
        current_version: str,
        result: str,
        request_id: str | None,
        response: FirmwareCheckResponse,
        chosen_version: str | None = None,
        chosen_release_id: str | None = None,
        message: str | None = None,
    ) -> FirmwareCheckResponse:
        await self.device_repo.update_last_check_result(mac=mac, result=result)
        await self.audit_repo.log_check(
            {
                "device_type": device_type,
                "mac": mac,
                "current_version": current_version,
                "checked_at": datetime.now(UTC),
                "result": result,
                "chosen_version": chosen_version,
                "chosen_release_id": chosen_release_id,
                "message": message,
                "request_id": request_id,
                "response": response.model_dump(),
            }
        )
        return response
