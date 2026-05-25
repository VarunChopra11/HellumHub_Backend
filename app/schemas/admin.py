from datetime import datetime

from pydantic import BaseModel, Field, field_validator
import semver


class CreateReleaseRequest(BaseModel):
    device_type: str = Field(..., min_length=2, max_length=64)
    version: str = Field(..., min_length=1, max_length=64)
    rollout_percentage: int = Field(100, ge=0, le=100)
    enabled: bool = False
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("version")
    @classmethod
    def validate_version(cls, value: str) -> str:
        semver.Version.parse(value)
        return value


class ReleaseResponse(BaseModel):
    id: str
    device_type: str
    version: str
    rollout_percentage: int
    enabled: bool
    notes: str | None = None
    firmware_file_id: str | None = None
    sha256: str | None = None
    size: int | None = None
    created_at: datetime
    updated_at: datetime


class ToggleReleaseRequest(BaseModel):
    enabled: bool


class RolloutUpdateRequest(BaseModel):
    rollout_percentage: int = Field(..., ge=0, le=100)


class OverrideUpsertRequest(BaseModel):
    version: str
    reason: str | None = Field(default=None, max_length=300)

    @field_validator("version")
    @classmethod
    def validate_version(cls, value: str) -> str:
        semver.Version.parse(value)
        return value


class OverrideResponse(BaseModel):
    id: str
    device_type: str
    mac: str
    version: str
    reason: str | None = None
    updated_at: datetime


class FirmwareUploadResponse(BaseModel):
    file_id: str
    sha256: str
    size: int
    mime: str
    filename: str


class AdminMessageResponse(BaseModel):
    message: str


class ReleaseListResponse(BaseModel):
    releases: list[ReleaseResponse]
