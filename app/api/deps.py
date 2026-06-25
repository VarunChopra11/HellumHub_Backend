import time
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

import jwt

from app.core.config import Settings, get_settings
from app.db.mongo import mongo_state
from app.repositories.admin_user_repository import AdminUserRepository
from app.repositories.audit_repository import AuditRepository
from app.repositories.device_model_repository import DeviceModelRepository
from app.repositories.device_repository import DeviceRepository
from app.repositories.firmware_repository import FirmwareRepository
from app.repositories.override_repository import OverrideRepository
from app.repositories.release_repository import ReleaseRepository
from app.repositories.smarthome_device_repository import SmartHomeDeviceRepository
from app.repositories.user_repository import UserRepository
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


# ---------------------------------------------------------------------------
# OTA repositories & services (unchanged)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Smart Home repositories
# ---------------------------------------------------------------------------

async def get_user_repo(db=Depends(get_db)) -> UserRepository:
    return UserRepository(db)


async def get_smarthome_device_repo(db=Depends(get_db)) -> SmartHomeDeviceRepository:
    return SmartHomeDeviceRepository(db)


async def get_device_model_repo(db=Depends(get_db)) -> DeviceModelRepository:
    return DeviceModelRepository(db)


async def get_admin_user_repo(db=Depends(get_db)) -> AdminUserRepository:
    return AdminUserRepository(db)


# ---------------------------------------------------------------------------
# Consumer JWT authentication dependency
# ---------------------------------------------------------------------------

_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_consumer_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
    settings: Settings = Depends(get_settings),
) -> str:
    """Validate a Hellum consumer Bearer JWT and return the user's ObjectId string."""
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing_bearer_token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not settings.consumer_jwt_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="consumer_jwt_not_configured",
        )

    token = credentials.credentials
    try:
        claims = jwt.decode(
            token,
            settings.consumer_jwt_secret,
            algorithms=[settings.consumer_jwt_algorithm],
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="token_expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    exp = claims.get("exp")
    if exp is not None and float(exp) < time.time():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="token_expired",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id: str = str(claims.get("sub", ""))
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_token_subject",
        )
    return user_id
