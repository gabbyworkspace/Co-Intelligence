import hashlib
import hmac
import json
import threading
import time
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from coint.server import Worker, make_handler
from conftest import BRIEF
from fakes import FOUNDER


def _serve(h):
    worker = Worker(h.engine, concurrency=2)
    srv = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(h.engine, worker))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    threading.Thread(target=worker.loop, kwargs={"idle_seconds": 0.2}, daemon=True).start()
    return srv


def _req(srv, path, body=None, headers=None, method="POST"):
    req = urllib.request.Request(f"http://127.0.0.1:{srv.server_port}{path}", method=method,
                                 data=json.dumps(body).encode() if isinstance(body, dict) else body)
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def test_kitt_session_decision_endpoint_and_async_pickup(h, monkeypatch):
    srv = _serve(h)
    # integration unavailable -> 503 blocker, never a bypass
    h.s.kitt_oauth_client_id = None
    code, res = _req(srv, "/kitt/founder-decision", {"decision_id": "abcdef12"}, {"Authorization": "Bearer t"})
    assert code == 503 and "blocker" in res
    h.s.kitt_oauth_client_id = "kitt-app"

    tokens = {"g-token": {"app": {"client_id": "kitt-app"}, "user": {"login": FOUNDER, "id": 1}},
              "kitt-token": {"app": {"client_id": "kitt-app"}, "user": {"login": "kitt-bot", "id": 2}}}

    def check(tok):
        from coint.errors import AuthError
        if tok not in tokens:
            raise AuthError("unknown token")
        return tokens[tok]
    monkeypatch.setattr(h.engine.kitt_verifier, "_check_token", check)
    decision = {"decision_id": "start-0001", "decision_type": "project_start", "issue_number": 7,
                "brief": BRIEF, "founder_statement": "Yes, confirmed."}
    assert _req(srv, "/kitt/founder-decision", decision)[0] == 401
    assert _req(srv, "/kitt/founder-decision", decision, {"Authorization": "Bearer kitt-token"})[0] == 403
    code, res = _req(srv, "/kitt/founder-decision", decision, {"Authorization": "Bearer g-token"})
    assert code == 200 and res["outcome"] == "accepted"
    for _ in range(100):
        p = h.engine.project("CI-TEST")
        if p and p["stage"] == "FOUNDER_INITIAL_REVIEW":
            break
        time.sleep(0.05)
    assert h.engine.project("CI-TEST")["stage"] == "FOUNDER_INITIAL_REVIEW"
    code, res = _req(srv, "/kitt/pending", headers={"Authorization": "Bearer g-token"}, method="GET")
    assert code == 200 and res["pending"][0]["allowed_decisions"] == ["initial_approve", "initial_changes"]
    code, spec = _req(srv, "/kitt/openapi.json", method="GET")
    assert spec["paths"]["/kitt/founder-decision"]["post"]["x-openai-isConsequential"] is True
    srv.shutdown()


def test_webhook_durable_queue_and_dedupe(h):
    srv = _serve(h)
    payload = {"action": "created", "repository": {"full_name": "gabbyworkspace/Co-Intelligence"},
               "issue": {"number": 7}, "sender": {"login": "kitt-bot", "type": "User"},
               "comment": {"id": 42, "body": "/delivery approve-close 1 " + "a" * 40,
                           "created_at": "t", "updated_at": "t", "html_url": "u"}}
    body = json.dumps(payload).encode()
    hdr = {"X-Hub-Signature-256": "sha256=" + hmac.new(b"s3cret", body, hashlib.sha256).hexdigest(),
           "X-GitHub-Event": "issue_comment", "X-GitHub-Delivery": "aaaa-bbbb-cccc"}
    assert _req(srv, "/webhook", body, hdr) == (202, {"queued": True, "duplicate": False})
    assert _req(srv, "/webhook", body, hdr) == (202, {"queued": False, "duplicate": True})
    for _ in range(100):
        r = h.db.one("SELECT outcome FROM processed_comments WHERE comment_id=42")
        if r:
            break
        time.sleep(0.05)
    assert r["outcome"].startswith("rejected")
    srv.shutdown()


def test_jarvis_session_endpoints(h, monkeypatch):
    h.to_final_review()
    srv = _serve(h)
    tokens = {"g-jarvis": {"app": {"client_id": "jarvis-app"}, "user": {"login": FOUNDER, "id": 1}},
              "g-kitt": {"app": {"client_id": "kitt-app"}, "user": {"login": FOUNDER, "id": 1}}}

    def check(tok, cid):
        from coint.errors import AuthError
        info = tokens.get(tok)
        if not info or info["app"]["client_id"] != cid:
            raise AuthError("token not issued to this app")
        return info
    monkeypatch.setattr(h.engine.jarvis_verifier, "_check_token", lambda t: check(t, "jarvis-app"))
    monkeypatch.setattr(h.engine.kitt_verifier, "_check_token", lambda t: check(t, "kitt-app"))
    sha = h.project()["current_delivery_sha"]
    dec = {"decision_id": "final-0001", "decision_type": "delivery_approve_close", "project_id": "CI-TEST",
           "cycle": 1, "sha": sha, "founder_statement": "APPROVE AND CLOSE"}
    # a KITT-session token cannot be used on the JARVIS channel, and KITT cannot submit final approval
    assert _req(srv, "/jarvis/founder-decision", dec, {"Authorization": "Bearer g-kitt"})[0] == 401
    assert _req(srv, "/kitt/founder-decision", dict(dec, decision_id="final-0002"),
                {"Authorization": "Bearer g-kitt"})[0] == 400
    code, res = _req(srv, "/jarvis/pending", headers={"Authorization": "Bearer g-jarvis"}, method="GET")
    assert code == 200 and res["session"] == "jarvis_session" and res["pending"][0]["sha"] == sha
    code, res = _req(srv, "/jarvis/founder-decision", dec, {"Authorization": "Bearer g-jarvis"})
    assert code == 200 and res["outcome"] == "accepted"
    for _ in range(100):
        if h.engine.project("CI-TEST")["status"] == "CLOSED":
            break
        time.sleep(0.05)
    assert h.engine.project("CI-TEST")["status"] == "CLOSED"   # after KITT recorded it
    spec = _req(srv, "/jarvis/openapi.json", method="GET")[1]
    assert set(spec["paths"]) == {"/jarvis/pending", "/jarvis/founder-decision"}
    srv.shutdown()
