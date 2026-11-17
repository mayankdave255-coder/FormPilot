"""Small cookie-based account system for the FormPilot demo deployment."""
from __future__ import annotations

import hashlib
import os
import re
import secrets
import time
import uuid
from pathlib import Path
from typing import Any

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy import delete, insert, select, update
from sqlalchemy.exc import IntegrityError

from . import database

_serializer: URLSafeTimedSerializer | None = None
TOKEN_MAX_AGE = 60 * 60 * 24 * 14
PASSWORD_ITERATIONS = 310_000


def init_auth(data_dir: Path) -> None:
    global _serializer
    data_dir.mkdir(parents=True, exist_ok=True)
    app_env = os.getenv("APP_ENV", "development").lower()
    key = os.getenv("AUTH_SECRET_KEY", "")
    if app_env == "production" and len(key) < 32:
        raise RuntimeError("Set AUTH_SECRET_KEY to a random value of at least 32 characters in production.")
    if not key:
        key = secrets.token_urlsafe(48)
        print("[formpilot] WARNING: using an ephemeral auth signing key. Set AUTH_SECRET_KEY to keep logins valid across restarts.")
    _serializer = URLSafeTimedSerializer(key, salt="formpilot-auth-v1")
    database.init_database(data_dir)


def normalize_email(email: str) -> str:
    return email.strip().lower()


def validate_email(email: str) -> bool:
    return len(email) <= 254 and bool(re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email))


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS)
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${salt.hex()}${derived.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, rounds, salt_hex, expected = stored.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(rounds)).hex()
        return secrets.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def public_user(row: Any) -> dict[str, str]:
    return {"id": row["id"], "email": row["email"], "name": row["name"]}


def create_user(email: str, name: str, password: str) -> dict[str, str]:
    if not validate_email(email):
        raise ValueError("Enter a valid email address.")
    email = normalize_email(email)
    name = " ".join(name.strip().split())
    if len(name) < 2 or len(name) > 80:
        raise ValueError("Enter a name between 2 and 80 characters.")
    if len(password) < 12 or len(password) > 128:
        raise ValueError("Use a password between 12 and 128 characters.")
    user = {"id": uuid.uuid4().hex, "email": email, "name": name}
    try:
        with database.transaction() as db:
            db.execute(insert(database.users).values(
                id=user["id"], email=email, name=name,
                password_hash=hash_password(password), created_at=time.time(),
            ))
    except IntegrityError as exc:
        raise ValueError("An account with this email already exists. Sign in instead.") from exc
    return user


def get_user(user_id: str) -> dict[str, str] | None:
    with database.transaction() as db:
        row = db.execute(
            select(database.users.c.id, database.users.c.email, database.users.c.name)
            .where(database.users.c.id == user_id)
        ).mappings().first()
    return public_user(row) if row else None


def authenticate(email: str, password: str) -> dict[str, str] | None:
    email = normalize_email(email)
    now = time.time()
    with database.transaction() as db:
        attempt = db.execute(
            select(database.login_attempts).where(database.login_attempts.c.email == email)
        ).mappings().first()
        if attempt and attempt["blocked_until"] > now:
            raise PermissionError("Too many sign-in attempts. Wait 15 minutes and try again.")
        row = db.execute(
            select(database.users.c.id, database.users.c.email, database.users.c.name, database.users.c.password_hash)
            .where(database.users.c.email == email)
        ).mappings().first()
        valid = bool(row and verify_password(password, row["password_hash"]))
        if valid:
            db.execute(delete(database.login_attempts).where(database.login_attempts.c.email == email))
            return public_user(row)
        if attempt and now - attempt["first_attempt"] < 900:
            attempts = attempt["attempts"] + 1
            first = attempt["first_attempt"]
        else:
            attempts, first = 1, now
        blocked_until = now + 900 if attempts >= 5 else 0
        values = {"email": email, "attempts": attempts, "first_attempt": first, "blocked_until": blocked_until}
        if attempt:
            db.execute(update(database.login_attempts).where(database.login_attempts.c.email == email).values(**values))
        else:
            db.execute(insert(database.login_attempts).values(**values))
    if blocked_until:
        raise PermissionError("Too many sign-in attempts. Wait 15 minutes and try again.")
    return None


def issue_token(user_id: str) -> str:
    if _serializer is None:
        raise RuntimeError("Auth has not been initialized.")
    return _serializer.dumps({"uid": user_id})


def user_from_token(token: str | None) -> dict[str, str] | None:
    if not token or _serializer is None:
        return None
    try:
        payload = _serializer.loads(token, max_age=TOKEN_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None
    user_id = payload.get("uid") if isinstance(payload, dict) else None
    return get_user(user_id) if user_id else None


def signup_enabled() -> bool:
    return os.getenv("ALLOW_SIGNUP", "true").strip().lower() in {"1", "true", "yes", "on"}
