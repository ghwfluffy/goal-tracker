from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from hmac import compare_digest

import bcrypt

BCRYPT_ROUNDS = 13
LEGACY_PASSWORD_HASH_ITERATIONS = 600_000
LEGACY_PASSWORD_HASH_NAME = "pbkdf2_sha256"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(rounds=BCRYPT_ROUNDS),
    ).decode("ascii")


def is_bcrypt_hash(stored_password_hash: str) -> bool:
    return stored_password_hash.startswith(("$2a$", "$2b$", "$2y$"))


def password_hash_needs_upgrade(stored_password_hash: str) -> bool:
    return not is_bcrypt_hash(stored_password_hash)


def verify_legacy_pbkdf2_password(password: str, stored_password_hash: str) -> bool:
    try:
        algorithm, iterations, encoded_salt, encoded_hash = stored_password_hash.split(
            "$", maxsplit=3
        )
    except ValueError:
        return False

    if algorithm != LEGACY_PASSWORD_HASH_NAME:
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


def verify_password(password: str, stored_password_hash: str) -> bool:
    if is_bcrypt_hash(stored_password_hash):
        try:
            return bcrypt.checkpw(
                password.encode("utf-8"),
                stored_password_hash.encode("ascii"),
            )
        except ValueError:
            return False

    return verify_legacy_pbkdf2_password(password, stored_password_hash)


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
