import itertools
import json
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
        return self.say("/project start\n```json\n" + json.dumps(BRIEF) + "\n```")

    def to_final_review(self):
        self.start()
        self.run_all()
        p = self.project()
        self.say(f"/initial approve 1 {p['current_document_sha']}")
        self.run_all()
        return self.project()

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
