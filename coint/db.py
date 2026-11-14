"""Persistent store (SQLite, WAL mode).

All state that must survive a restart lives here: webhook inbox, processed
comments, tasks (the queue), routing outbox, handoffs, approvals, closures,
email outbox, check results, and the audit log.

Atomicity uses `BEGIN IMMEDIATE` transactions so that the webhook path, the
worker and the scheduler (separate processes) can never claim the same task.
For multi-host deployments swap in PostgreSQL with the same schema and
`SELECT ... FOR UPDATE SKIP LOCKED` claims (see docs/OPERATING.md).
"""
from __future__ import annotations

import contextlib
import json
import os
import sqlite3
import threading
from datetime import datetime, timezone

SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL);

CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    issue_number INTEGER NOT NULL UNIQUE,
    branch TEXT NOT NULL,
    stage TEXT NOT NULL,
    status TEXT NOT NULL,
    current_cycle INTEGER NOT NULL DEFAULT 1,
    assignment_rev INTEGER NOT NULL DEFAULT 1,
    revision_loops INTEGER NOT NULL DEFAULT 0,
    brief_json TEXT NOT NULL,
    current_document_sha TEXT,
    current_package_sha TEXT,
    current_delivery_sha TEXT,
    head_sha TEXT,
    blocked_reason TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS webhook_deliveries (
    delivery_id TEXT PRIMARY KEY,
    event TEXT NOT NULL,
    action TEXT,
    payload TEXT NOT NULL,
    status TEXT NOT NULL,            -- RECEIVED | PROCESSED | IGNORED | ERROR
    error TEXT,
    received_at TEXT NOT NULL,
    processed_at TEXT
);

CREATE TABLE IF NOT EXISTS processed_comments (
    comment_id INTEGER PRIMARY KEY,
    issue_number INTEGER NOT NULL,
    actor TEXT NOT NULL,
    command TEXT,
    outcome TEXT NOT NULL,
    processed_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    idem_key TEXT NOT NULL UNIQUE,
    project_id TEXT NOT NULL REFERENCES projects(id),
    cycle INTEGER NOT NULL,
    stage TEXT NOT NULL,
    role TEXT NOT NULL,
    task_type TEXT NOT NULL,
    input_sha TEXT NOT NULL,
    assignment_rev INTEGER NOT NULL,
    state TEXT NOT NULL,
    external INTEGER NOT NULL DEFAULT 0,
    attempts INTEGER NOT NULL DEFAULT 0,
    next_attempt_at TEXT,
    lease_owner TEXT,
    lease_expires_at TEXT,
    heartbeat_at TEXT,
    deadline_at TEXT,
    manifest TEXT NOT NULL,
    checkpoint TEXT,                 -- model output checkpoint (before external actions)
    published_sha TEXT,              -- commit SHA of published outputs
    output TEXT,
    error TEXT,
    overdue_flagged_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_tasks_state ON tasks(state, next_attempt_at);
CREATE INDEX IF NOT EXISTS ix_tasks_project ON tasks(project_id, cycle);

CREATE TABLE IF NOT EXISTS outbox (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL,
    kind TEXT NOT NULL,              -- comment | close_issue | label
    payload TEXT NOT NULL,
    dedupe_key TEXT UNIQUE,
    created_at TEXT NOT NULL,
    dispatched_at TEXT,
    attempts INTEGER NOT NULL DEFAULT 0,
    last_error TEXT
);

CREATE TABLE IF NOT EXISTS handoffs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    cycle INTEGER NOT NULL,
    revision INTEGER NOT NULL,
    source_role TEXT NOT NULL,
    dest_role TEXT NOT NULL,
    task_type TEXT NOT NULL,
    input_sha TEXT NOT NULL,
    output_sha TEXT NOT NULL,
    manifest TEXT NOT NULL,
    expected_outputs TEXT NOT NULL,
    next_action TEXT NOT NULL,
    comment_id INTEGER,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS council_packages (
    project_id TEXT NOT NULL,
    cycle INTEGER NOT NULL,
    package_sha TEXT NOT NULL,
    manifest TEXT NOT NULL,
    frozen_at TEXT NOT NULL,
    PRIMARY KEY (project_id, cycle, package_sha)
);

CREATE TABLE IF NOT EXISTS deliveries (
    project_id TEXT NOT NULL,
    cycle INTEGER NOT NULL,
    delivery_sha TEXT NOT NULL,
    development_complete INTEGER NOT NULL,
    verification_status TEXT NOT NULL,
    verification TEXT NOT NULL,
    unresolved_blockers TEXT NOT NULL,
    final_report_path TEXT NOT NULL,
    submitted_at TEXT NOT NULL,
    PRIMARY KEY (project_id, cycle, delivery_sha)
);

CREATE TABLE IF NOT EXISTS approvals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL,
    cycle INTEGER NOT NULL,
    kind TEXT NOT NULL,              -- initial | delivery
    decision TEXT NOT NULL,          -- approve | changes | approve-close
    actor TEXT NOT NULL,
    sha TEXT NOT NULL,
    comment_id INTEGER,
    comment_url TEXT,
    details TEXT,
    channel TEXT NOT NULL DEFAULT 'system',  -- kitt_session | jarvis_session | system
    attestation_id TEXT,                     -- founder_decisions.decision_id
    created_at TEXT NOT NULL
);

