import pytest

from app.core.config import Settings

_BASE_KWARGS = {
    "_env_file": None,
    "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost/db",
    "SECRET_KEY": "change-me-to-a-random-64-char-string",
}


def test_placeholder_secret_key_rejected_in_production():
    with pytest.raises(ValueError, match="placeholder value"):
        Settings(**_BASE_KWARGS, APP_ENV="production")


def test_placeholder_secret_key_allowed_outside_production():
    settings = Settings(**_BASE_KWARGS, APP_ENV="development")
    assert _BASE_KWARGS["SECRET_KEY"] == settings.SECRET_KEY


def test_real_secret_key_allowed_in_production():
    settings = Settings(
        _env_file=None,
        DATABASE_URL=_BASE_KWARGS["DATABASE_URL"],
        SECRET_KEY="a-genuinely-random-production-secret-key-value",
        APP_ENV="production",
    )
    assert settings.is_production is True
