import pytest

from app.services.check_service import CheckService
from tests.fakes import FakeState


@pytest.mark.asyncio
async def test_blocked_device_returns_no_update() -> None:
    state = FakeState()
    state.device_repo.devices["AA:BB:CC:DD:EE:FF"] = {
        "mac": "AA:BB:CC:DD:EE:FF",
        "blocked": True,
    }
    service = CheckService(
        device_repo=state.device_repo,
        release_repo=state.release_repo,
        override_repo=state.override_repo,
        audit_repo=state.audit_repo,
    )

    response = await service.evaluate(
        device_type="smart_switch",
        mac="AA:BB:CC:DD:EE:FF",
        current_version="1.0.0",
        request_id="t1",
        last_ip="127.0.0.1",
        firmware_url_builder=lambda *_: "http://x",
    )

    assert response.update_available is False


@pytest.mark.asyncio
async def test_override_takes_precedence() -> None:
    state = FakeState()
    release = await state.release_repo.create_release(
        {
            "device_type": "smart_switch",
            "version": "1.2.0",
            "rollout_percentage": 100,
            "enabled": True,
            "notes": None,
        }
    )
    await state.release_repo.patch_release(
        release["_id"],
        {
            "firmware_file_id": "file123",
            "sha256": "abc",
            "size": 123,
        },
    )
    await state.override_repo.upsert_override(
        device_type="smart_switch",
        mac="AA:BB:CC:DD:EE:FF",
        version="1.2.0",
        reason="hotfix",
    )

    service = CheckService(
        device_repo=state.device_repo,
        release_repo=state.release_repo,
        override_repo=state.override_repo,
        audit_repo=state.audit_repo,
    )

    response = await service.evaluate(
        device_type="smart_switch",
        mac="AA:BB:CC:DD:EE:FF",
        current_version="1.0.0",
        request_id="t2",
        last_ip="127.0.0.1",
        firmware_url_builder=lambda *_: "http://fw",
    )

    assert response.update_available is True
    assert response.version == "1.2.0"


@pytest.mark.asyncio
async def test_rollout_excluded_returns_no_update() -> None:
    state = FakeState()
    await state.release_repo.create_release(
        {
            "device_type": "smart_switch",
            "version": "1.3.0",
            "rollout_percentage": 0,
            "enabled": True,
            "notes": None,
        }
    )

    service = CheckService(
        device_repo=state.device_repo,
        release_repo=state.release_repo,
        override_repo=state.override_repo,
        audit_repo=state.audit_repo,
    )

    response = await service.evaluate(
        device_type="smart_switch",
        mac="AA:BB:CC:DD:EE:FF",
        current_version="1.0.0",
        request_id="t3",
        last_ip="127.0.0.1",
        firmware_url_builder=lambda *_: "http://fw",
    )

    assert response.update_available is False
    assert state.audit_repo.entries[-1]["result"] == "rollout_not_included"
