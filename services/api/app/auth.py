from __future__ import annotations

import base64
import hashlib
import hmac
import secrets

from app.database.store import get_store


PBKDF2_ITERATIONS = 210_000


def hash_password(password: str, *, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return "pbkdf2_sha256${}${}${}".format(
        PBKDF2_ITERATIONS,
        base64.b64encode(salt).decode("ascii"),
        base64.b64encode(digest).decode("ascii"),
    )


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, raw_salt, raw_digest = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        salt = base64.b64decode(raw_salt.encode("ascii"))
        expected = base64.b64decode(raw_digest.encode("ascii"))
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations))
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False


def issue_session(user_id: str, student_id: str, course_id: str) -> dict[str, str]:
    token = "lf_" + secrets.token_urlsafe(32)
    return get_store().create_auth_session(token=token, user_id=user_id, student_id=student_id, course_id=course_id)
