import logging
import time
from uuid import uuid4

from fastapi import Request

logger = logging.getLogger("mavi.api")


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


async def request_log_middleware(request: Request, call_next):
    request_id = str(uuid4())
    started = time.perf_counter()
    response = await call_next(request)
    route = request.scope.get("route")
    route_pattern = getattr(route, "path", "unmatched")
    logger.info(
        "request_complete method=%s route=%s status=%s duration_ms=%s request_id=%s",
        request.method,
        route_pattern,
        response.status_code,
        round((time.perf_counter() - started) * 1000),
        request_id,
    )
    response.headers["X-Request-ID"] = request_id
    return response

