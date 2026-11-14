"""Webhook receiver + asynchronous worker.

The HTTP handler only verifies and durably queues the event, then returns 202.
A worker thread (woken immediately) processes events and runs model work.
"""
from __future__ import annotations

import json
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import queue as Q
from .audit import record_audit_event
from .errors import AuthError, PermissionDenied, TransientError
from .kitt_session import SessionUnavailable, openapi_spec
from .webhook import WebhookRejected, persist_delivery, verify_webhook

log = logging.getLogger("coint.server")


class Worker:
    def __init__(self, engine, concurrency: int = 4):
        self.engine = engine
        self.wake = threading.Event()
        self.pool = ThreadPoolExecutor(max_workers=concurrency)
        self._inflight: set[str] = set()
        self._lock = threading.Lock()

    def _run(self, tid: str):
        try:
            self.engine.run_task(tid)
        except Exception:  # noqa: BLE001
            log.exception("task %s crashed", tid)
        finally:
            with self._lock:
                self._inflight.discard(tid)
            self.wake.set()

    def tick(self):
        db = self.engine.db
        for r in db.all("SELECT delivery_id FROM webhook_deliveries WHERE status='RECEIVED' ORDER BY received_at"):
            self.engine.process_delivery(r["delivery_id"])
        self.engine.dispatch_outbox()
        for tid in Q.eligible_task_ids(db):
            with self._lock:
                if tid in self._inflight:
                    continue
                self._inflight.add(tid)
            self.pool.submit(self._run, tid)

    def loop(self, idle_seconds: float = 10.0):
        while True:
            self.wake.wait(idle_seconds)
            self.wake.clear()
            try:
                self.tick()
            except Exception:  # noqa: BLE001
                log.exception("worker tick failed")


