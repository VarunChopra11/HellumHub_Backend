"""
Pydantic schemas for Smart Home device management and Google Home fulfillment.

Covers:
  - Device model catalog (admin endpoints)
  - Device provisioning via MQTT Binding Token
  - Consumer device management
  - Google Home Fulfillment request/response shapes (SYNC, QUERY, EXECUTE)
  - OAuth 2.0 token response shape
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Device Model Catalog schemas (admin-managed)
# ---------------------------------------------------------------------------

class EndpointDefinitionSchema(BaseModel):
    """One endpoint in a device model definition."""
    id: str = Field(..., description="MQTT payload 'device' field value, e.g. 'light1'")
    name: str = Field(..., description="Human-readable label, e.g. 'Light 1'")
    google_type: str = Field(
        ...,
        description="Google Home device type, e.g. 'action.devices.types.LIGHT'",
    )


class DeviceModelCreate(BaseModel):
    model_id: str = Field(
        ...,
        min_length=2,
        max_length=64,
        pattern=r"^[a-z0-9\-]+$",
        description="URL-safe slug, e.g. '4-switch-board'",
    )
    display_name: str = Field(..., min_length=1, max_length=128)
    manufacturer: str = Field("Hellum", max_length=64)
    hw_version: str = Field("1.0", max_length=32)
    endpoints: list[EndpointDefinitionSchema] = Field(
        ..., min_length=1, description="At least one endpoint required"
    )


class DeviceModelUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=128)
    manufacturer: str | None = Field(default=None, max_length=64)
    hw_version: str | None = Field(default=None, max_length=32)
    endpoints: list[EndpointDefinitionSchema] | None = None


class DeviceModelResponse(BaseModel):
    id: str
    model_id: str
    display_name: str
    manufacturer: str
    hw_version: str
    endpoints: list[EndpointDefinitionSchema]
    created_at: datetime


# ---------------------------------------------------------------------------
# Smart Home Device instance schemas
# ---------------------------------------------------------------------------

class EndpointResponse(BaseModel):
    """Runtime state of a single endpoint on a provisioned device."""
    id: str
    name: str
    google_type: str
    state: bool


class SmartHomeDeviceResponse(BaseModel):
    id: str
    mac: str
    user_id: str
    name: str
    device_model: str
    endpoints: list[EndpointResponse]
    created_at: datetime


class DeviceRenameRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)


# ---------------------------------------------------------------------------
# MQTT Binding Token provisioning
# ---------------------------------------------------------------------------

class BindingTokenResponse(BaseModel):
    """Returned to the consumer frontend after requesting a binding token."""
    binding_token: str
    expires_in: int  # seconds


# ---------------------------------------------------------------------------
# OAuth 2.0 token response (used by Google Home Account Linking)
# ---------------------------------------------------------------------------

class OAuthTokenResponse(BaseModel):
    token_type: Literal["Bearer"] = "Bearer"
    access_token: str
    expires_in: int
    refresh_token: str


# ---------------------------------------------------------------------------
# Admin role management schemas
# ---------------------------------------------------------------------------

class AdminRoleGrantRequest(BaseModel):
    email: str = Field(..., description="Google account email to grant admin access")


class AdminRoleResponse(BaseModel):
    id: str
    email: str
    role: str
    granted_by: str
    created_at: datetime


# ---------------------------------------------------------------------------
# Google Home Fulfillment — request envelope
# ---------------------------------------------------------------------------

class FulfillmentInput(BaseModel):
    intent: str
    payload: dict[str, Any] = Field(default_factory=dict)


class FulfillmentRequest(BaseModel):
    requestId: str
    inputs: list[FulfillmentInput]


# ---------------------------------------------------------------------------
# Generic fulfillment response envelope
# ---------------------------------------------------------------------------

class FulfillmentResponse(BaseModel):
    requestId: str
    payload: dict[str, Any]
