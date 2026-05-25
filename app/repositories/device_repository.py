from datetime import UTC, datetime
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase


class DeviceRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.collection = db.devices

    async def upsert_last_seen(
        self,
        *,
        mac: str,
        device_type: str,
        current_version: str,
        last_ip: str | None,
    ) -> dict[str, Any]:
        now = datetime.now(UTC)
        await self.collection.update_one(
            {"mac": mac},
            {
                "$set": {
                    "device_type": device_type,
                    "current_version": current_version,
                    "last_seen_at": now,
                    "last_ip": last_ip,
                },
                "$setOnInsert": {
                    "rollout_group": None,
                    "blocked": False,
                    "created_at": now,
                },
            },
            upsert=True,
        )
        device = await self.collection.find_one({"mac": mac})
        return device or {}

    async def update_last_check_result(self, mac: str, result: str) -> None:
        await self.collection.update_one(
            {"mac": mac},
            {"$set": {"last_check_result": result, "updated_at": datetime.now(UTC)}},
        )
