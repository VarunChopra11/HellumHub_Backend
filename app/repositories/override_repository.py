from datetime import UTC, datetime
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase


class OverrideRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.collection = db.device_overrides

    async def get_override(self, device_type: str, mac: str) -> dict[str, Any] | None:
        return await self.collection.find_one({"device_type": device_type, "mac": mac})

    async def upsert_override(
        self,
        *,
        device_type: str,
        mac: str,
        version: str,
        reason: str | None,
    ) -> dict[str, Any]:
        now = datetime.now(UTC)
        await self.collection.update_one(
            {"device_type": device_type, "mac": mac},
            {
                "$set": {
                    "version": version,
                    "reason": reason,
                    "updated_at": now,
                },
                "$setOnInsert": {
                    "created_at": now,
                },
            },
            upsert=True,
        )
        doc = await self.collection.find_one({"device_type": device_type, "mac": mac})
        return doc or {}

    async def delete_override(self, device_type: str, mac: str) -> int:
        result = await self.collection.delete_one({"device_type": device_type, "mac": mac})
        return result.deleted_count
