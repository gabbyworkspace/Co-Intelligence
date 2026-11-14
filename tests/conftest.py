import itertools
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from coint.config import ROLES  # noqa: E402
from coint.db import DB  # noqa: E402
from coint.workflow import Engine  # noqa: E402
from fakes import FOUNDER, FakeAdapter, FakeGitHub, FakeGmail, make_settings  # noqa: E402

BRIEF = {"title": "Widget", "objective": "Build widget", "scope": ["core"], "deliverables": ["app"],
         "acceptance_criteria": ["AC1"], "constraints": ["none"], "confirmed": True, "project_id": "CI-TEST"}


class Harness:
    _ids = itertools.count(1000)

    def __init__(self, tmp_path, *, manual=(), scripts=None, gmail_mode="ok", **settings_kw):
        self.path = str(tmp_path / "coint.sqlite3")
        self.s = make_settings(self.path, **settings_kw)
        self.gh = FakeGitHub()
        self.gmail = FakeGmail(gmail_mode)
        self.adapters = {r: FakeAdapter(r, (scripts or {}).get(r), external=r in manual) for r in ROLES}
        self.engine = Engine(self.s, DB(self.path), self.gh, adapters=self.adapters, gmail=self.gmail)
        self.issue = 7

    def restart(self):
        self.engine.db.close()
        self.engine = Engine(self.s, DB(self.path), self.gh, adapters=self.adapters, gmail=self.gmail)

    @property
    def db(self):
        return self.engine.db

    def say(self, body, actor=FOUNDER, **kw):
        cid = kw.pop("comment_id", next(self._ids))
        out = self.engine.handle_comment(issue=self.issue, comment_id=cid, body=body, actor=actor,
                                         url=f"https://github.com/c/{cid}", **kw)
        self.engine.dispatch_outbox()
        return out

    def decide(self, dtype, login=FOUNDER, client_id=None, decision_id=None, channel=None, **fields):
        from coint.kitt_session import Attestation
        channel = channel or ("jarvis_session" if dtype.startswith("delivery_") else "kitt_session")
        client_id = client_id or ("jarvis-app" if channel == "jarvis_session" else "kitt-app")
        att = Attestation(login, 4242, client_id, "f" * 64, channel)
        req = {"decision_id": decision_id or f"dec-{next(self._ids)}", "decision_type": dtype,
               "founder_statement": fields.pop("statement", "G: yes, go ahead"), **fields}
        if dtype != "project_start":
            req.setdefault("project_id", "CI-TEST")
        res = self.engine.founder_decision(att, req)
        self.engine.dispatch_outbox()
        return res["outcome"]

    def run_all(self, max_rounds=50):
        from coint import queue as Q
        for _ in range(max_rounds):
            ids = Q.eligible_task_ids(self.db)
            if not ids:
                return
            for tid in ids:
                self.engine.run_task(tid)

    def project(self):
        return self.engine.project("CI-TEST")

    def start(self):
        return self.decide("project_start", brief=BRIEF, issue_number=self.issue)

    def to_final_review(self, send_review=True):
        self.start()
        self.run_all()
        p = self.project()
        self.decide("initial_approve", cycle=1, sha=p["current_document_sha"])
        self.run_all()
        if send_review:  # step 11.3: review package to baileys (kept out of later final-email assertions)
            from coint.email_report import process_email_outbox
            mode, self.gmail.mode = self.gmail.mode, "ok"
            process_email_outbox(self.engine)
            self.gmail.mode = mode
            self.review_sends = list(self.gmail.sends)
            self.gmail.sends.clear()
        return self.project()

    def final_row(self):
        return self.db.one("SELECT * FROM email_outbox WHERE kind='final_report'")

    def final_count(self):
        return self.db.one("SELECT COUNT(*) n FROM email_outbox WHERE kind='final_report'")["n"]

    def tasks(self, **where):
        q = "SELECT * FROM tasks"
        if where:
            q += " WHERE " + " AND ".join(f"{k}=?" for k in where)
        return self.db.all(q + " ORDER BY created_at, rowid", *where.values())


@pytest.fixture
def h(tmp_path):
    return Harness(tmp_path)


@pytest.fixture
def make_h(tmp_path):
    return lambda **kw: Harness(tmp_path, **kw)
