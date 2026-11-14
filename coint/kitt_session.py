"""Trusted founder-decision channel: the authorized KITT ChatGPT session.

G works with KITT in ChatGPT. KITT's GPT Action calls this service with a GitHub
OAuth user token obtained through the KITT OAuth App (G signs in with GitHub
inside ChatGPT). Each decision is accepted only if GitHub confirms that:

  1. the token was issued to the configured KITT OAuth App (the authorized
     KITT session integration), and
  2. the token belongs to G (FOUNDER_GITHUB_USERNAME / FOUNDER_GITHUB_USER_ID).

The action is marked consequential, so ChatGPT shows G the exact payload
(project, cycle, version, decision) and requires G to confirm before it is sent.

A GitHub comment, including one written by KITT, is never approval evidence.
If this integration is not configured, founder decisions are refused and
reported as a blocker; there is no fallback path.
"""
from __future__ import annotations

import base64
import hashlib
import json
import urllib.error
import urllib.request
from dataclasses import dataclass

from .config import Settings
from .errors import AuthError, PermissionDenied, TransientError


class SessionUnavailable(Exception):
    """Trusted session integration is not configured: report as a blocker."""


@dataclass
class Attestation:
    github_login: str
    github_user_id: int
    oauth_client_id: str
    token_fingerprint: str  # sha256 of the token; the token itself is never stored


def token_fingerprint(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class KittSessionVerifier:
    def __init__(self, settings: Settings, timeout: int = 15):
        self.s = settings
        self.timeout = timeout

    def available(self) -> bool:
        return bool(self.s.kitt_oauth_client_id and self.s.kitt_oauth_client_secret)

    def _check_token(self, token: str) -> dict:
        """GitHub: POST /applications/{client_id}/token (app basic auth).
        Returns 404 unless the token was issued to THIS OAuth app."""
        cid, secret = self.s.kitt_oauth_client_id, self.s.kitt_oauth_client_secret
        req = urllib.request.Request(f"https://api.github.com/applications/{cid}/token", method="POST",
                                     data=json.dumps({"access_token": token}).encode())
        req.add_header("Authorization", "Basic " + base64.b64encode(f"{cid}:{secret}".encode()).decode())
        req.add_header("Accept", "application/vnd.github+json")
        req.add_header("X-GitHub-Api-Version", "2022-11-28")
        req.add_header("User-Agent", "co-intelligence-automation")
        req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code in (404, 422):
                raise AuthError("token was not issued to the authorized KITT session app, or is revoked")
            if e.code == 401:
                raise SessionUnavailable("KITT OAuth app credentials rejected by GitHub")
            raise TransientError(f"GitHub token check {e.code}")
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            raise TransientError(f"GitHub token check unreachable: {e}")

    def verify_founder(self, token: str) -> Attestation:
        if not self.available():
            raise SessionUnavailable("KITT session integration not configured "
                                     "(KITT_OAUTH_CLIENT_ID / KITT_OAUTH_CLIENT_SECRET)")
        if not token:
            raise AuthError("missing bearer token")
        info = self._check_token(token)
        app_cid = (info.get("app") or {}).get("client_id")
        user = info.get("user") or {}
        if app_cid != self.s.kitt_oauth_client_id:
            raise AuthError("token not issued to the authorized KITT session app")
        login = user.get("login") or ""
        if login.lower() != self.s.founder_login.lower():
            raise PermissionDenied(f"session user @{login} is not the configured founder")
        if self.s.founder_user_id and str(user.get("id")) != str(self.s.founder_user_id):
            raise PermissionDenied("session user id does not match FOUNDER_GITHUB_USER_ID")
        return Attestation(login, int(user.get("id") or 0), app_cid, token_fingerprint(token))


DECISION_TYPES = {
    "project_start": "project start",
    "initial_approve": "initial approve",
    "initial_changes": "initial changes",
    "delivery_changes": "delivery changes",
    "delivery_approve_close": "delivery approve-close",
    "project_pause": "project pause",
    "project_resume": "project resume",
}


def openapi_spec(base_url: str) -> dict:
    """OpenAPI document for KITT's GPT Action (OAuth: GitHub, scope read:user)."""
    decision = {
        "type": "object",
        "required": ["decision_id", "decision_type", "founder_statement"],
        "properties": {
            "decision_id": {"type": "string", "description": "New UUID per decision (idempotency key)."},
            "decision_type": {"type": "string", "enum": sorted(DECISION_TYPES)},
            "project_id": {"type": "string"},
            "cycle": {"type": "integer", "minimum": 1},
            "sha": {"type": "string", "description": "Exact 40-char document or delivery SHA G reviewed."},
            "founder_statement": {"type": "string", "description": "G's decision in G's own words, verbatim."},
            "brief": {"type": "object", "description": "project_start only: confirmed brief incl. confirmed=true"},
            "issue_number": {"type": "integer", "description": "project_start: existing tracking issue (optional)"},
            "changes": {"type": "array", "items": {"type": "string"}},
            "route": {"type": "string", "enum": ["documents", "development"]},
            "decisions": {"type": "array", "items": {"type": "string"}},
        },
    }
    return {
        "openapi": "3.1.0",
        "info": {"title": "Co-Intelligence founder decisions (KITT)", "version": "1"},
        "servers": [{"url": base_url}],
        "paths": {
            "/kitt/pending": {"get": {
                "operationId": "listPendingFounderReviews",
                "summary": "Founder questions and review packages awaiting G",
                "responses": {"200": {"description": "pending items"}}}},
            "/kitt/founder-decision": {"post": {
                "operationId": "submitFounderDecision",
                "summary": "Submit an explicit decision G made in this session",
                "x-openai-isConsequential": True,
                "requestBody": {"required": True, "content": {"application/json": {"schema": decision}}},
                "responses": {"200": {"description": "accepted"}, "400": {"description": "rejected"},
                              "401": {"description": "not an authorized session"},
                              "403": {"description": "not the founder"},
                              "503": {"description": "integration unavailable"}}}},
        },
        "components": {"securitySchemes": {"github": {"type": "oauth2", "flows": {"authorizationCode": {
            "authorizationUrl": "https://github.com/login/oauth/authorize",
            "tokenUrl": "https://github.com/login/oauth/access_token",
            "scopes": {"read:user": "Identify G"}}}}}},
        "security": [{"github": ["read:user"]}],
    }
