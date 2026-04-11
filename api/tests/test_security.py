from __future__ import annotations

from app.core.security import BCRYPT_ROUNDS, hash_password, verify_password


def test_hash_password_uses_bcrypt() -> None:
    hashed_password = hash_password("supersafepassword")

    assert hashed_password.startswith(f"$2b${BCRYPT_ROUNDS:02d}$")
    assert verify_password("supersafepassword", hashed_password) is True
    assert verify_password("wrongpassword", hashed_password) is False
