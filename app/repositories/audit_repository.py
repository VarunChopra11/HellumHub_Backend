from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase


class AuditRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.collection = db.audit_checks

    async def log_check(self, payload: dict[str, Any]) -> None:
        await self.collection.insert_one(payload)
