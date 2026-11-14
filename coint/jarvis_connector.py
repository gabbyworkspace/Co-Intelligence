"""JARVIS chat connector: a remote MCP server with GitHub sign-in.

Lets the JARVIS chat (a Claude chat with this connector added) present final
reviews to G and submit G's explicit APPROVE AND CLOSE / REQUEST CHANGES, with
G's identity proven by GitHub — not by anything an agent says.

OAuth: this service is the authorization server the chat client discovers
(RFC 9728 protected-resource metadata -> RFC 8414 AS metadata -> RFC 7591
dynamic client registration -> authorization code + PKCE S256). It delegates
the actual sign-in to GitHub using the JARVIS OAuth App, refuses to finish the
connection unless the GitHub user is G, and hands the chat client the GitHub
token. Every MCP call re-verifies that token with GitHub (issued to the JARVIS
OAuth App, user == founder) through SessionVerifier("jarvis_session").

MCP: Streamable HTTP, JSON responses (no SSE), tools:
  list_pending_final_reviews   read-only
  submit_founder_decision      destructive; the chat asks G to confirm the call
"""
from __future__ import annotations

import base64
import hashlib
import json
import secrets
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

from .audit import record_audit_event
from .errors import AuthError, PermissionDenied, TransientError
from .kitt_session import CHANNEL_DECISIONS, SessionUnavailable

PROTOCOL_VERSIONS = ("2025-06-18", "2025-03-26", "2024-11-05")
DEFAULT_REDIRECTS = ("https://claude.ai/api/mcp/auth_callback", "https://claude.com/api/mcp/auth_callback")
MCP_PATH = "/mcp/jarvis"
PENDING_TTL = 600
CODE_TTL = 300

TOOLS = [
    {
        "name": "list_pending_final_reviews",
        "title": "List final reviews awaiting G",
        "description": ("Final delivery reviews waiting for G in the JARVIS chat: project ID, cycle, exact delivery "
                        "SHA and tag, completion summary, verification results, limitations, KITT's review, and the "
                        "review-package email status (with the exact chat confirmation to use only when SENT)."),
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
        "annotations": {"readOnlyHint": True, "openWorldHint": False},
    },
    {
        "name": "submit_founder_decision",
        "title": "Submit G's explicit decision",
        "description": ("Submit a decision G explicitly made in this chat. Final review: APPROVE AND CLOSE "
                        "(delivery_approve_close) or REQUEST CHANGES (delivery_changes, with changes and route). "
                        "Only call after G states the decision; put G's words verbatim in founder_statement and use "
                        "the exact project_id, cycle and 40-char sha from list_pending_final_reviews. KITT records "
                        "the decision on GitHub before it takes effect."),
        "inputSchema": {
            "type": "object",
            "required": ["decision_id", "decision_type", "project_id", "founder_statement"],
            "properties": {
                "decision_id": {"type": "string", "description": "New UUID for this decision"},
                "decision_type": {"type": "string", "enum": sorted(CHANNEL_DECISIONS["jarvis_session"])},
                "project_id": {"type": "string"},
                "cycle": {"type": "integer", "minimum": 1},
                "sha": {"type": "string", "description": "Exact 40-char delivery SHA G reviewed"},
                "founder_statement": {"type": "string", "description": "G's decision, verbatim"},
                "changes": {"type": "array", "items": {"type": "string"}},
                "route": {"type": "string", "enum": ["documents", "development"]},
                "decisions": {"type": "array", "items": {"type": "string"}},
            },
            "additionalProperties": False,
        },
        "annotations": {"destructiveHint": True, "idempotentHint": True, "openWorldHint": False},
    },
]


class Response:
    def __init__(self, status: int, body=None, headers: dict | None = None, content_type: str = "application/json"):
        self.status, self.body, self.headers, self.content_type = status, body, headers or {}, content_type


def _b64url_sha256(verifier: str) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()


