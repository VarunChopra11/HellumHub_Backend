import pytest


@pytest.mark.asyncio
async def test_admin_release_upload_enable_rollout_and_override(client):
    create = await client.post(
        "/admin/releases",
        json={
            "device_type": "smart_switch",
            "version": "2.0.0",
            "rollout_percentage": 100,
            "enabled": False,
            "notes": "major",
        },
        headers={"x-api-key": "test-key"},
    )
    assert create.status_code == 201
    release_id = create.json()["id"]

    upload = await client.post(
        f"/admin/releases/{release_id}/firmware",
        files={"file": ("switch-v2.0.0.bin", b"firmware-bytes", "application/octet-stream")},
        headers={"x-api-key": "test-key"},
    )
    assert upload.status_code == 200
    assert upload.json()["size"] == len(b"firmware-bytes")

    enabled = await client.patch(
        f"/admin/releases/{release_id}/enabled",
        json={"enabled": True},
        headers={"x-api-key": "test-key"},
    )
    assert enabled.status_code == 200
    assert enabled.json()["enabled"] is True

    rollout = await client.patch(
        f"/admin/releases/{release_id}/rollout",
        json={"rollout_percentage": 25},
        headers={"x-api-key": "test-key"},
    )
    assert rollout.status_code == 200
    assert rollout.json()["rollout_percentage"] == 25

    override = await client.put(
        "/admin/overrides/smart_switch/AA-BB-CC-DD-EE-FF",
        json={"version": "2.0.0", "reason": "pilot device"},
        headers={"x-api-key": "test-key"},
    )
    assert override.status_code == 200
    assert override.json()["mac"] == "AA:BB:CC:DD:EE:FF"