-- Every founder decision received from the authorized KITT session (accepted or not).
CREATE TABLE IF NOT EXISTS founder_decisions (
    decision_id TEXT PRIMARY KEY,
    decision_type TEXT NOT NULL,
    project_id TEXT,
    cycle INTEGER,
    sha TEXT,
    request_json TEXT NOT NULL,
    request_hash TEXT NOT NULL,
    github_login TEXT NOT NULL,
    github_user_id INTEGER NOT NULL,
    oauth_client_id TEXT NOT NULL,
    token_fingerprint TEXT NOT NULL,
    channel TEXT NOT NULL,           -- kitt_session | jarvis_session
    outcome TEXT NOT NULL,           -- accepted | rejected
    detail TEXT,
    received_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS closures (
    project_id TEXT NOT NULL,
    cycle INTEGER NOT NULL,
    approval_id INTEGER NOT NULL REFERENCES approvals(id),
    delivery_sha TEXT NOT NULL,
    closed_at TEXT NOT NULL,
    issue_closed_at TEXT,
    PRIMARY KEY (project_id, cycle)
);

CREATE TABLE IF NOT EXISTS email_outbox (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email_key TEXT NOT NULL UNIQUE,  -- final:project|cycle|approval  or  review:project|cycle|sha
    kind TEXT NOT NULL DEFAULT 'final_report',  -- final_report | review_package
    to_addr TEXT NOT NULL DEFAULT 'g@resystem.org',
    delivery_sha TEXT,
    project_id TEXT NOT NULL,
    cycle INTEGER NOT NULL,
    approval_id INTEGER,
    state TEXT NOT NULL,             -- PENDING | SENDING | SENT | SEND_UNCERTAIN | BLOCKED | CANCELLED
    rfc822_message_id TEXT NOT NULL,
    subject TEXT,
    attempts INTEGER NOT NULL DEFAULT 0,
    next_attempt_at TEXT,
    attempt_started_at TEXT,
    gmail_message_id TEXT,
    accepted_at TEXT,
    last_error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS check_results (
    sha TEXT NOT NULL,
    name TEXT NOT NULL,
    status TEXT NOT NULL,
    conclusion TEXT,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (sha, name)
);

CREATE TABLE IF NOT EXISTS reminders (
    project_id TEXT NOT NULL,
    stage TEXT NOT NULL,
    cycle INTEGER NOT NULL,
    last_sent_at TEXT NOT NULL,
    PRIMARY KEY (project_id, stage, cycle)
);

CREATE TABLE IF NOT EXISTS scan_cursors (
    name TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    project_id TEXT,
    cycle INTEGER,
    version TEXT,
    outcome TEXT NOT NULL,
    detail TEXT
);
"""


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime | None = None) -> str:
    return (dt or utcnow()).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def parse_iso(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)


class DB:
    def __init__(self, path: str):
        self.path = path
        if path != ":memory:":
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self._local = threading.local()
        self.conn.executescript(SCHEMA)  # executescript manages its own transaction
        with self.tx() as c:
            if not c.execute("SELECT 1 FROM schema_version").fetchone():
                c.execute("INSERT INTO schema_version VALUES (1)")

    @property
    def conn(self) -> sqlite3.Connection:
        c = getattr(self._local, "conn", None)
        if c is None:
            c = sqlite3.connect(self.path, timeout=30, isolation_level=None)
            c.row_factory = sqlite3.Row
            c.execute("PRAGMA journal_mode=WAL")
            c.execute("PRAGMA foreign_keys=ON")
            c.execute("PRAGMA busy_timeout=30000")
            self._local.conn = c
        return c

    @contextlib.contextmanager
    def tx(self):
        """Immediate (write-locking) transaction; nested calls join the outer one."""
        c = self.conn
        if c.in_transaction:
            yield c
            return
        c.execute("BEGIN IMMEDIATE")
        try:
            yield c
            c.execute("COMMIT")
        except BaseException:
            c.execute("ROLLBACK")
            raise

    def one(self, sql: str, *args):
        return self.conn.execute(sql, args).fetchone()

    def all(self, sql: str, *args):
        return self.conn.execute(sql, args).fetchall()

    def close(self):
        c = getattr(self._local, "conn", None)
        if c is not None:
            c.close()
            self._local.conn = None


def dumps(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))
