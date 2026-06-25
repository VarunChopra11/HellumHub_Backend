"""Repository for the Device Model catalog."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError

logger = logging.getLogger(__name__)


class DeviceModelRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.collection = db.device_models

    async def create(self, data: dict[str, Any]) -> dict[str, Any]:
        """Insert a new device model. Raises ValueError on duplicate model_id."""
        now = datetime.now(UTC)
        doc = {**data, "created_at": now, "updated_at": now}
        try:
            result = await self.collection.insert_one(doc)
        except DuplicateKeyError as exc:
            raise ValueError(
                f"Device model '{data.get('model_id')}' already exists."
            ) from exc
        doc["_id"] = result.inserted_id
        return doc

    async def get_by_model_id(self, model_id: str) -> dict[str, Any] | None:
        return await self.collection.find_one({"model_id": model_id})

    async def list_all(self) -> list[dict[str, Any]]:
        cursor = self.collection.find({})
        return await cursor.to_list(length=None)

    async def update(self, model_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
        """Apply a partial update to a device model. Returns the updated document."""
        updates["updated_at"] = datetime.now(UTC)
        doc = await self.collection.find_one_and_update(
            {"model_id": model_id},
            {"$set": updates},
            return_document=True,
        )
        return doc

    async def delete(self, model_id: str) -> bool:
        result = await self.collection.delete_one({"model_id": model_id})
        return result.deleted_count > 0
