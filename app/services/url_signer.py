import base64
import hashlib
import hmac
import time
from urllib.parse import urlencode


class UrlSigner:
    def __init__(self, secret: str | None, ttl_seconds: int) -> None:
        self.secret = (secret or "").encode("utf-8")
        self.ttl_seconds = ttl_seconds

    def sign(self, path: str) -> str:
        if not self.secret:
            return ""
        expires = int(time.time()) + self.ttl_seconds
        payload = f"{path}|{expires}".encode("utf-8")
        sig = hmac.new(self.secret, payload, hashlib.sha256).digest()
        token = base64.urlsafe_b64encode(sig).decode("utf-8").rstrip("=")
        return urlencode({"exp": expires, "sig": token})

    def verify(self, path: str, exp: int, sig: str) -> bool:
        if not self.secret:
            return False
        if exp < int(time.time()):
            return False
        payload = f"{path}|{exp}".encode("utf-8")
        expected = hmac.new(self.secret, payload, hashlib.sha256).digest()
        decoded = base64.urlsafe_b64decode(sig + "=" * ((4 - len(sig) % 4) % 4))
        return hmac.compare_digest(decoded, expected)
