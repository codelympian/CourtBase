"""Shared SlowAPI rate limiter."""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings

# headers_enabled is intentionally off: SlowAPI's header injection requires every
# decorated endpoint to declare a `response: Response` parameter, which would 500
# our auth routes. Rate limiting itself (429 on exceed) is unaffected.
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[settings.RATE_LIMIT_DEFAULT],
    headers_enabled=False,
)
