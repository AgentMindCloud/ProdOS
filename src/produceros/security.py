"""Security primitives: password hashing, tokens, path safety, headers.

Centralizing these here means every other module reuses the same
audited helpers instead of re-implementing hashing, randomness, or path
validation.
"""

from __future__ import annotations

import hmac
import re
import secrets
import string
from collections.abc import Sequence
from pathlib import Path

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHash, VerificationError, VerifyMismatchError

_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2)

PAIRING_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O/1/I ambiguity
PAIRING_CODE_LENGTH = 8


def hash_password(plain_password: str) -> str:
    return _hasher.hash(plain_password)


def verify_password(hashed: str, plain_password: str) -> bool:
    try:
        return _hasher.verify(hashed, plain_password)
    except (VerifyMismatchError, VerificationError, InvalidHash):
        return False


def needs_rehash(hashed: str) -> bool:
    try:
        return _hasher.check_needs_rehash(hashed)
    except InvalidHash:
        return True


def generate_session_token() -> str:
    return secrets.token_urlsafe(32)


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(24)


def constant_time_equals(a: str, b: str) -> bool:
    return hmac.compare_digest(a, b)


def generate_pairing_code(length: int = PAIRING_CODE_LENGTH) -> str:
    return "".join(secrets.choice(PAIRING_CODE_ALPHABET) for _ in range(length))


_SAFE_NAME_RE = re.compile(r"^[A-Za-z0-9 _.\-\(\)\[\]&',!]+$")


def is_safe_display_name(value: str) -> bool:
    """Loose validation for user-visible free-text fields (not path safety)."""
    return bool(value) and len(value) <= 512


class PathSecurityError(ValueError):
    """Raised when a path fails allowlist or traversal checks."""


def resolve_within_allowed_roots(
    candidate: str | Path, allowed_roots: Sequence[str | Path]
) -> Path:
    """Resolve ``candidate`` and confirm it is inside one of ``allowed_roots``.

    Prevents path traversal (``..``), symlink escapes, and access to
    locations outside the producer's configured scanner roots. Raises
    ``PathSecurityError`` if the path cannot be safely resolved or falls
    outside every allowed root.
    """
    if not allowed_roots:
        raise PathSecurityError("No scanner roots are configured.")

    try:
        resolved = Path(candidate).resolve(strict=False)
    except OSError as exc:  # pragma: no cover - defensive, e.g. bad path chars
        raise PathSecurityError(f"Could not resolve path: {exc}") from exc

    for root in allowed_roots:
        try:
            resolved_root = Path(root).resolve(strict=False)
        except OSError:
            continue
        try:
            resolved.relative_to(resolved_root)
            return resolved
        except ValueError:
            continue

    raise PathSecurityError(f"Path '{resolved}' is outside all approved scanner roots.")


def is_allowed_extension(path: str | Path, allowed_extensions: list[str]) -> bool:
    suffix = Path(path).suffix.lower()
    return suffix in {ext.lower() for ext in allowed_extensions}


def is_within_size_limit(size_bytes: int, max_mb: int) -> bool:
    return size_bytes <= max_mb * 1024 * 1024


SECURITY_HEADERS: dict[str, str] = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self'; "
        "img-src 'self' data:; "
        "font-src 'self'; "
        "connect-src 'self'; "
        "form-action 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "object-src 'none'"
    ),
}


def random_alphanumeric(length: int = 16) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))
