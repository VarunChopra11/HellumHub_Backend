import json
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any


@dataclass
class ParsedLimit:
    max_requests: int
    window_seconds: int


def parse_limit(value: str) -> ParsedLimit:
    raw = value.strip().lower()
    count_str, unit = raw.split("/")
    count = int(count_str)

    unit_map = {
        "s": 1,
        "sec": 1,
        "second": 1,
        "seconds": 1,
        "m": 60,
        "min": 60,
        "minute": 60,
        "minutes": 60,
        "h": 3600,
        "hour": 3600,
        "hours": 3600,
    }
    if unit not in unit_map:
        raise ValueError("Invalid rate limit unit")

    return ParsedLimit(max_requests=count, window_seconds=unit_map[unit])


class PathRateLimiterMiddleware:
    def __init__(self, app, *, limit: str, path: str) -> None:
        self.app = app
        self.path = path
        self.parsed = parse_limit(limit)
        self.hits: dict[str, deque[float]] = defaultdict(deque)

    async def __call__(self, scope: dict[str, Any], receive, send) -> None:
        if scope.get("type") != "http" or scope.get("path") != self.path:
            await self.app(scope, receive, send)
            return

        now = time.time()
        headers = {k.decode("latin1"): v.decode("latin1") for k, v in scope.get("headers", [])}
        client_ip = headers.get("x-forwarded-for", "").split(",")[0].strip()
        if not client_ip:
            client = scope.get("client")
            if client:
                client_ip = str(client[0])

        key = client_ip or "unknown"
        window_start = now - self.parsed.window_seconds
        bucket = self.hits[key]
        while bucket and bucket[0] < window_start:
            bucket.popleft()

        if len(bucket) >= self.parsed.max_requests:
            body = json.dumps({"update_available": False, "detail": "rate_limit_exceeded"}).encode(
                "utf-8"
            )
            await send(
                {
                    "type": "http.response.start",
                    "status": 429,
                    "headers": [
                        (b"content-type", b"application/json"),
                        (b"content-length", str(len(body)).encode("ascii")),
                        (b"retry-after", str(self.parsed.window_seconds).encode("ascii")),
                    ],
                }
            )
            await send({"type": "http.response.body", "body": body})
            return

        bucket.append(now)
        await self.app(scope, receive, send)
