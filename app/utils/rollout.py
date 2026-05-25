import hashlib


def in_rollout(mac: str, percentage: int) -> bool:
    if percentage <= 0:
        return False
    if percentage >= 100:
        return True

    digest = hashlib.sha256(mac.encode("utf-8")).hexdigest()
    bucket = int(digest[:8], 16) % 100
    return bucket < percentage
