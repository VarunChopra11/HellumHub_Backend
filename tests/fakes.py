from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import semver


class InMemoryDeviceRepo:
    def __init__(self) -> None:
        self.devices: dict[str, dict[str, Any]] = {}

    async def upsert_last_seen(
        self,
        *,
        mac: str,
        device_type: str,
        current_version: str,
        last_ip: str | None,
    ) -> dict[str, Any]:
        now = datetime.now(UTC)
        doc = self.devices.get(mac) or {
            "mac": mac,
            "blocked": False,
            "rollout_group": None,
            "created_at": now,
        }
        doc.update(
            {
                "device_type": device_type,
                "current_version": current_version,
                "last_seen_at": now,
                "last_ip": last_ip,
            }
        )
        self.devices[mac] = doc
        return doc

    async def update_last_check_result(self, mac: str, result: str) -> None:
        if mac in self.devices:
            self.devices[mac]["last_check_result"] = result


class InMemoryReleaseRepo:
    def __init__(self) -> None:
        self.releases: dict[str, dict[str, Any]] = {}

    async def create_release(self, payload: dict[str, Any]) -> dict[str, Any]:
        for existing in self.releases.values():
            if (
                existing["device_type"] == payload["device_type"]
                and existing["version"] == payload["version"]
            ):
                raise ValueError("duplicate")

        now = datetime.now(UTC)
        _id = str(uuid4())
        doc = {
            "_id": _id,
            **payload,
            "firmware_file_id": None,
            "sha256": None,
            "size": None,
            "mime": None,
            "filename": None,
            "created_at": now,
            "updated_at": now,
        }
        self.releases[_id] = doc
        return doc

    async def get_by_id(self, release_id: str) -> dict[str, Any] | None:
        return self.releases.get(release_id)

    async def get_by_device_version(self, device_type: str, version: str) -> dict[str, Any] | None:
        for release in self.releases.values():
            if release["device_type"] == device_type and release["version"] == version:
                return release
        return None

    async def list_by_device(self, device_type: str) -> list[dict[str, Any]]:
        return [r for r in self.releases.values() if r["device_type"] == device_type]

    async def get_active_latest(self, device_type: str) -> dict[str, Any] | None:
        candidates = [
            r
            for r in self.releases.values()
            if r["device_type"] == device_type and r.get("enabled")
        ]
        if not candidates:
            return None
        return sorted(candidates, key=lambda r: semver.Version.parse(r["version"]), reverse=True)[0]

    async def patch_release(self, release_id: str, update_fields: dict[str, Any]) -> dict[str, Any] | None:
        doc = self.releases.get(release_id)
        if not doc:
            return None
        doc.update(update_fields)
        doc["updated_at"] = datetime.now(UTC)
        return doc


class InMemoryOverrideRepo:
    def __init__(self) -> None:
        self.overrides: dict[tuple[str, str], dict[str, Any]] = {}

    async def get_override(self, device_type: str, mac: str) -> dict[str, Any] | None:
        return self.overrides.get((device_type, mac))

    async def upsert_override(
        self,
        *,
        device_type: str,
        mac: str,
        version: str,
        reason: str | None,
    ) -> dict[str, Any]:
        key = (device_type, mac)
        now = datetime.now(UTC)
        doc = self.overrides.get(key) or {
            "_id": str(uuid4()),
            "device_type": device_type,
            "mac": mac,
            "created_at": now,
        }
        doc.update({"version": version, "reason": reason, "updated_at": now})
        self.overrides[key] = doc
        return doc

    async def delete_override(self, device_type: str, mac: str) -> int:
        key = (device_type, mac)
        if key not in self.overrides:
            return 0
        del self.overrides[key]
        return 1


class InMemoryAuditRepo:
    def __init__(self) -> None:
        self.entries: list[dict[str, Any]] = []

    async def log_check(self, payload: dict[str, Any]) -> None:
        self.entries.append(payload)


class FakeGridOut:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload
        self._offset = 0
        self.chunk_size = 1024

    async def readchunk(self) -> bytes:
        if self._offset >= len(self.payload):
            return b""
        nxt = self.payload[self._offset : self._offset + self.chunk_size]
        self._offset += len(nxt)
        return nxt


class InMemoryFirmwareRepo:
    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}

    async def upload_binary(
        self,
        *,
        content: bytes,
        filename: str,
        mime: str,
        device_type: str,
        version: str,
    ) -> dict[str, Any]:
        file_id = str(uuid4())
        self.files[file_id] = content
        return {
            "file_id": file_id,
            "sha256": hashlib.sha256(content).hexdigest(),
            "size": len(content),
            "mime": mime,
            "filename": filename,
            "uploaded_at": datetime.now(UTC),
        }

    async def get_grid_out(self, file_id: str):
        data = self.files.get(file_id)
        if data is None:
            raise LookupError("file_not_found")
        return FakeGridOut(data)


class FakeState:
    def __init__(self) -> None:
        self.device_repo = InMemoryDeviceRepo()
        self.release_repo = InMemoryReleaseRepo()
        self.override_repo = InMemoryOverrideRepo()
        self.audit_repo = InMemoryAuditRepo()
        self.firmware_repo = InMemoryFirmwareRepo()
