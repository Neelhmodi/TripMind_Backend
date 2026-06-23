import time
import logging
from collections import defaultdict
from fastapi import Request, HTTPException

logger = logging.getLogger(__name__)

MAX_REQUESTS = 30
WINDOW_SECONDS = 60

_rate_store: dict[str, tuple[int, float]] = defaultdict(lambda: (0, 0.0))


def check_rate_limit(request: Request):
    ip = (
        request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        or (request.client.host if request.client else "unknown")
    )
    now = time.time()
    count, window_start = _rate_store[ip]

    if now - window_start > WINDOW_SECONDS:
        count = 0
        window_start = now

    count += 1
    _rate_store[ip] = (count, window_start)

    if count > MAX_REQUESTS:
        retry_after = int(WINDOW_SECONDS - (now - window_start))
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Retry after {retry_after}s.",
            headers={"Retry-After": str(retry_after)},
        )
