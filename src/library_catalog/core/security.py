import base64
import hashlib
import hmac
import json
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any


def hash_password(password: str, iterations: int = 100_000) -> str:
    """Hash password using PBKDF2-HMAC-SHA256."""
    salt = secrets.token_hex(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    ).hex()
    return f"pbkdf2_sha256${iterations}${salt}${password_hash}"


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify password against stored PBKDF2 hash."""
    try:
        algorithm, iterations_str, salt, password_hash = hashed_password.split("$", 3)
    except ValueError:
        return False

    if algorithm != "pbkdf2_sha256":
        return False

    computed_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        int(iterations_str),
    ).hex()
    return hmac.compare_digest(computed_hash, password_hash)


def create_access_token(
    subject: str,
    role: str,
    secret_key: str,
    expires_minutes: int,
) -> str:
    """Create a signed JWT access token."""
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": subject,
        "role": role,
        "type": "access",
        "exp": int(
            (datetime.now(UTC) + timedelta(minutes=expires_minutes)).timestamp()
        ),
    }

    encoded_header = _b64encode_json(header)
    encoded_payload = _b64encode_json(payload)
    signing_input = f"{encoded_header}.{encoded_payload}"
    signature = hmac.new(
        secret_key.encode("utf-8"),
        signing_input.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    encoded_signature = _b64encode(signature)
    return f"{signing_input}.{encoded_signature}"


def decode_access_token(token: str, secret_key: str) -> dict[str, Any]:
    """Decode and verify a JWT access token."""
    try:
        encoded_header, encoded_payload, encoded_signature = token.split(".")
    except ValueError as exc:
        raise ValueError("Invalid token structure") from exc

    signing_input = f"{encoded_header}.{encoded_payload}"
    expected_signature = hmac.new(
        secret_key.encode("utf-8"),
        signing_input.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    actual_signature = _b64decode(encoded_signature)

    if not hmac.compare_digest(expected_signature, actual_signature):
        raise ValueError("Invalid token signature")

    payload = json.loads(_b64decode(encoded_payload).decode("utf-8"))
    if payload.get("type") != "access":
        raise ValueError("Invalid token type")

    exp = payload.get("exp")
    if exp is None or datetime.now(UTC).timestamp() > exp:
        raise ValueError("Token has expired")

    return payload


def _b64encode_json(data: dict[str, Any]) -> str:
    return _b64encode(
        json.dumps(data, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def _b64decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(f"{data}{padding}".encode("utf-8"))