class JarvisConnector:
    def __init__(self, engine, base_url: str, *, redirect_allowlist=None, exchange_code=None):
        self.engine = engine
        self.s = engine.s
        self.base = base_url.rstrip("/")
        self.redirects = tuple(redirect_allowlist or DEFAULT_REDIRECTS)
        self._exchange = exchange_code or self._github_exchange
        self._lock = threading.Lock()
        self._pending: dict[str, dict] = {}   # github state -> authorize request (memory only)
        self._codes: dict[str, dict] = {}     # our auth code -> token + PKCE binding (memory only)

    # ------------------------------------------------------------ discovery
    def protected_resource(self) -> Response:
        return Response(200, {"resource": self.base + MCP_PATH, "authorization_servers": [self.base],
                              "scopes_supported": ["read:user"], "bearer_methods_supported": ["header"],
                              "resource_name": "Co-Intelligence JARVIS final review"})

    def authorization_server(self) -> Response:
        return Response(200, {
            "issuer": self.base,
            "authorization_endpoint": self.base + "/oauth/authorize",
            "token_endpoint": self.base + "/oauth/token",
            "registration_endpoint": self.base + "/oauth/register",
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code"],
            "code_challenge_methods_supported": ["S256"],
            "token_endpoint_auth_methods_supported": ["none"],
            "scopes_supported": ["read:user"],
        })

    def _unauthorized(self, msg: str) -> Response:
        return Response(401, {"error": "unauthorized", "error_description": msg}, {
            "WWW-Authenticate": f'Bearer resource_metadata="{self.base}/.well-known/oauth-protected-resource{MCP_PATH}"'})

    # ------------------------------------------------------------ registration
    def register(self, body: dict) -> Response:
        uris = body.get("redirect_uris")
        if not isinstance(uris, list) or not uris or any(u not in self.redirects for u in uris):
            return Response(400, {"error": "invalid_redirect_uri",
                                  "error_description": f"redirect_uris must be within {list(self.redirects)}"})
        client_id = "jc_" + secrets.token_urlsafe(16)
        with self.engine.db.tx() as c:
            c.execute("INSERT INTO oauth_clients(client_id, redirect_uris, client_name, created_at)"
                      " VALUES (?,?,?,datetime('now'))", (client_id, json.dumps(uris), str(body.get("client_name", ""))[:200]))
        return Response(201, {"client_id": client_id, "redirect_uris": uris, "token_endpoint_auth_method": "none",
                              "grant_types": ["authorization_code"], "response_types": ["code"],
                              "client_name": body.get("client_name", "")})

    def _client(self, client_id: str):
        return self.engine.db.one("SELECT * FROM oauth_clients WHERE client_id=?", client_id or "")

    # ------------------------------------------------------------ authorize
    def authorize(self, q: dict) -> Response:
        if not self.engine.jarvis_verifier.available():
            return Response(503, {"error": "temporarily_unavailable",
                                  "error_description": "JARVIS session OAuth app not configured (blocker)"})
        client = self._client(q.get("client_id"))
        redirect = q.get("redirect_uri", "")
        if not client or redirect not in json.loads(client["redirect_uris"]):
            return Response(400, {"error": "invalid_request", "error_description": "unknown client or redirect_uri"})
        if q.get("response_type") != "code" or q.get("code_challenge_method") != "S256" or not q.get("code_challenge"):
            return self._redirect_error(redirect, q.get("state"), "invalid_request", "PKCE S256 and code required")
        gh_state = secrets.token_urlsafe(24)
        with self._lock:
            self._gc()
            self._pending[gh_state] = {"client_id": client["client_id"], "redirect_uri": redirect,
                                       "code_challenge": q["code_challenge"], "state": q.get("state"),
                                       "at": time.time()}
        url = "https://github.com/login/oauth/authorize?" + urllib.parse.urlencode({
            "client_id": self.s.jarvis_oauth_client_id, "redirect_uri": self.base + "/oauth/callback",
            "scope": "read:user", "state": gh_state, "allow_signup": "false"})
        return Response(302, None, {"Location": url})

    def callback(self, q: dict) -> Response:
        with self._lock:
            pend = self._pending.pop(q.get("state", ""), None)
        if not pend or time.time() - pend["at"] > PENDING_TTL:
            return Response(400, {"error": "invalid_request", "error_description": "unknown or expired sign-in"})
        if q.get("error") or not q.get("code"):
            return self._redirect_error(pend["redirect_uri"], pend["state"], "access_denied", "GitHub sign-in declined")
        try:
            token = self._exchange(q["code"])
            att = self.engine.jarvis_verifier.verify_founder(token)
        except PermissionDenied as e:
            record_audit_event(self.engine.db, actor="unknown", action="jarvis_connector.connect", outcome="denied",
                               detail={"reason": str(e)})
            return self._redirect_error(pend["redirect_uri"], pend["state"], "access_denied",
                                        "Only the configured founder can connect the JARVIS decision connector")
        except (AuthError, SessionUnavailable, TransientError) as e:
            return self._redirect_error(pend["redirect_uri"], pend["state"], "server_error", str(e)[:200])
        code = secrets.token_urlsafe(32)
        with self._lock:
            self._codes[code] = {**pend, "token": token, "at": time.time()}
        record_audit_event(self.engine.db, actor=att.github_login, action="jarvis_connector.connect",
                           outcome="authorized", detail={"client_id": pend["client_id"]})
        sep = "&" if "?" in pend["redirect_uri"] else "?"
        params = {"code": code} | ({"state": pend["state"]} if pend["state"] else {})
        return Response(302, None, {"Location": pend["redirect_uri"] + sep + urllib.parse.urlencode(params)})

    def token(self, form: dict) -> Response:
        if form.get("grant_type") != "authorization_code":
            return Response(400, {"error": "unsupported_grant_type"})
        with self._lock:
            rec = self._codes.pop(form.get("code", ""), None)   # one-time use
        if not rec or time.time() - rec["at"] > CODE_TTL:
            return Response(400, {"error": "invalid_grant"})
        if form.get("client_id") != rec["client_id"] or form.get("redirect_uri") != rec["redirect_uri"]:
            return Response(400, {"error": "invalid_grant", "error_description": "client/redirect mismatch"})
        if _b64url_sha256(form.get("code_verifier", "")) != rec["code_challenge"]:
            return Response(400, {"error": "invalid_grant", "error_description": "PKCE verification failed"})
        return Response(200, {"access_token": rec["token"], "token_type": "Bearer", "scope": "read:user"},
                        {"Cache-Control": "no-store"})

    def _redirect_error(self, redirect, state, err, desc) -> Response:
        params = {"error": err, "error_description": desc} | ({"state": state} if state else {})
        sep = "&" if "?" in redirect else "?"
        return Response(302, None, {"Location": redirect + sep + urllib.parse.urlencode(params)})

    def _gc(self):
        now = time.time()
        for d, ttl in ((self._pending, PENDING_TTL), (self._codes, CODE_TTL)):
            for k in [k for k, v in d.items() if now - v["at"] > ttl]:
                d.pop(k, None)

    def _github_exchange(self, code: str) -> str:
        req = urllib.request.Request("https://github.com/login/oauth/access_token", method="POST",
                                     data=urllib.parse.urlencode({
                                         "client_id": self.s.jarvis_oauth_client_id,
                                         "client_secret": self.s.jarvis_oauth_client_secret,
                                         "code": code, "redirect_uri": self.base + "/oauth/callback"}).encode())
        req.add_header("Accept", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
        except (urllib.error.URLError, TimeoutError) as e:
            raise TransientError(f"GitHub token exchange failed: {e}")
        if "access_token" not in data:
            raise AuthError(f"GitHub token exchange: {data.get('error', 'no token')}")
        return data["access_token"]

    # ------------------------------------------------------------ MCP
    def mcp(self, bearer: str, body) -> Response:
        try:
            att = self.engine.jarvis_verifier.verify_founder(bearer)
        except SessionUnavailable as e:
            return Response(503, {"error": "founder decision channel unavailable", "blocker": str(e)})
        except PermissionDenied as e:
            return Response(403, {"error": str(e)})
        except AuthError as e:
            return self._unauthorized(str(e))
        except TransientError as e:
            return Response(503, {"error": f"temporarily unable to verify session: {e}"})
        if isinstance(body, list):
            out = [r for r in (self._rpc(att, m) for m in body) if r is not None]
            return Response(200, out) if out else Response(202, None)
        res = self._rpc(att, body)
        return Response(200, res) if res is not None else Response(202, None)

    def _rpc(self, att, msg):
        if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0" or "method" not in msg:
            return {"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "invalid request"}}
        mid, method, params = msg.get("id"), msg["method"], msg.get("params") or {}
        if mid is None:  # notification (e.g. notifications/initialized)
            return None

        def ok(result):
            return {"jsonrpc": "2.0", "id": mid, "result": result}

        if method == "initialize":
            requested = params.get("protocolVersion")
            return ok({"protocolVersion": requested if requested in PROTOCOL_VERSIONS else PROTOCOL_VERSIONS[0],
                       "capabilities": {"tools": {"listChanged": False}},
                       "serverInfo": {"name": "co-intelligence-jarvis", "title": "Co-Intelligence JARVIS",
                                      "version": "1.0"},
                       "instructions": ("Use list_pending_final_reviews to present the exact delivery version to "
                                        "G. Submit only G's explicit APPROVE AND CLOSE or REQUEST CHANGES with "
                                        "submit_founder_decision. Never infer approval.")})
        if method == "ping":
            return ok({})
        if method == "tools/list":
            return ok({"tools": TOOLS})
        if method == "tools/call":
            name, args = params.get("name"), params.get("arguments") or {}
            if name == "list_pending_final_reviews":
                data = {"pending": self.engine.pending_reviews(channel="jarvis_session")}
                return ok(self._tool_result(data, False))
            if name == "submit_founder_decision":
                res = self.engine.founder_decision(att, dict(args))
                status = res.pop("status")
                return ok(self._tool_result(res, status != 200))
            return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32602, "message": f"unknown tool {name}"}}
        return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": f"method not found: {method}"}}

    @staticmethod
    def _tool_result(data: dict, is_error: bool) -> dict:
        return {"content": [{"type": "text", "text": json.dumps(data, indent=2, default=str)}],
                "structuredContent": data, "isError": is_error}
