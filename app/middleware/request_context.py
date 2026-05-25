import logging
import time
import uuid
from typing import Any

from app.core.logging import request_id_ctx


class RequestContextMiddleware:
    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive, send) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        headers = {k.decode("latin1"): v.decode("latin1") for k, v in scope.get("headers", [])}
        request_id = headers.get("x-request-id", str(uuid.uuid4()))
        request_id_ctx.set(request_id)

        method = scope.get("method", "GET")
        path = scope.get("path", "")
        logger = logging.getLogger("app.request")
        started = time.perf_counter()
        logger.info("request_started method=%s path=%s", method, path)

        status_code = 500

        async def send_wrapper(message):
            nonlocal status_code
            if message.get("type") == "http.response.start":
                status_code = int(message.get("status", 500))
                raw_headers = list(message.get("headers", []))
                raw_headers.append((b"x-request-id", request_id.encode("latin1")))
                message["headers"] = raw_headers
            await send(message)

        await self.app(scope, receive, send_wrapper)

        elapsed_ms = (time.perf_counter() - started) * 1000
        logger.info(
            "request_finished method=%s path=%s status=%s elapsed_ms=%.2f",
            method,
            path,
            status_code,
            elapsed_ms,
        )
