"""Repository for admin user RBAC."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError

logger = logging.getLogger(__name__)


class AdminUserRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.collection = db.admin_users

    async def grant_admin(
        self,
        *,
        email: str,
        role: str = "admin",
        granted_by: str,
    ) -> dict[str, Any]:
        """Grant admin access to a Google email address.

        Raises ValueError if the email is already an admin.
        """
        now = datetime.now(UTC)
        doc: dict[str, Any] = {
            "email": email.lower().strip(),
            "role": role,
            "granted_by": granted_by,
            "created_at": now,
        }
        try:
            result = await self.collection.insert_one(doc)
        except DuplicateKeyError as exc:
            raise ValueError(f"'{email}' already has admin access.") from exc
        doc["_id"] = result.inserted_id
        return doc

    async def is_admin(self, email: str) -> bool:
        """Check if an email address is registered as an admin."""
        doc = await self.collection.find_one({"email": email.lower().strip()})
        return doc is not None

    async def get_by_email(self, email: str) -> dict[str, Any] | None:
        return await self.collection.find_one({"email": email.lower().strip()})

    async def list_all(self) -> list[dict[str, Any]]:
        cursor = self.collection.find({})
        return await cursor.to_list(length=None)

    async def revoke_admin(self, email: str) -> bool:
        """Remove admin access for an email. Returns True if a document was deleted."""
        result = await self.collection.delete_one({"email": email.lower().strip()})
        return result.deleted_count > 0
