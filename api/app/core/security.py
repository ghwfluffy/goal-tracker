from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from hmac import compare_digest

PASSWORD_HASH_ITERATIONS = 600_000
PASSWORD_HASH_NAME = "pbkdf2_sha256"


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    derived_key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_HASH_ITERATIONS,
    )
    encoded_salt = base64.b64encode(salt).decode("ascii")
    encoded_hash = base64.b64encode(derived_key).decode("ascii")
    return f"{PASSWORD_HASH_NAME}${PASSWORD_HASH_ITERATIONS}${encoded_salt}${encoded_hash}"


def verify_password(password: str, stored_password_hash: str) -> bool:
    try:
        algorithm, iterations, encoded_salt, encoded_hash = stored_password_hash.split("$", maxsplit=3)
    except ValueError:
        return False

    if algorithm != PASSWORD_HASH_NAME:
        return False

    salt = base64.b64decode(encoded_salt.encode("ascii"))
    expected_hash = base64.b64decode(encoded_hash.encode("ascii"))
    candidate_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        int(iterations),
    )
    return compare_digest(candidate_hash, expected_hash)


def generate_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def sign_session_token(token: str, session_key: str) -> str:
    return hmac.new(
        key=session_key.encode("utf-8"),
        msg=token.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()


def encode_session_cookie(token: str, session_key: str) -> str:
    signature = sign_session_token(token, session_key)
    return f"{token}.{signature}"


def decode_session_cookie(cookie_value: str, session_key: str) -> str | None:
    token, separator, signature = cookie_value.partition(".")
    if separator == "":
        return None

    expected_signature = sign_session_token(token, session_key)
    if not compare_digest(signature, expected_signature):
        return None

    return token
