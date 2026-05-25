import re

MAC_RE = re.compile(r"^[0-9A-F]{2}(:[0-9A-F]{2}){5}$")


def normalize_mac(raw: str) -> str:
    candidate = raw.replace("-", ":").strip().upper()
    if len(candidate) == 12 and ":" not in candidate:
        candidate = ":".join(candidate[i : i + 2] for i in range(0, 12, 2))
    if not MAC_RE.fullmatch(candidate):
        raise ValueError("Invalid MAC format")
    return candidate
