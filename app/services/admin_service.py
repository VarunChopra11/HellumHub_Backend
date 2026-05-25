from bson.errors import InvalidId
from pymongo.errors import DuplicateKeyError

from app.repositories.firmware_repository import FirmwareRepository
from app.repositories.override_repository import OverrideRepository
from app.repositories.release_repository import ReleaseRepository


class AdminService:
    def __init__(
        self,
        *,
        release_repo: ReleaseRepository,
        firmware_repo: FirmwareRepository,
        override_repo: OverrideRepository,
    ) -> None:
        self.release_repo = release_repo
        self.firmware_repo = firmware_repo
        self.override_repo = override_repo

    async def create_release(self, payload: dict):
        try:
            return await self.release_repo.create_release(payload)
        except DuplicateKeyError as exc:
            raise ValueError("release_version_already_exists") from exc

    async def upload_firmware_for_release(
        self,
        *,
        release_id: str,
        content: bytes,
        filename: str,
        mime: str,
    ):
        try:
            release = await self.release_repo.get_by_id(release_id)
        except InvalidId as exc:
            raise LookupError("release_not_found") from exc
        if not release:
            raise LookupError("release_not_found")

        uploaded = await self.firmware_repo.upload_binary(
            content=content,
            filename=filename,
            mime=mime,
            device_type=release["device_type"],
            version=release["version"],
        )

        await self.release_repo.patch_release(
            release_id,
            {
                "firmware_file_id": uploaded["file_id"],
                "sha256": uploaded["sha256"],
                "size": uploaded["size"],
                "mime": uploaded["mime"],
                "filename": uploaded["filename"],
            },
        )
        return uploaded

    async def set_release_enabled(self, release_id: str, enabled: bool):
        try:
            release = await self.release_repo.patch_release(release_id, {"enabled": enabled})
        except InvalidId as exc:
            raise LookupError("release_not_found") from exc
        if not release:
            raise LookupError("release_not_found")
        return release

    async def set_rollout_percentage(self, release_id: str, rollout_percentage: int):
        try:
            release = await self.release_repo.patch_release(
                release_id, {"rollout_percentage": rollout_percentage}
            )
        except InvalidId as exc:
            raise LookupError("release_not_found") from exc
        if not release:
            raise LookupError("release_not_found")
        return release
