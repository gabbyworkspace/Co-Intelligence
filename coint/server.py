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


def make_handler(engine, worker: Worker):
    class H(BaseHTTPRequestHandler):
        def _send(self, code: int, obj: dict):
            data = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path == "/healthz":
                engine.db.one("SELECT 1")
                return self._send(200, {"ok": True})
            self._send(404, {"error": "not found"})

        def do_POST(self):
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
