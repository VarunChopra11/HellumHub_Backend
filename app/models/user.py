"""
User model for consumer accounts.

Authentication is exclusively via Google Sign-In (OAuth). The ``google_sub``
field is the stable, immutable identifier issued by Google for each account.
No passwords are stored.
"""

from __future__ import annotations

from datetime import datetime


class UserDoc:
    """Runtime representation of a users MongoDB document.

    Not a Pydantic model on purpose — avoids accidentally serialising internal
    fields in API responses. Use ``app.schemas.user`` for validated shapes.
    """

    __slots__ = ("id", "google_sub", "email", "display_name", "created_at")

    def __init__(
        self,
        *,
        id: str,
        google_sub: str,
        email: str,
        display_name: str | None,
        created_at: datetime,
    ) -> None:
        self.id = id
        self.google_sub = google_sub
        self.email = email
        self.display_name = display_name
        self.created_at = created_at

    @classmethod
    def from_doc(cls, doc: dict) -> "UserDoc":
        return cls(
            id=str(doc["_id"]),
            google_sub=doc["google_sub"],
            email=doc["email"],
            display_name=doc.get("display_name"),
            created_at=doc["created_at"],
        )
