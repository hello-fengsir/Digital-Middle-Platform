import base64
import binascii
import hashlib
import hmac
import json
import time
from datetime import UTC, datetime

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import ApiClient


def hash_api_key(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode((data + padding).encode("ascii"))


def verify_admin_password(password: str) -> bool:
    stored = settings.admin_password_hash or ""
    if not stored.startswith("sha256:"):
        return False
    expected = stored.split(":", 1)[1]
    actual = hashlib.sha256(password.encode("utf-8")).hexdigest()
    return hmac.compare_digest(actual, expected)


def create_admin_session_token(username: str) -> tuple[str, int]:
    if not settings.admin_session_secret:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Admin session secret is not configured")
    expires_at = int(time.time()) + int(settings.admin_session_ttl_seconds)
    payload_b64 = _b64url_encode(json.dumps({"sub": username, "exp": expires_at}, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    signature = hmac.new(settings.admin_session_secret.encode("utf-8"), payload_b64.encode("ascii"), hashlib.sha256).digest()
    return f"{payload_b64}.{_b64url_encode(signature)}", expires_at


def parse_admin_session_token(token: str) -> dict:
    try:
        payload_b64, signature_b64 = token.split(".", 1)
        expected = hmac.new(settings.admin_session_secret.encode("utf-8"), payload_b64.encode("ascii"), hashlib.sha256).digest()
        actual = _b64url_decode(signature_b64)
        if not hmac.compare_digest(actual, expected):
            raise ValueError("bad signature")
        payload = json.loads(_b64url_decode(payload_b64))
    except (ValueError, json.JSONDecodeError, binascii.Error):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin session")
    if payload.get("sub") != settings.admin_username or int(payload.get("exp", 0)) <= int(time.time()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin session")
    return payload


def format_expires_at(timestamp: int) -> str:
    return datetime.fromtimestamp(timestamp, UTC).isoformat()


def require_admin_session(authorization: str | None = Header(default=None, alias="Authorization")) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin login required")
    return parse_admin_session_token(authorization.removeprefix("Bearer ").strip())


def ensure_default_api_client(db: Session) -> None:
    key_hash = hash_api_key(settings.api_key)
    existing = db.scalar(select(ApiClient).where(ApiClient.name == "default"))
    if existing:
        existing.key_hash = key_hash
        existing.is_active = True
    else:
        db.add(ApiClient(name="default", key_hash=key_hash, is_active=True))
    db.commit()


def require_api_client(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    db: Session = Depends(get_db),
) -> ApiClient:
    if not x_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="X-API-Key required")
    key_hash = hash_api_key(x_api_key)
    clients = db.scalars(select(ApiClient).where(ApiClient.is_active.is_(True))).all()
    for client in clients:
        if hmac.compare_digest(client.key_hash, key_hash):
            return client
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid API key")
