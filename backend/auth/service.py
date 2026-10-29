"""
Shared credential-check logic for the single demo account, used by both
/auth/login (legacy) and /v1/auth/login (versioned) so there's exactly one
place that decides whether a login succeeds — the two endpoints differ only
in response shape, never in auth logic.
"""
import bcrypt

from core.config import settings


def authenticate_demo_account(username: str, password: str) -> bool:
    if not settings.demo_password_hash:
        # No credential configured (e.g. local dev with .env.example
        # defaults) — any username/password succeeds, matching the original
        # Milestone 1 stub. core/security_startup.py refuses to boot in
        # production without a hash set, so this branch is unreachable there.
        return True

    # Always run both comparisons — never short-circuit on username — so a
    # failed attempt can't be used to enumerate the valid username by timing.
    username_ok = username == settings.demo_username
    try:
        password_ok = bcrypt.checkpw(
            password.encode("utf-8")[:72],  # bcrypt's own 72-byte input limit
            settings.demo_password_hash.encode("utf-8"),
        )
    except ValueError:
        # Malformed hash in config — fail closed, never treat as a match.
        password_ok = False

    return username_ok and password_ok
