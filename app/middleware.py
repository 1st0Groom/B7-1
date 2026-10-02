import asyncio
import math
import time
from collections import defaultdict, deque
from uuid import uuid4

from starlette.requests import Request

from app.errors import AppError, error_response
from app.logging import event, request_id


class RateLimiter:
    def __init__(self):
        self.buckets = defaultdict(deque)
        self.last_cleanup = 0.0

    def check(self, key, limit=10):
        now = time.monotonic()
        if now - self.last_cleanup > 60:
            self.buckets = defaultdict(
                deque, {k: v for k, v in self.buckets.items() if v and v[-1] > now - 60}
            )
            self.last_cleanup = now
        bucket = self.buckets[key]
        while bucket and bucket[0] <= now - 60:
            bucket.popleft()
        if len(bucket) >= limit:
            raise AppError(
                "RATE_LIMITED",
                429,
                headers={"Retry-After": str(max(1, math.ceil(60 - now + bucket[0])))},
            )
        bucket.append(now)


class RequestMiddleware:
    def __init__(self, app, settings):
        self.app = app
        self.settings = settings

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        request = Request(scope)
        rid = uuid4().hex
        scope.setdefault("state", {})["request_id"] = rid
        token = request_id.set(rid)
        start = time.monotonic()
        status = 500
        started = False

        async def tracked_send(message):
            nonlocal status, started
            if message["type"] == "http.response.start":
                status = message["status"]
                started = True
                message["headers"] += [
                    (b"x-request-id", rid.encode()),
                    (b"x-content-type-options", b"nosniff"),
                    (b"referrer-policy", b"same-origin"),
                    (b"cache-control", b"no-store"),
                    (
                        b"content-security-policy",
                        b"default-src 'self'; script-src 'self'; "
                        b"style-src 'self'; img-src 'self'; connect-src 'self'; "
                        b"frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
                    ),
                ]
            await send(message)

        event("request_received", method=request.method, path=request.url.path)
        try:
            body_messages = []
            if request.method not in {"GET", "HEAD", "OPTIONS"}:
                if request.headers.get("origin") != self.settings.app_origin:
                    raise AppError("ORIGIN_REJECTED", 403)
                size = 0
                # Bound both chunked bodies and reads from slow clients.
                async with asyncio.timeout(10):
                    while True:
                        message = await receive()
                        if message["type"] == "http.disconnect":
                            return
                        size += len(message.get("body", b""))
                        if size > 16384:
                            raise AppError("REQUEST_TOO_LARGE", 413)
                        body_messages.append(message)
                        if not message.get("more_body", False):
                            break
                if size and request.headers.get("content-type", "").split(";")[0].strip() != (
                    "application/json"
                ):
                    raise AppError("UNSUPPORTED_MEDIA_TYPE", 415)

            async def replay_receive():
                if body_messages:
                    return body_messages.pop(0)
                return await receive()

            await self.app(scope, replay_receive, tracked_send)
        except AppError as exc:
            if not started:
                await error_response(request, exc)(scope, receive, tracked_send)
        except TimeoutError:
            if not started:
                await error_response(request, AppError("REQUEST_TOO_LARGE", 408))(
                    scope, receive, tracked_send
                )
        except Exception:
            event("request_failed", code="INTERNAL_ERROR")
            if not started:
                await error_response(request, AppError("INTERNAL_ERROR"))(
                    scope, receive, tracked_send
                )
        finally:
            event(
                "request_completed",
                status_code=status,
                latency_ms=int((time.monotonic() - start) * 1000),
            )
            request_id.reset(token)
