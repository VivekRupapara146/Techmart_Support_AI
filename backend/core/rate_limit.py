"""
Global rate limiting, applied at the app level so no future endpoint
can be added without a default limit by accident.

Per-endpoint overrides are still possible via the `@limiter.limit(...)`
decorator when a route needs a different threshold.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

from core.config import settings

limiter = Limiter(key_func=get_remote_address, default_limits=[settings.rate_limit_default])
