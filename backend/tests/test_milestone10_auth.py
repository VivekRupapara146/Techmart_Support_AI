"""
Tests for the Milestone 10 demo credential check (closes the "anyone can
log in" gap flagged before public deployment).
"""
import sys
import asyncio
sys.path.insert(0, ".")

import bcrypt
from mongomock_motor import AsyncMongoMockClient


def _setup_test_app_with_demo_creds(demo_hash: str):
    from fastapi.testclient import TestClient
    import main
    import core.config as config_module
    import database.mongo as mongo_module
    from database.conversations import ensure_indexes

    config_module.settings.demo_username = "demo"
    config_module.settings.demo_password_hash = demo_hash

    mock_db = AsyncMongoMockClient()["test_db"]
    mongo_module._db = mock_db
    asyncio.run(ensure_indexes(mock_db))

    return TestClient(main.app)


def test_login_stub_mode_when_no_hash_configured():
    """Local dev default: no DEMO_PASSWORD_HASH set -> M1 stub behavior
    (any credentials work) so local development stays frictionless."""
    client = _setup_test_app_with_demo_creds(demo_hash="")
    r = client.post("/auth/login", json={"username": "anyone", "password": "anything"})
    assert r.status_code == 200
    print("test_login_stub_mode_when_no_hash_configured: PASS")


def test_login_correct_demo_credentials_succeeds():
    real_hash = bcrypt.hashpw(b"correct-horse-battery-staple", bcrypt.gensalt()).decode()
    client = _setup_test_app_with_demo_creds(demo_hash=real_hash)
    r = client.post("/auth/login", json={"username": "demo", "password": "correct-horse-battery-staple"})
    assert r.status_code == 200, r.text
    assert "access_token" in r.json()["data"]
    print("test_login_correct_demo_credentials_succeeds: PASS")


def test_login_wrong_password_rejected():
    real_hash = bcrypt.hashpw(b"correct-horse-battery-staple", bcrypt.gensalt()).decode()
    client = _setup_test_app_with_demo_creds(demo_hash=real_hash)
    r = client.post("/auth/login", json={"username": "demo", "password": "wrong-password"})
    assert r.status_code == 401
    print("test_login_wrong_password_rejected: PASS")


def test_login_wrong_username_rejected():
    real_hash = bcrypt.hashpw(b"correct-horse-battery-staple", bcrypt.gensalt()).decode()
    client = _setup_test_app_with_demo_creds(demo_hash=real_hash)
    r = client.post("/auth/login", json={"username": "not-demo", "password": "correct-horse-battery-staple"})
    assert r.status_code == 401
    print("test_login_wrong_username_rejected: PASS")


def test_error_message_identical_for_wrong_username_vs_wrong_password():
    """Enumeration resistance: both failure modes must be indistinguishable."""
    real_hash = bcrypt.hashpw(b"correct-horse-battery-staple", bcrypt.gensalt()).decode()
    client = _setup_test_app_with_demo_creds(demo_hash=real_hash)

    r1 = client.post("/auth/login", json={"username": "wrong-user", "password": "correct-horse-battery-staple"})
    r2 = client.post("/auth/login", json={"username": "demo", "password": "wrong-password"})
    assert r1.status_code == r2.status_code == 401
    assert r1.json()["detail"] == r2.json()["detail"]
    print("test_error_message_identical_for_wrong_username_vs_wrong_password: PASS")


def test_production_guard_rejects_missing_demo_hash():
    from core.security_startup import verify_production_secrets
    import core.config as config_module

    original_env = config_module.settings.environment
    original_key = config_module.settings.jwt_secret_key
    original_hash = config_module.settings.demo_password_hash
    try:
        config_module.settings.environment = "production"
        config_module.settings.jwt_secret_key = "a" * 64
        config_module.settings.demo_password_hash = ""
        try:
            verify_production_secrets()
            print("test_production_guard_rejects_missing_demo_hash: FAIL (should have raised)")
        except RuntimeError:
            print("test_production_guard_rejects_missing_demo_hash: PASS")
    finally:
        config_module.settings.environment = original_env
        config_module.settings.jwt_secret_key = original_key
        config_module.settings.demo_password_hash = original_hash


if __name__ == "__main__":
    test_login_stub_mode_when_no_hash_configured()
    test_login_correct_demo_credentials_succeeds()
    test_login_wrong_password_rejected()
    test_login_wrong_username_rejected()
    test_error_message_identical_for_wrong_username_vs_wrong_password()
    test_production_guard_rejects_missing_demo_hash()
    print("\nAll Milestone 10 auth tests passed.")
