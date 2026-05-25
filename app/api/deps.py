from fastapi import Depends, HTTPException, Request, status

from app.db.mongo import mongo_state
from app.repositories.audit_repository import AuditRepository
from app.repositories.device_repository import DeviceRepository
from app.repositories.firmware_repository import FirmwareRepository
from app.repositories.override_repository import OverrideRepository
from app.repositories.release_repository import ReleaseRepository
from app.services.admin_service import AdminService
from app.services.check_service import CheckService


async def get_db(request: Request):
    if mongo_state.db is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="database unavailable")
    return mongo_state.db


async def get_gridfs(request: Request):
    if mongo_state.gridfs is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="storage unavailable")
    return mongo_state.gridfs


async def get_device_repo(db=Depends(get_db)) -> DeviceRepository:
    return DeviceRepository(db)


async def get_release_repo(db=Depends(get_db)) -> ReleaseRepository:
    return ReleaseRepository(db)


async def get_override_repo(db=Depends(get_db)) -> OverrideRepository:
    return OverrideRepository(db)


async def get_audit_repo(db=Depends(get_db)) -> AuditRepository:
    return AuditRepository(db)


async def get_firmware_repo(
    request: Request, db=Depends(get_db), gridfs=Depends(get_gridfs)
) -> FirmwareRepository:
    bucket_name = request.app.state.settings.gridfs_bucket_name
    return FirmwareRepository(db, gridfs, bucket_name)


async def get_check_service(
    device_repo: DeviceRepository = Depends(get_device_repo),
    release_repo: ReleaseRepository = Depends(get_release_repo),
    override_repo: OverrideRepository = Depends(get_override_repo),
    audit_repo: AuditRepository = Depends(get_audit_repo),
) -> CheckService:
    return CheckService(
        device_repo=device_repo,
        release_repo=release_repo,
        override_repo=override_repo,
        audit_repo=audit_repo,
    )


async def get_admin_service(
    release_repo: ReleaseRepository = Depends(get_release_repo),
    firmware_repo: FirmwareRepository = Depends(get_firmware_repo),
    override_repo: OverrideRepository = Depends(get_override_repo),
) -> AdminService:
    return AdminService(
        release_repo=release_repo,
        firmware_repo=firmware_repo,
        override_repo=override_repo,
    )
