import os

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("MONGO_URI", "mongodb://localhost:27017")
os.environ.setdefault("SIGNED_URL_SECRET", "test-signing-secret")
os.environ.setdefault("PUBLIC_BASE_URL", "http://testserver")

from app.api import deps
from app.core.security import AdminPrincipal, admin_auth
from app.main import create_app
from app.services.admin_service import AdminService
from app.services.check_service import CheckService
from tests.fakes import FakeState


@pytest.fixture()
def test_state() -> FakeState:
    return FakeState()


@pytest.fixture()
def app(test_state: FakeState):
    application = create_app(enable_lifespan=False)

    async def _admin_principal() -> AdminPrincipal:
        return AdminPrincipal(subject="test-admin")

    async def _check_service() -> CheckService:
        return CheckService(
            device_repo=test_state.device_repo,
            release_repo=test_state.release_repo,
            override_repo=test_state.override_repo,
            audit_repo=test_state.audit_repo,
        )

    async def _admin_service() -> AdminService:
        return AdminService(
            release_repo=test_state.release_repo,
            firmware_repo=test_state.firmware_repo,
            override_repo=test_state.override_repo,
        )

    from app.core.config import get_settings

    application.state.settings = get_settings()

    application.dependency_overrides[admin_auth] = _admin_principal
    application.dependency_overrides[deps.get_check_service] = _check_service
    application.dependency_overrides[deps.get_admin_service] = _admin_service
    async def _release_repo():
        return test_state.release_repo

    async def _override_repo():
        return test_state.override_repo

    async def _firmware_repo():
        return test_state.firmware_repo

    application.dependency_overrides[deps.get_release_repo] = _release_repo
    application.dependency_overrides[deps.get_override_repo] = _override_repo
    application.dependency_overrides[deps.get_firmware_repo] = _firmware_repo
    return application


@pytest.fixture()
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c
