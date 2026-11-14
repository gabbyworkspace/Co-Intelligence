"""The single scheduler: recovery, overdue monitoring, closure-email recovery and
founder reminders. Models are invoked only for eligible, atomically claimed tasks."""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timedelta, timezone

from . import queue as Q
from .audit import record_audit_event
from .db import iso, parse_iso, utcnow
from .email_report import process_email_outbox
from .models import FOUNDER_STAGES, Stage

log = logging.getLogger("coint.scheduler")

# Reference UTC cron expressions (spec). 05:17 UTC == 09:17 Asia/Dubai (UTC+4, no DST).
JOBS = {
    "recover_pending_tasks": "*/5 * * * *",
    "monitor_overdue_tasks": "2,17,32,47 * * * *",
    "email_recovery": "*/5 * * * *",
    "founder_reminders": "17 5 * * *",
}


def _field_match(field: str, value: int) -> bool:
    for part in field.split(","):
        if part == "*":
            return True
        if part.startswith("*/"):
            if value % int(part[2:]) == 0:
                return True
        elif "-" in part:
            a, b = part.split("-")
            if int(a) <= value <= int(b):
                return True
        elif int(part) == value:
            return True
    return False


def cron_matches(expr: str, dt: datetime) -> bool:
    mi, h, dom, mon, dow = expr.split()
    return (_field_match(mi, dt.minute) and _field_match(h, dt.hour) and _field_match(dom, dt.day)
            and _field_match(mon, dt.month) and _field_match(dow, (dt.weekday() + 1) % 7))


def recover_pending_tasks(engine, run_tasks: bool = True) -> dict:
    db = engine.db
    res = {"deliveries": 0, "comments": 0, "leases": 0, "tasks": 0}
    # 1. Webhook deliveries persisted but not processed (crash between ack and processing).
    cutoff = iso(utcnow() - timedelta(seconds=60))
    for r in db.all("SELECT delivery_id FROM webhook_deliveries WHERE status='RECEIVED' AND received_at<?", cutoff):
        engine.process_delivery(r["delivery_id"])
        res["deliveries"] += 1
    # 2. Missed handoffs/commands: scan repository comments since the last cursor.
    cur = db.one("SELECT value FROM scan_cursors WHERE name='comments_since'")
    since = cur["value"] if cur else iso(utcnow() - timedelta(days=2))[:19] + "Z"
    scan_started = iso(utcnow() - timedelta(minutes=2))[:19] + "Z"
    try:
        for cm in engine.gh.list_repo_comments(since):
            issue = int(cm["issue_url"].rstrip("/").split("/")[-1])
            out = engine.handle_comment(issue=issue, comment_id=cm["id"], body=cm.get("body") or "",
                                        actor=cm["user"]["login"], actor_type=cm["user"].get("type", "User"),
                                        created_at=cm.get("created_at"), updated_at=cm.get("updated_at"),
                                        url=cm.get("html_url"))
            if out not in ("duplicate", "bot", "not_command"):
                res["comments"] += 1
                record_audit_event(db, actor="scheduler", action="recovery.missed_comment", outcome=out,
                                   detail={"comment_id": cm["id"], "issue": issue})
        with db.tx() as c:
            c.execute("INSERT OR REPLACE INTO scan_cursors VALUES ('comments_since', ?)", (scan_started,))
    except Exception as e:  # noqa: BLE001
        log.warning("comment scan failed: %s", e)
    # 3. Expired leases (only after the grace period).
    res["leases"] = len(Q.recover_expired_leases(db, engine.s.lease_grace_seconds))
    # 4. Eligible unclaimed tasks (atomic claim prevents double execution with the worker).
    if run_tasks:
        for tid in Q.eligible_task_ids(db):
            if engine.run_task(tid) != "not_claimed":
                res["tasks"] += 1
    # 5. Pending GitHub side effects.
    engine.dispatch_outbox()
    return res


