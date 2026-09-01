"""Password hashing, JWT issuance/verification, and API-key hashing.

Design:
- Passwords: bcrypt, used directly (not via passlib — passlib has been
  unmaintained since 2020 and its internal self-test breaks outright on
  bcrypt>=4.1, which turned silent-truncation-past-72-bytes into a hard
  ValueError; see the truncation handling below).
- Access tokens: short-lived JWT (HS256), carry `sub` (user id), `org_id`, `type=access`.
- Refresh tokens: opaque random string; only a SHA-256 hash is persisted
  (see `models.refresh_token.RefreshToken`), so a stolen DB dump doesn't yield
  usable tokens. The raw token is returned to the client once.
- API keys: same hash-at-rest pattern as refresh tokens, with a short
  non-secret `key_prefix` stored in the clear for fast lookup before the
  (slower) hash comparison.
"""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any

import bcrypt
import jwt

from app.core.config import settings

# bcrypt only uses the first 72 bytes of the input; modern bcrypt (>=4.1)
# raises instead of silently truncating, so we truncate ourselves. This must
# be applied identically in hash and verify — it's a pure function of the
# input, not a security-relevant secret, so determinism is all that matters.
_BCRYPT_MAX_BYTES = 72


class TokenType(StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"


def _bcrypt_bytes(plain_password: str) -> bytes:
    return plain_password.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(plain_password: str) -> str:
    hashed = bcrypt.hashpw(_bcrypt_bytes(plain_password), bcrypt.gensalt())
    return hashed.decode("ascii")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(_bcrypt_bytes(plain_password), hashed_password.encode("ascii"))
    except ValueError:
        # Malformed/foreign hash format (e.g. hand-edited DB row) — treat as
        # a verification failure rather than a 500.
        return False


def create_access_token(
    *, subject: str, organization_id: str | None = None, extra_claims: dict[str, Any] | None = None
) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload: dict[str, Any] = {
        "sub": subject,
        "org_id": organization_id,
        "type": TokenType.ACCESS.value,
        "exp": expire,
        "iat": datetime.now(UTC),
        # JWT `exp`/`iat` are second-granularity (RFC 7519 NumericDate), so
        # two tokens for the same user issued within the same second would
        # otherwise be byte-identical (same header+payload+key => same HMAC
        # signature) — caught by actually running the refresh-token
        # integration test against a real server, where login and refresh
        # can easily land in the same wall-clock second. `jti` guarantees
        # distinct tokens regardless of timing.
        "jti": secrets.token_urlsafe(16),
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    """Raises jwt.PyJWTError subclasses on invalid/expired tokens — callers
    (api.deps) translate these into HTTP 401."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])


def generate_opaque_token() -> str:
    """A cryptographically random, URL-safe token for refresh tokens / API keys."""
    return secrets.token_urlsafe(48)


def hash_opaque_token(raw_token: str) -> str:
    """SHA-256 is fine here (not bcrypt): these are already high-entropy random
    tokens, not human-chosen passwords, so we don't need a slow KDF — we need
    fast, deterministic lookup by hash."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def generate_api_key() -> tuple[str, str, str]:
    """Returns (raw_key, key_prefix, key_hash).

    The raw key (shown once) is `rf_live_<random>`; `key_prefix` is the first
    12 chars after the scheme, stored unhashed to let lookups narrow candidate
    rows before the hash comparison.
    """
    raw_secret = secrets.token_urlsafe(32)
    raw_key = f"rf_live_{raw_secret}"
    key_prefix = raw_key[:16]
    key_hash = hash_opaque_token(raw_key)
    return raw_key, key_prefix, key_hash
