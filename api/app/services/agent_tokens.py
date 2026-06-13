from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db import User

TOKEN_PREFIX = "agent-v1"
ISSUER = "agent-service"
AUDIENCE = "goals"


@dataclass(frozen=True)
class AgentTokenClaims:
    subject: str
    scope: str
    expires_at: int
    audience: str


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _sign(payload: str, secret: str) -> str:
    return _b64encode(hmac.new(secret.encode("utf-8"), payload.encode("ascii"), hashlib.sha256).digest())


def encode_agent_token(
    *,
    secret: str,
    subject: str,
    scope: str,
    audience: str = AUDIENCE,
    expires_at: int | None = None,
) -> str:
    payload = {
        "iss": ISSUER,
        "aud": audience,
        "sub": subject,
        "scope": scope,
        "iat": int(time.time()),
        "exp": expires_at if expires_at is not None else int(time.time()) + 300,
    }
    encoded_payload = _b64encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    return f"{TOKEN_PREFIX}.{encoded_payload}.{_sign(encoded_payload, secret)}"


def decode_agent_token(token: str, *, secret: str, audience: str = AUDIENCE) -> AgentTokenClaims | None:
    prefix, separator, rest = token.partition(".")
    payload, separator_two, signature = rest.partition(".")
    if prefix != TOKEN_PREFIX or separator != "." or separator_two != "." or not payload or not signature:
        return None
    if not hmac.compare_digest(signature, _sign(payload, secret)):
        return None
    try:
        claims = json.loads(_b64decode(payload))
    except (ValueError, json.JSONDecodeError):
        return None
    if not isinstance(claims, dict):
        return None
    if claims.get("iss") != ISSUER or claims.get("aud") != audience:
        return None
    subject = claims.get("sub")
    scope = claims.get("scope")
    expires_at = claims.get("exp")
    if not isinstance(subject, str) or not isinstance(scope, str) or not isinstance(expires_at, int):
        return None
    if expires_at <= int(time.time()):
        return None
    return AgentTokenClaims(subject=subject, scope=scope, expires_at=expires_at, audience=audience)


def _path_after_api_prefix(request: Request, settings: Settings) -> str:
    path = request.url.path
    prefix = settings.api_v1_prefix.rstrip("/")
    if prefix and path.startswith(prefix):
        path = path.removeprefix(prefix)
    return path or "/"


def required_agent_scope(request: Request, settings: Settings) -> str | None:
    path = _path_after_api_prefix(request, settings).rstrip("/") or "/"
    method = request.method.upper()
    segments = [segment for segment in path.split("/") if segment]

    if segments == ["goals"] and method == "GET":
        return "goals.list_goals"
    if segments == ["goals"] and method == "POST":
        return "goals.create_goal"
    if len(segments) == 2 and segments[0] == "goals" and method == "PATCH":
        return "goals.update_goal"
    if (
        len(segments) == 4
        and segments[0] == "goals"
        and segments[2] == "checklist-items"
        and method == "PATCH"
    ):
        return "goals.complete_checklist_item"
    if segments == ["metrics"] and method == "GET":
        return "goals.list_metrics"
    if segments == ["metrics"] and method == "POST":
        return "goals.create_metric"
    if len(segments) == 3 and segments[0] == "metrics" and segments[2] == "entries" and method == "POST":
        return "goals.record_metric_entry"
    if segments == ["notifications"] and method == "GET":
        return "goals.list_notifications"
    if (
        len(segments) == 3
        and segments[0] == "notifications"
        and segments[2] == "complete"
        and method == "POST"
    ):
        return "goals.complete_notification"
    return None


def bearer_token(request: Request) -> str | None:
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        return auth_header[7:].strip()
    return None


def user_from_agent_token(
    *,
    request: Request,
    db: Session,
    settings: Settings,
) -> User | None:
    token = bearer_token(request)
    if not token:
        return None
    required_scope = required_agent_scope(request, settings)
    if required_scope is None or not settings.agent_integration_token_secret:
        return None
    claims = decode_agent_token(
        token,
        secret=settings.agent_integration_token_secret,
        audience=AUDIENCE,
    )
    if claims is None or claims.scope != required_scope:
        return None
    return db.scalar(
        select(User).where(
            User.identity_provider == settings.normalized_auth_base_url,
            User.external_subject == claims.subject,
        )
    )