def monitor_overdue_tasks(engine) -> list[str]:
    db, flagged = engine.db, []
    now = iso()
    rows = db.all("SELECT t.*, p.issue_number FROM tasks t JOIN projects p ON p.id=t.project_id WHERE"
                  " t.state IN ('QUEUED','RUNNING','BLOCKED') AND t.deadline_at IS NOT NULL AND t.deadline_at<?"
                  " AND t.overdue_flagged_at IS NULL AND p.status='ACTIVE'", now)
    for t in rows:
        project = engine.project(t["project_id"])
        kind = "missing council review" if t["task_type"] == "council_review" else "stalled task"
        with db.tx() as c:
            c.execute("UPDATE tasks SET overdue_flagged_at=? WHERE id=?", (now, t["id"]))
            engine.comment(c, project, f"⏰ Overdue — {kind}: `{t['id']}` ({t['role']} {t['task_type']}, state "
                                       f"{t['state']}, input `{t['input_sha'][:12]}`), deadline {t['deadline_at']}. "
                                       "The council will not complete without all four reviews of the same package.",
                           f"overdue:{t['id']}")
        record_audit_event(db, actor="scheduler", action="monitor.overdue", outcome=kind,
                           project_id=t["project_id"], cycle=t["cycle"], detail={"task_id": t["id"]})
        flagged.append(t["id"])
    engine.dispatch_outbox()
    return flagged


def founder_reminders(engine) -> list[str]:
    """At most once per 24h per pending review. Never advances the workflow."""
    db, sent = engine.db, []
    for p in db.all("SELECT * FROM projects WHERE status='ACTIVE'"):
        if Stage(p["stage"]) not in FOUNDER_STAGES:
            continue
        r = db.one("SELECT last_sent_at FROM reminders WHERE project_id=? AND stage=? AND cycle=?",
                   p["id"], p["stage"], p["current_cycle"])
        if r and utcnow() - parse_iso(r["last_sent_at"]) < timedelta(hours=23, minutes=50):
            continue
        with db.tx() as c:
            c.execute("INSERT OR REPLACE INTO reminders VALUES (?,?,?,?)", (p["id"], p["stage"], p["current_cycle"], iso()))
            gate = db.one("SELECT manifest FROM tasks WHERE project_id=? AND state='WAITING_FOUNDER'"
                          " ORDER BY created_at DESC LIMIT 1", p["id"])
            gctx = json.loads(gate["manifest"]).get("context", {}) if gate else {}
            jarvis = engine.gate_channel(Stage(p["stage"]), gctx) == "jarvis_session"
            who = "JARVIS" if jarvis else "KITT"
            login = engine.s.adapters[who].github_login
            where = "the JARVIS chat (`/jarvis/pending`)" if jarvis else "KITT's ChatGPT (`listPendingFounderReviews`)"
            engine.comment(c, p, f"🔔 Reminder{f' @{login}' if login else ''}: **Review Required** — `{p['id']}` is "
                                 f"waiting for G's decision at {p['stage']} (Version {p['current_cycle']}). {who}: "
                                 f"present it to G in {where}. Nothing proceeds until G decides through the "
                                 f"authorized {who} session.")
        sent.append(p["id"])
    engine.dispatch_outbox()
    return sent


def run_job(engine, name: str):
    if name == "recover_pending_tasks":
        return recover_pending_tasks(engine)
    if name == "monitor_overdue_tasks":
        return monitor_overdue_tasks(engine)
    if name == "email_recovery":
        return process_email_outbox(engine)
    if name == "founder_reminders":
        return founder_reminders(engine)
    raise ValueError(name)


def run_forever(engine):
    """One scheduler process. Fires each job at most once per matching minute."""
    last = None
    while True:
        now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
        if now != last:
            last = now
            for name, expr in JOBS.items():
                if cron_matches(expr, now):
                    try:
                        log.info("job %s -> %s", name, json.dumps(run_job(engine, name), default=str)[:500])
                    except Exception:  # noqa: BLE001
                        log.exception("job %s failed", name)
        time.sleep(5)
