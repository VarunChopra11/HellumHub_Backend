"""Repository for consumer user accounts (Google SSO only)."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError

logger = logging.getLogger(__name__)


class UserRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.collection = db.users

    async def upsert_by_google_sub(
        self,
        *,
        google_sub: str,
        email: str,
        display_name: str | None = None,
    ) -> dict[str, Any]:
        """Insert or update a consumer user identified by their Google Subject ID.

        This is the primary write path — called on every successful Google Sign-In.
        If the user already exists, their email and display_name are refreshed
        (Google may update these over time).

        Returns the full user document after upsert.
        """
        now = datetime.now(UTC)
        result = await self.collection.find_one_and_update(
            {"google_sub": google_sub},
            {
                "$set": {
                    "email": email.lower().strip(),
                    "display_name": display_name,
                    "updated_at": now,
                },
                "$setOnInsert": {
                    "google_sub": google_sub,
                    "created_at": now,
                },
            },
            upsert=True,
            return_document=True,  # pymongo ReturnDocument.AFTER equivalent
        )
        return result

    async def get_by_google_sub(self, google_sub: str) -> dict[str, Any] | None:
        return await self.collection.find_one({"google_sub": google_sub})

    async def get_by_id(self, user_id: str) -> dict[str, Any] | None:
        try:
            oid = ObjectId(user_id)
        except Exception:
            return None
        return await self.collection.find_one({"_id": oid})
