"""Webhook verification and durable intake (queue before acknowledging)."""
from __future__ import annotations

import hashlib
import hmac
import json
import re
from dataclasses import dataclass

from .config import Settings
from .db import DB, iso

# Only the events the workflow needs.
ALLOWED_EVENTS = {"issues", "issue_comment", "pull_request", "check_run", "check_suite", "ping"}
_DELIVERY_RE = re.compile(r"^[0-9a-fA-F-]{8,64}$")


class WebhookRejected(Exception):
    def __init__(self, status: int, msg: str):
        super().__init__(msg)
        self.status = status


@dataclass
class VerifiedEvent:
    delivery_id: str
    event: str
    action: str | None
    payload: dict


def _h(headers: dict, name: str) -> str | None:
    for k, v in headers.items():
        if k.lower() == name.lower():
            return v
    return None


def verify_webhook(settings: Settings, headers: dict, body: bytes) -> VerifiedEvent:
    """Validate signature, repository, event, and delivery identity."""
    if not settings.webhook_secret:
        raise WebhookRejected(500, "webhook secret not configured")
    if len(body) > settings.max_webhook_bytes:
        raise WebhookRejected(413, "payload too large")
    sig = _h(headers, "X-Hub-Signature-256") or ""
    if not sig.startswith("sha256="):
        raise WebhookRejected(401, "missing signature")
    expected = "sha256=" + hmac.new(settings.webhook_secret.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        raise WebhookRejected(401, "bad signature")
    event = _h(headers, "X-GitHub-Event") or ""
    if event not in ALLOWED_EVENTS:
        raise WebhookRejected(202, f"event {event!r} not subscribed")
    delivery = _h(headers, "X-GitHub-Delivery") or ""
    if not _DELIVERY_RE.match(delivery):
        raise WebhookRejected(400, "missing/invalid delivery id")
    try:
        payload = json.loads(body)
    except ValueError:
        raise WebhookRejected(400, "invalid json")
    repo = payload.get("repository") or {}
    if (repo.get("full_name") or "").lower() != settings.repo_full_name.lower():
        raise WebhookRejected(403, "repository mismatch")
    if settings.github_repo_id and str(repo.get("id")) != str(settings.github_repo_id):
        raise WebhookRejected(403, "repository id mismatch")
    inst = (payload.get("installation") or {}).get("id")
    if settings.github_installation_id and inst is not None and str(inst) != str(settings.github_installation_id):
        raise WebhookRejected(403, "installation mismatch")
    return VerifiedEvent(delivery, event, payload.get("action"), payload)


def persist_delivery(db: DB, ev: VerifiedEvent) -> bool:
    """Durably queue the event. Returns False for a duplicate delivery ID."""
    with db.tx() as c:
        if c.execute("SELECT 1 FROM webhook_deliveries WHERE delivery_id=?", (ev.delivery_id,)).fetchone():
            return False
        c.execute("INSERT INTO webhook_deliveries(delivery_id, event, action, payload, status, received_at)"
                  " VALUES (?,?,?,?, 'RECEIVED', ?)",
                  (ev.delivery_id, ev.event, ev.action, json.dumps(ev.payload), iso()))
    return True
