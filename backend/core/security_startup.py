"""
Fails fast at startup if running in production with an obviously
placeholder secret — better to crash loudly at deploy time than silently
run with a guessable JWT signing key (Instruction 7: secret management).
"""
from core.config import settings

_KNOWN_PLACEHOLDER_VALUES = {
    "change-this-to-a-long-random-string",
    "",
    "secret",
    "changeme",
}


def verify_production_secrets() -> None:
    if not settings.is_production:
        return

    if settings.jwt_secret_key.lower() in _KNOWN_PLACEHOLDER_VALUES or len(settings.jwt_secret_key) < 32:
        raise RuntimeError(
            "Refusing to start in production: JWT_SECRET_KEY is missing, a known "
            "placeholder, or too short (<32 chars). Generate a real secret, e.g. "
            "`python -c \"import secrets; print(secrets.token_hex(32))\"`."
        )

    if not settings.demo_password_hash:
        raise RuntimeError(
            "Refusing to start in production: DEMO_PASSWORD_HASH is not set. "
            "Without it, /auth/login falls back to accepting ANY credentials — "
            "fine for local dev, not for a public deployment. Generate one with "
            "`python -m scripts.generate_password_hash`."
        )
