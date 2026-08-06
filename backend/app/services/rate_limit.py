"""Simple in-memory per-client rate limit for the local deployment."""

from collections import defaultdict, deque
from time import monotonic

from fastapi import HTTPException

from app.config import settings


_requests: dict[str, deque[float]] = defaultdict(deque)


def enforce_rate_limit(client_key: str) -> None:
    now = monotonic()
    window = _requests[client_key]
    while window and window[0] <= now - 60:
        window.popleft()
    if len(window) >= settings.rate_limit_per_minute:
        raise HTTPException(status_code=429, detail="Too many scan requests. Try again in a minute.")
    window.append(now)
