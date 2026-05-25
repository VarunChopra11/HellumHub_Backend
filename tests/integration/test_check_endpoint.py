import pytest


@pytest.mark.asyncio
async def test_smart_switch_check_update_and_no_update(client, test_state) -> None:
    release = await test_state.release_repo.create_release(
        {
            "device_type": "smart_switch",
            "version": "1.2.0",
            "rollout_percentage": 100,
            "enabled": True,
            "notes": "stable",
        }
    )
    await test_state.release_repo.patch_release(
        release["_id"],
        {
            "firmware_file_id": "fw-file-1",
            "sha256": "deadbeef",
            "size": 4096,
            "mime": "application/octet-stream",
            "filename": "switch-v1.2.0.bin",
        },
    )

    resp = await client.get("/smart_switch/check", params={"mac": "aabbccddeeff", "ver": "1.0.0"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["update_available"] is True
    assert data["version"] == "1.2.0"
    assert "/firmware/smart_switch/1.2.0/download" in data["firmware_url"]
    assert resp.headers.get("Cache-Control") == "no-store"

    no_update = await client.get(
        "/smart_switch/check", params={"mac": "AA:BB:CC:DD:EE:FF", "ver": "1.2.0"}
    )
    assert no_update.status_code == 200
    assert no_update.json() == {"update_available": False}
