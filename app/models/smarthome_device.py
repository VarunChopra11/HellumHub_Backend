"""
Smart Home Device domain models — dynamic endpoint architecture.

Each physical ESP32 device stores its endpoint list directly on its document.
The list is seeded from the DeviceModel catalog at provisioning time, so the
device document is self-contained and querying Google Home intents never needs
to join against the device_models collection.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class DeviceEndpoint:
    """A single controllable endpoint on a provisioned device.

    The ``state`` field holds the most recently known ON/OFF value, updated by
    the MQTT bridge whenever the ESP32 publishes to its state topic.
    """

    id: str           # Matches ESP32 firmware payload "device" field
    name: str         # Human-readable label (e.g. "Light 1")
    google_type: str  # Google Home device type string
    state: bool = False

    @classmethod
    def from_dict(cls, d: dict) -> "DeviceEndpoint":
        return cls(
            id=d["id"],
            name=d["name"],
            google_type=d["google_type"],
            state=bool(d.get("state", False)),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "google_type": self.google_type,
            "state": self.state,
        }


@dataclass
class SmartHomeDeviceDoc:
    """Runtime representation of a smarthome_devices MongoDB document.

    ``mac`` is stored in 12-char lowercase hex format (e.g. ``aabbccddeeff``)
    matching the ESP32 firmware's MQTT topic convention.
    """

    id: str
    mac: str                          # 12-char lowercase hex, no colons
    user_id: str                      # ObjectId string of the owning User
    name: str                         # Human-readable name (e.g. "Living Room Board")
    device_model: str                 # Model slug (e.g. "4-switch-board")
    endpoints: list[DeviceEndpoint] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def get_endpoint_ids(self) -> frozenset[str]:
        """Return the set of valid endpoint IDs for fast membership tests."""
        return frozenset(e.id for e in self.endpoints)

    def get_state_dict(self) -> dict[str, bool]:
        """Return {endpoint_id: state} map — used in QUERY intent responses."""
        return {e.id: e.state for e in self.endpoints}

    @classmethod
    def from_doc(cls, doc: dict) -> "SmartHomeDeviceDoc":
        return cls(
            id=str(doc["_id"]),
            mac=doc["mac"],
            user_id=str(doc["user_id"]),
            name=doc.get("name", doc["mac"]),
            device_model=doc.get("device_model", "unknown"),
            endpoints=[DeviceEndpoint.from_dict(e) for e in doc.get("endpoints", [])],
            created_at=doc.get("created_at", datetime.utcnow()),
        )
