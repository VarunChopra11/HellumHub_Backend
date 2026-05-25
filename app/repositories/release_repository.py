from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
import semver


class ReleaseRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.collection = db.releases

    async def create_release(self, payload: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now(UTC)
        doc = {
            **payload,
            "firmware_file_id": None,
            "sha256": None,
            "size": None,
            "mime": None,
            "filename": None,
            "created_at": now,
            "updated_at": now,
        }
        result = await self.collection.insert_one(doc)
        doc["_id"] = result.inserted_id
        return doc

    async def get_by_id(self, release_id: str) -> dict[str, Any] | None:
        return await self.collection.find_one({"_id": ObjectId(release_id)})

    async def get_by_device_version(self, device_type: str, version: str) -> dict[str, Any] | None:
        return await self.collection.find_one({"device_type": device_type, "version": version})

    async def list_by_device(self, device_type: str) -> list[dict[str, Any]]:
        cursor = self.collection.find({"device_type": device_type}).sort("created_at", -1)
        return [doc async for doc in cursor]

    async def get_active_latest(self, device_type: str) -> dict[str, Any] | None:
        cursor = self.collection.find({"device_type": device_type, "enabled": True})
        items = [doc async for doc in cursor]
        if not items:
            return None

        def sort_key(item: dict[str, Any]) -> semver.Version:
            raw = item.get("version", "0.0.0")
            try:
                return semver.Version.parse(raw)
            except ValueError:
                return semver.Version.parse("0.0.0")

        items.sort(key=sort_key, reverse=True)
        return items[0]

    async def patch_release(self, release_id: str, update_fields: dict[str, Any]) -> dict[str, Any] | None:
        update_fields["updated_at"] = datetime.now(UTC)
        await self.collection.update_one({"_id": ObjectId(release_id)}, {"$set": update_fields})
        return await self.get_by_id(release_id)
