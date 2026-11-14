"""JARVIS chat connector: OAuth (discovery, DCR, PKCE, GitHub sign-in) + MCP tools."""
import base64
import hashlib
import json
import threading
import urllib.parse
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from coint.errors import AuthError
from coint.jarvis_connector import JarvisConnector
from coint.server import Worker, make_handler
from fakes import FOUNDER

CB = "https://claude.ai/api/mcp/auth_callback"
TOKENS = {"gh-g": ("jarvis-app", FOUNDER), "gh-other": ("jarvis-app", "someone-else"),
          "gh-kitt-g": ("kitt-app", FOUNDER)}


def _check(tok, app):
    if tok not in TOKENS or TOKENS[tok][0] != app:
        raise AuthError("token not issued to this app")
    return {"app": {"client_id": TOKENS[tok][0]}, "user": {"login": TOKENS[tok][1], "id": 7}}


@pytest.fixture
def conn(h, monkeypatch):
    monkeypatch.setattr(h.engine.jarvis_verifier, "_check_token", lambda t: _check(t, "jarvis-app"))
    codes = {"code-g": "gh-g", "code-other": "gh-other"}
    return JarvisConnector(h.engine, "https://coint.example.com", exchange_code=lambda c: codes[c])


def _pkce():
    verifier = "v" * 64
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    return verifier, challenge


def _connect(conn, gh_code="code-g"):
    reg = conn.register({"redirect_uris": [CB], "client_name": "Claude"})
    assert reg.status == 201
    cid = reg.body["client_id"]
    verifier, challenge = _pkce()
    r = conn.authorize({"response_type": "code", "client_id": cid, "redirect_uri": CB, "state": "s1",
                        "code_challenge": challenge, "code_challenge_method": "S256", "scope": "read:user"})
    assert r.status == 302 and r.headers["Location"].startswith("https://github.com/login/oauth/authorize?")
    gh_state = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(r.headers["Location"]).query))["state"]
    cb = conn.callback({"code": gh_code, "state": gh_state})
    loc = urllib.parse.urlsplit(cb.headers["Location"])
    q = dict(urllib.parse.parse_qsl(loc.query))
    return cid, verifier, q


def test_discovery_metadata(conn):
    pr = conn.protected_resource().body
    assert pr["resource"] == "https://coint.example.com/mcp/jarvis"
    assert pr["authorization_servers"] == ["https://coint.example.com"]
    asm = conn.authorization_server().body
    assert asm["code_challenge_methods_supported"] == ["S256"] and asm["registration_endpoint"].endswith("/oauth/register")


def test_registration_only_allows_claude_callbacks(conn):
    assert conn.register({"redirect_uris": ["https://evil.example.com/cb"]}).status == 400
    assert conn.register({"redirect_uris": [CB]}).status == 201


def test_full_sign_in_and_pkce(conn):
    cid, verifier, q = _connect(conn)
    assert q["state"] == "s1" and "code" in q
    assert conn.token({"grant_type": "authorization_code", "code": q["code"], "client_id": cid,
                       "redirect_uri": CB, "code_verifier": "wrong"}).status == 400       # PKCE fails, code burnt
    cid, verifier, q = _connect(conn)
    tok = conn.token({"grant_type": "authorization_code", "code": q["code"], "client_id": cid,
                      "redirect_uri": CB, "code_verifier": verifier})
    assert tok.status == 200 and tok.body["access_token"] == "gh-g"
    assert conn.token({"grant_type": "authorization_code", "code": q["code"], "client_id": cid,
                       "redirect_uri": CB, "code_verifier": verifier}).status == 400     # one-time code


def test_non_founder_cannot_connect(conn):
    cid, verifier, q = _connect(conn, gh_code="code-other")
    assert q["error"] == "access_denied" and "code" not in q


def test_mcp_requires_valid_jarvis_session_token(conn):
    r = conn.mcp("", {"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    assert r.status == 401 and "resource_metadata=" in r.headers["WWW-Authenticate"]
    assert conn.mcp("gh-kitt-g", {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}).status == 401
    assert conn.mcp("gh-other", {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}).status == 403


def test_mcp_final_review_end_to_end(h, conn):
    h.to_final_review()
    init = conn.mcp("gh-g", {"jsonrpc": "2.0", "id": 1, "method": "initialize",
                             "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                                        "clientInfo": {"name": "claude", "version": "x"}}})
    assert init.body["result"]["protocolVersion"] == "2025-06-18"
    assert conn.mcp("gh-g", {"jsonrpc": "2.0", "method": "notifications/initialized"}).status == 202
    tools = conn.mcp("gh-g", {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}).body["result"]["tools"]
    assert {t["name"] for t in tools} == {"list_pending_final_reviews", "submit_founder_decision"}
    pending = conn.mcp("gh-g", {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                                "params": {"name": "list_pending_final_reviews", "arguments": {}}}).body["result"]
    item = pending["structuredContent"]["pending"][0]
    assert item["delivery_tag"] == "CI-TEST-v1" and item["review_package_email"]["state"] == "SENT"
    call = {"name": "submit_founder_decision", "arguments": {
        "decision_id": "mcp-final-0001", "decision_type": "delivery_approve_close", "project_id": "CI-TEST",
        "cycle": 1, "sha": item["sha"], "founder_statement": "APPROVE AND CLOSE CI-TEST v1"}}
    # an initial-phase decision is refused on the JARVIS connector
    bad = conn.mcp("gh-g", {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {
        "name": "submit_founder_decision", "arguments": dict(call["arguments"], decision_id="mcp-bad-0001",
                                                             decision_type="initial_approve")}}).body["result"]
    assert bad["isError"] is True
    res = conn.mcp("gh-g", {"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": call}).body["result"]
    assert res["isError"] is False and res["structuredContent"]["outcome"] == "accepted"
    h.run_all()   # JARVIS publishes the reference, KITT records it -> closure
    assert h.project()["status"] == "CLOSED"
    dec = h.db.one("SELECT * FROM founder_decisions WHERE decision_id='mcp-final-0001'")
    assert dec["channel"] == "jarvis_session" and dec["github_login"] == FOUNDER


def test_connector_routes_over_http(h, conn):
    worker = Worker(h.engine, concurrency=1)
    srv = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(h.engine, worker, connector=conn))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_port}"
    with urllib.request.urlopen(base + "/.well-known/oauth-authorization-server") as r:
        assert json.loads(r.read())["issuer"] == "https://coint.example.com"
    req = urllib.request.Request(base + "/mcp/jarvis", method="POST",
                                 data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"}).encode())
    try:
        urllib.request.urlopen(req)
        raise AssertionError("expected 401")
    except urllib.error.HTTPError as e:
        assert e.code == 401 and "resource_metadata" in e.headers["WWW-Authenticate"]
    req.add_header("Authorization", "Bearer gh-g")
    with urllib.request.urlopen(req) as r:
        assert json.loads(r.read()) == {"jsonrpc": "2.0", "id": 1, "result": {}}
    srv.shutdown()
