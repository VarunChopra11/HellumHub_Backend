"""
Device Model Catalog domain models.

A DeviceModel is a reusable hardware definition that describes what endpoints
(controllable components) a physical ESP32 device exposes. When a device is
provisioned via the MQTT binding flow, its endpoint list is copied from the
matching DeviceModel in this catalog.

This design lets us support any future device (e.g. a 2-switch board, a smart
pendant, a voice assistant module) without changing any application code —
just register the model via the admin API.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class EndpointDefinition:
    """Defines a single controllable endpoint on a device model.

    Attributes:
        id:          Unique endpoint identifier used in MQTT payloads and Google
                     Home device IDs (e.g. 'light1', 'relay_a', 'motor').
        name:        Human-readable label shown in the Google Home app.
        google_type: Google Home device type string.
                     See https://developers.google.com/assistant/smarthome/guides
    """

    id: str
    name: str
    google_type: str

    @classmethod
    def from_dict(cls, d: dict) -> "EndpointDefinition":
        return cls(id=d["id"], name=d["name"], google_type=d["google_type"])

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "google_type": self.google_type}


@dataclass
class DeviceModelDoc:
    """Runtime representation of a device_models MongoDB document."""

    id: str
    model_id: str           # URL-safe slug, e.g. "4-switch-board"
    display_name: str       # e.g. "4-Switch Smart Board"
    manufacturer: str       # e.g. "Hellum"
    hw_version: str         # e.g. "1.0"
    endpoints: list[EndpointDefinition] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def from_doc(cls, doc: dict) -> "DeviceModelDoc":
        return cls(
            id=str(doc["_id"]),
            model_id=doc["model_id"],
            display_name=doc["display_name"],
            manufacturer=doc.get("manufacturer", ""),
            hw_version=doc.get("hw_version", "1.0"),
            endpoints=[EndpointDefinition.from_dict(e) for e in doc.get("endpoints", [])],
            created_at=doc.get("created_at", datetime.utcnow()),
        )
