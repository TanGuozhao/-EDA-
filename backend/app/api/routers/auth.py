import json
import os
import base64
import hashlib
import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy.orm import Session

from app.adapters.db.mysql.database import get_db
from app.adapters.db.mysql.models import User, UserSession

router = APIRouter()

SESSION_TTL_HOURS = 8
PBKDF2_ITERATIONS = 120_000
SALT_BYTES = 16
KEY_BYTES = 32
AUTH_REDIS_NAMESPACE = "auth:v1"


class RegisterRequest(BaseModel):
    account: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8, max_length=128)
    user_name: str | None = Field(default=None, max_length=100)


class LoginRequest(BaseModel):
    account: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1, max_length=128)


def _normalize_account(account: str) -> str:
    return account.strip().lower()


def _redis_client() -> Redis:
    return Redis.from_url(
        os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0"),
        decode_responses=True,
        socket_connect_timeout=1,
        socket_timeout=1,
    )


def _session_cache_key(session_key: str) -> str:
    return f"{AUTH_REDIS_NAMESPACE}:session:{session_key}"


def _public_user(user: User) -> dict:
    return {
        "userId": user.id,
        "account": user.username,
        "userName": user.display_name or user.username,
        "status": user.status or "active",
        "createdAt": user.created_at,
        "lastLoginAt": user.last_login_at,
    }


def _hash_password(raw_password: str) -> str:
    salt = secrets.token_bytes(SALT_BYTES)
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        raw_password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
        dklen=KEY_BYTES,
    )
    return "pbkdf2${}${}${}".format(
        PBKDF2_ITERATIONS,
        base64.b64encode(salt).decode("ascii"),
        base64.b64encode(derived).decode("ascii"),
    )


def _password_matches(raw_password: str, encoded_password: str | None) -> bool:
    if not encoded_password or not encoded_password.startswith("pbkdf2$"):
        return False
    try:
        _, iterations_text, salt_text, expected_text = encoded_password.split("$", 3)
        salt = base64.b64decode(salt_text.encode("ascii"))
        expected = base64.b64decode(expected_text.encode("ascii"))
        actual = hashlib.pbkdf2_hmac(
            "sha256",
            raw_password.encode("utf-8"),
            salt,
            int(iterations_text),
            dklen=len(expected),
        )
        return secrets.compare_digest(expected, actual)
    except Exception:
        return False


def _issue_session(db: Session, user: User) -> UserSession:
    session = UserSession(
        session_key="SESSION-" + secrets.token_urlsafe(32),
        user_id=user.id,
        issued_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(hours=SESSION_TTL_HOURS),
    )
    db.add(session)
    return session


def _cache_session(session: UserSession) -> None:
    ttl_seconds = max(1, int((session.expires_at - datetime.utcnow()).total_seconds()))
    payload = {
        "sessionKey": session.session_key,
        "userId": session.user_id,
        "expiresAt": session.expires_at.isoformat(),
    }
    _redis_client().set(
        _session_cache_key(session.session_key),
        json.dumps(payload, separators=(",", ":")),
        ex=ttl_seconds,
    )


def _load_session_from_cache(session_key: str) -> tuple[int, datetime] | None:
    payload = _redis_client().get(_session_cache_key(session_key))
    if payload is None:
        return None
    try:
        data = json.loads(payload)
        return int(data["userId"]), datetime.fromisoformat(data["expiresAt"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        _redis_client().delete(_session_cache_key(session_key))
        return None


def _delete_cached_session(session_key: str) -> None:
    _redis_client().delete(_session_cache_key(session_key))


def get_current_user(
    x_session_key: str | None = Header(default=None, alias="X-Session-Key"),
    db: Session = Depends(get_db),
) -> User:
    if not x_session_key:
        raise HTTPException(status_code=401, detail="login required")

    session_key = x_session_key.strip()
    try:
        cached_session = _load_session_from_cache(session_key)
    except RedisError as error:
        raise HTTPException(status_code=503, detail="auth cache is unavailable") from error

    if cached_session is not None:
        user_id, expires_at = cached_session
        if expires_at < datetime.utcnow():
            try:
                _delete_cached_session(session_key)
            except RedisError as error:
                raise HTTPException(status_code=503, detail="auth cache is unavailable") from error
            raise HTTPException(status_code=401, detail="session expired")
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=401, detail="invalid session")
        if user.status != "active":
            raise HTTPException(status_code=403, detail="account disabled")
        return user

    session = (
        db.query(UserSession)
        .filter(UserSession.session_key == session_key)
        .first()
    )
    if not session:
        raise HTTPException(status_code=401, detail="invalid session")
    if session.expires_at < datetime.utcnow():
        db.delete(session)
        db.commit()
        try:
            _delete_cached_session(session_key)
        except RedisError as error:
            raise HTTPException(status_code=503, detail="auth cache is unavailable") from error
        raise HTTPException(status_code=401, detail="session expired")

    user = db.query(User).filter(User.id == session.user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="invalid session")
    if user.status != "active":
        raise HTTPException(status_code=403, detail="account disabled")
    try:
        _cache_session(session)
    except RedisError as error:
        raise HTTPException(status_code=503, detail="auth cache is unavailable") from error
    return user


@router.post("/register")
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    account = _normalize_account(request.account)
    if not account:
        raise HTTPException(status_code=400, detail="account is required")
    if any(ch.isspace() for ch in account):
        raise HTTPException(status_code=400, detail="account cannot contain spaces")

    exists = db.query(User).filter(User.username == account).first()
    if exists:
        raise HTTPException(status_code=409, detail="account already exists")

    user = User(
        username=account,
        display_name=(request.user_name or account).strip(),
        password_hash=_hash_password(request.password),
        status="active",
    )
    db.add(user)
    db.flush()
    session = _issue_session(db, user)
    try:
        _cache_session(session)
    except RedisError as error:
        db.rollback()
        raise HTTPException(status_code=503, detail="auth cache is unavailable") from error
    db.commit()
    db.refresh(user)

    return {
        "sessionKey": session.session_key,
        "expireTime": session.expires_at,
        "user": _public_user(user),
    }


@router.post("/login")
def login(request: LoginRequest, db: Session = Depends(get_db)):
    account = _normalize_account(request.account)
    user = db.query(User).filter(User.username == account).first()
    if not user or not _password_matches(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="invalid account or password")
    if user.status != "active":
        raise HTTPException(status_code=403, detail="account disabled")

    user.last_login_at = datetime.utcnow()
    session = _issue_session(db, user)
    try:
        _cache_session(session)
    except RedisError as error:
        db.rollback()
        raise HTTPException(status_code=503, detail="auth cache is unavailable") from error
    db.commit()
    db.refresh(user)

    return {
        "sessionKey": session.session_key,
        "expireTime": session.expires_at,
        "user": _public_user(user),
    }


@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return {"user": _public_user(current_user)}


@router.post("/logout")
def logout(
    x_session_key: str | None = Header(default=None, alias="X-Session-Key"),
    db: Session = Depends(get_db),
):
    if x_session_key:
        session_key = x_session_key.strip()
        try:
            _delete_cached_session(session_key)
        except RedisError as error:
            raise HTTPException(status_code=503, detail="auth cache is unavailable") from error
        session = (
            db.query(UserSession)
            .filter(UserSession.session_key == session_key)
            .first()
        )
        if session:
            db.delete(session)
            db.commit()
    return {"message": "logout success"}
