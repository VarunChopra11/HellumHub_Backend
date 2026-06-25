import re

MAC_RE = re.compile(r"^[0-9A-F]{2}(:[0-9A-F]{2}){5}$")
# 12-char lowercase hex, no separators — the format used in MQTT topics and DB
MAC_PLAIN_RE = re.compile(r"^[0-9a-f]{12}$")


def normalize_mac(raw: str) -> str:
    """Return an uppercase colon-separated MAC address (e.g. 'AA:BB:CC:DD:EE:FF').

    Accepts input with colons, hyphens, or no separators in any case.
    Raises ValueError on invalid input.
    """
    candidate = raw.replace("-", ":").strip().upper()
    if len(candidate) == 12 and ":" not in candidate:
        candidate = ":".join(candidate[i : i + 2] for i in range(0, 12, 2))
    if not MAC_RE.fullmatch(candidate):
        raise ValueError("Invalid MAC format")
    return candidate


def normalize_mac_plain(raw: str) -> str:
    """Return a 12-char lowercase hex MAC address with no separators.

    This is the format used by the ESP32 firmware in MQTT topics and the
    format stored in the ``smarthome_devices`` collection.

    Accepts input with colons, hyphens, or no separators in any case.
    Raises ValueError on invalid input.

    Examples:
        >>> normalize_mac_plain("AA:BB:CC:DD:EE:FF")
        'aabbccddeeff'
        >>> normalize_mac_plain("aabb-ccdd-eeff")
        'aabbccddeeff'
        >>> normalize_mac_plain("aabbccddeeff")
        'aabbccddeeff'
    """
    stripped = raw.replace(":", "").replace("-", "").strip().lower()
    if not MAC_PLAIN_RE.fullmatch(stripped):
        raise ValueError(f"Invalid MAC address: '{raw}'. Expected 12 hex characters.")
    return stripped
