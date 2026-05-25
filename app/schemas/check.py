from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CheckQuery(BaseModel):
    mac: str
    ver: str


class FirmwareCheckResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    update_available: bool
    version: str | None = None
    firmware_url: str | None = None
    sha256: str | None = None
    size: int | None = None


class CheckDecisionAudit(BaseModel):
    mac: str
    device_type: str
    current_version: str
    checked_at: datetime
    result: Literal[
        "blocked",
        "invalid_version",
        "no_active_release",
        "version_not_greater",
        "rollout_not_included",
        "update_available",
        "override_invalid",
        "error_fallback",
    ]
    chosen_version: str | None = None
    chosen_release_id: str | None = None
    message: str | None = None
    request_id: str | None = None
