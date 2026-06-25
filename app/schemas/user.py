"""Pydantic schemas for consumer user API endpoints."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class GoogleAuthRequest(BaseModel):
    """Frontend sends this after a successful Google Sign-In."""
    id_token: str = Field(..., description="Google ID token from the client-side Sign-In flow")


class ConsumerTokenResponse(BaseModel):
    """Hellum JWT pair returned after successful Google SSO verification."""
    token_type: Literal["Bearer"] = "Bearer"
    access_token: str
    expires_in: int
    refresh_token: str


class UserResponse(BaseModel):
    id: str
    google_sub: str
    email: str
    display_name: str | None = None
    created_at: datetime
