"""Admin user model for Role-Based Access Control."""

from __future__ import annotations

from datetime import datetime
from enum import Enum


class AdminRole(str, Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"


class AdminUserDoc:
    """Runtime representation of an admin_users MongoDB document.

    Admin access is granted by email address (verified via Google Sign-In).
    The Super Admin email is set in .env; all others are stored here.
    """

    __slots__ = ("id", "email", "role", "granted_by", "created_at")

    def __init__(
        self,
        *,
        id: str,
        email: str,
        role: AdminRole,
        granted_by: str,
        created_at: datetime,
    ) -> None:
        self.id = id
        self.email = email
        self.role = role
        self.granted_by = granted_by
        self.created_at = created_at

    @classmethod
    def from_doc(cls, doc: dict) -> "AdminUserDoc":
        return cls(
            id=str(doc["_id"]),
            email=doc["email"],
            role=AdminRole(doc.get("role", AdminRole.ADMIN)),
            granted_by=doc.get("granted_by", ""),
            created_at=doc["created_at"],
        )
