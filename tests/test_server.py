import hashlib
import hmac
import json
import threading
import time
import urllib.request
from http.server import ThreadingHTTPServer

from coint.server import Worker, make_handler
from conftest import BRIEF
from fakes import FOUNDER


def test_webhook_queue_then_async_processing(h):
    worker = Worker(h.engine, concurrency=2)
    srv = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(h.engine, worker))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    threading.Thread(target=worker.loop, kwargs={"idle_seconds": 0.2}, daemon=True).start()
    payload = {"action": "created", "repository": {"full_name": "gabbyworkspace/Co-Intelligence"},
               "issue": {"number": 7}, "sender": {"login": FOUNDER, "type": "User"},
               "comment": {"id": 42, "body": "/project start\n```json\n" + json.dumps(BRIEF) + "\n```",
                           "created_at": "t", "updated_at": "t", "html_url": "u"}}
    body = json.dumps(payload).encode()
    sig = "sha256=" + hmac.new(b"s3cret", body, hashlib.sha256).hexdigest()

    def post():
        req = urllib.request.Request(f"http://127.0.0.1:{srv.server_port}/webhook", data=body, method="POST")
        for k, v in {"X-Hub-Signature-256": sig, "X-GitHub-Event": "issue_comment",
                     "X-GitHub-Delivery": "aaaa-bbbb-cccc", "Content-Type": "application/json"}.items():
            req.add_header(k, v)
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())

    assert post() == (202, {"queued": True, "duplicate": False})
    assert post() == (202, {"queued": False, "duplicate": True})
    for _ in range(100):
        p = h.engine.project("CI-TEST")
        if p and p["stage"] == "FOUNDER_INITIAL_REVIEW":
            break
        time.sleep(0.05)
    assert h.engine.project("CI-TEST")["stage"] == "FOUNDER_INITIAL_REVIEW"
    srv.shutdown()
