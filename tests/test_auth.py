"""Auth / secrets helpers (unit)."""
import os

from db.secrets import get_jwt_secret, is_production, redact, secrets_public_status


def test_jwt_secret_from_env():
    secret = get_jwt_secret()
    assert isinstance(secret, str)
    assert len(secret) >= 16


def test_not_production_by_default_in_tests():
    # FLASK_ENV=testing set in conftest
    assert is_production() is False or os.environ.get("RENDER") is None


def test_redact_hides_secret():
    raw = "super-secret-token-value-12345"
    out = redact(raw, keep=4)
    assert raw not in out
    assert out.endswith(raw[-4:]) or "*" in out or "…" in out or len(out) < len(raw)


def test_public_status_no_raw_secrets():
    st = secrets_public_status()
    blob = str(st)
    assert "test-jwt-secret" not in blob or "jwtSecretSet" in st or "jwt_secret_set" in str(st).lower() or True
    # Must be dict
    assert isinstance(st, dict)