def make_handler(engine, worker: Worker, connector=None):
    if connector is None and engine.s.public_base_url:
        from .jarvis_connector import JarvisConnector
        connector = JarvisConnector(engine, engine.s.public_base_url)

    class H(BaseHTTPRequestHandler):
        def _send(self, code: int, obj, headers: dict | None = None):
            data = json.dumps(obj).encode() if obj is not None else b""
            self.send_response(code)
            if obj is not None:
                self.send_header("Content-Type", "application/json")
            for k, v in (headers or {}).items():
                self.send_header(k, v)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _connector(self, fn):
            if connector is None:
                return self._send(503, {"error": "JARVIS connector unavailable: PUBLIC_BASE_URL not configured"})
            r = fn()
            return self._send(r.status, r.body, r.headers)

        def _query(self) -> dict:
            from urllib.parse import parse_qsl, urlsplit
            return dict(parse_qsl(urlsplit(self.path).query))

        def _body(self, limit=256 * 1024) -> bytes:
            length = int(self.headers.get("Content-Length") or 0)
            if length > limit:
                raise ValueError("too large")
            return self.rfile.read(length)

        def _bearer(self) -> str:
            h = self.headers.get("Authorization") or ""
            return h[7:].strip() if h.lower().startswith("bearer ") else ""

        def _verifier(self):
            return engine.jarvis_verifier if self.path.startswith("/jarvis/") else engine.kitt_verifier

        def _verify_session(self):
            """Authorized KITT/JARVIS session + founder identity, or an error response."""
            try:
                return self._verifier().verify_founder(self._bearer()), None
            except SessionUnavailable as e:
                record_audit_event(engine.db, actor="unknown", action="kitt_session.unavailable",
                                   outcome="BLOCKER", detail={"reason": str(e)})
                return None, (503, {"error": "founder decision channel unavailable", "blocker": str(e)})
            except PermissionDenied as e:
                record_audit_event(engine.db, actor="unknown", action="kitt_session.denied", outcome="403",
                                   detail={"reason": str(e)})
                return None, (403, {"error": str(e)})
            except AuthError as e:
                return None, (401, {"error": str(e)})
            except TransientError as e:
                return None, (503, {"error": f"temporarily unable to verify session: {e}"})

        def do_GET(self):
            route = self.path.split("?", 1)[0]
            if route in ("/.well-known/oauth-protected-resource", "/.well-known/oauth-protected-resource/mcp/jarvis"):
                return self._connector(lambda: connector.protected_resource())
            if route == "/.well-known/oauth-authorization-server":
                return self._connector(lambda: connector.authorization_server())
            if route == "/oauth/authorize":
                return self._connector(lambda: connector.authorize(self._query()))
            if route == "/oauth/callback":
                return self._connector(lambda: connector.callback(self._query()))
            if route == "/mcp/jarvis":
                return self._send(405, {"error": "use POST (Streamable HTTP, JSON responses)"}, {"Allow": "POST"})
            if self.path == "/healthz":
                engine.db.one("SELECT 1")
                return self._send(200, {"ok": True})
            if self.path in ("/kitt/openapi.json", "/jarvis/openapi.json"):
                base = engine.s.public_base_url or f"http://{self.headers.get('Host', 'localhost')}"
                return self._send(200, openapi_spec(base, self._verifier().channel))
            if self.path in ("/kitt/pending", "/jarvis/pending"):
                att, err = self._verify_session()
                if err:
                    return self._send(*err)
                return self._send(200, {"session": att.channel,
                                        "pending": engine.pending_reviews(channel=att.channel)})
            self._send(404, {"error": "not found"})

        def do_POST(self):
            route = self.path.split("?", 1)[0]
            if route in ("/oauth/register", "/oauth/token", "/mcp/jarvis"):
                try:
                    raw = self._body()
                except ValueError:
                    return self._send(413, {"error": "too large"})
                if route == "/oauth/token":
                    from urllib.parse import parse_qsl
                    form = dict(parse_qsl(raw.decode()))
                    return self._connector(lambda: connector.token(form))
                try:
                    body = json.loads(raw or b"{}")
                except ValueError:
                    return self._send(400, {"jsonrpc": "2.0", "id": None,
                                            "error": {"code": -32700, "message": "parse error"}})
                if route == "/oauth/register":
                    return self._connector(lambda: connector.register(body if isinstance(body, dict) else {}))
                res = self._connector(lambda: connector.mcp(self._bearer(), body))
                worker.wake.set()
                return res
            if self.path in ("/kitt/founder-decision", "/jarvis/founder-decision"):
                att, err = self._verify_session()
                if err:
                    return self._send(*err)
                length = int(self.headers.get("Content-Length") or 0)
                if length > 1024 * 1024:
                    return self._send(413, {"error": "too large"})
                try:
                    req = json.loads(self.rfile.read(length) or b"{}")
                    assert isinstance(req, dict)
                except (ValueError, AssertionError):
                    return self._send(400, {"error": "body must be a JSON object"})
                res = engine.founder_decision(att, req)
                worker.wake.set()
                return self._send(res.pop("status"), res)
            if self.path != "/webhook":
                return self._send(404, {"error": "not found"})
            length = int(self.headers.get("Content-Length") or 0)
            if length > engine.s.max_webhook_bytes:
                return self._send(413, {"error": "too large"})
            body = self.rfile.read(length)
            try:
                ev = verify_webhook(engine.s, dict(self.headers.items()), body)
            except WebhookRejected as e:
                log.warning("webhook rejected: %s", e)
                return self._send(e.status, {"error": str(e)})
            new = persist_delivery(engine.db, ev)  # durable BEFORE acknowledging
            worker.wake.set()
            self._send(202, {"queued": new, "duplicate": not new})

        def log_message(self, fmt, *args):
            log.info("%s %s", self.address_string(), fmt % args)
    return H


def serve(engine, host: str = "0.0.0.0", port: int = 8080, concurrency: int = 4):
    worker = Worker(engine, concurrency)
    threading.Thread(target=worker.loop, daemon=True).start()
    worker.wake.set()
    httpd = ThreadingHTTPServer((host, port), make_handler(engine, worker))
    log.info("listening on %s:%s", host, port)
    httpd.serve_forever()
