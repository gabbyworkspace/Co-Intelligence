"""Durable task queue: semantic idempotency, atomic leased claims, heartbeats,
checkpoints, retries, supersession."""
from __future__ import annotations

import uuid
from datetime import timedelta

from .audit import record_audit_event
from .db import DB, dumps, iso, utcnow
from .models import TERMINAL_STATES, TaskState


def semantic_key(project_id: str, cycle: int, stage: str, role: str, input_sha: str,
                 assignment_rev: int) -> str:
    """project, cycle, stage, role, input SHA, assignment revision."""
    return f"{project_id}|c{cycle}|{stage}|{role}|{input_sha}|r{assignment_rev}"


def enqueue_task(db: DB, *, project_id: str, cycle: int, stage: str, role: str,
                 task_type: str, input_sha: str, assignment_rev: int, manifest: dict,
                 state: TaskState = TaskState.QUEUED, external: bool = False,
                 deadline_minutes: int | None = None) -> tuple[str, bool]:
    """Create the task only if its semantic idempotency key is new.

    Returns (task_id, created)."""
    key = semantic_key(project_id, cycle, stage, role, input_sha, assignment_rev)
    now = utcnow()
    with db.tx() as c:
        row = c.execute("SELECT id FROM tasks WHERE idem_key=?", (key,)).fetchone()
        if row:
            return row["id"], False
        tid = f"T-{uuid.uuid4().hex[:12]}"
        c.execute(
            "INSERT INTO tasks(id, idem_key, project_id, cycle, stage, role, task_type, input_sha,"
            " assignment_rev, state, external, next_attempt_at, deadline_at, manifest, created_at, updated_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (tid, key, project_id, cycle, stage, role, task_type, input_sha, assignment_rev,
             state.value, int(external), iso(now),
             iso(now + timedelta(minutes=deadline_minutes)) if deadline_minutes else None,
             dumps(manifest), iso(now), iso(now)),
        )
        record_audit_event(db, actor="system", action="task.enqueue", outcome=state.value,
                           project_id=project_id, cycle=cycle, version=input_sha,
                           detail={"task_id": tid, "role": role, "stage": stage, "task_type": task_type})
    return tid, True


def claim_task(db: DB, task_id: str, worker: str, lease_seconds: int) -> bool:
    """Atomically claim a QUEUED, due task of an ACTIVE project with a lease."""
    now = utcnow()
    with db.tx() as c:
        cur = c.execute(
            "UPDATE tasks SET state='RUNNING', lease_owner=?, lease_expires_at=?, heartbeat_at=?,"
            " attempts=attempts+1, updated_at=? WHERE id=? AND state='QUEUED' AND external=0"
            " AND (next_attempt_at IS NULL OR next_attempt_at<=?)"
            " AND project_id IN (SELECT id FROM projects WHERE status='ACTIVE')",
            (worker, iso(now + timedelta(seconds=lease_seconds)), iso(now), iso(now), task_id, iso(now)),
        )
        return cur.rowcount == 1


def heartbeat(db: DB, task_id: str, worker: str, lease_seconds: int) -> bool:
    now = utcnow()
    with db.tx() as c:
        cur = c.execute(
            "UPDATE tasks SET heartbeat_at=?, lease_expires_at=?, updated_at=?"
            " WHERE id=? AND state='RUNNING' AND lease_owner=?",
            (iso(now), iso(now + timedelta(seconds=lease_seconds)), iso(now), task_id, worker),
        )
        return cur.rowcount == 1


def eligible_task_ids(db: DB, limit: int = 20) -> list[str]:
    rows = db.all(
        "SELECT t.id FROM tasks t JOIN projects p ON p.id=t.project_id"
        " WHERE t.state='QUEUED' AND t.external=0 AND p.status='ACTIVE'"
        " AND (t.next_attempt_at IS NULL OR t.next_attempt_at<=?)"
        " ORDER BY t.created_at LIMIT ?", iso(), limit)
    return [r["id"] for r in rows]


def get_task(db: DB, task_id: str):
    return db.one("SELECT * FROM tasks WHERE id=?", task_id)


def save_checkpoint(db: DB, task_id: str, worker: str, checkpoint: dict) -> None:
    with db.tx() as c:
        cur = c.execute("UPDATE tasks SET checkpoint=?, updated_at=? WHERE id=? AND lease_owner=? AND state='RUNNING'",
                        (dumps(checkpoint), iso(), task_id, worker))
        if cur.rowcount != 1:
            raise RuntimeError("lease lost before checkpoint")


def save_published_sha(db: DB, task_id: str, worker: str, sha: str) -> None:
    with db.tx() as c:
        cur = c.execute("UPDATE tasks SET published_sha=?, updated_at=? WHERE id=? AND lease_owner=? AND state='RUNNING'",
                        (sha, iso(), task_id, worker))
        if cur.rowcount != 1:
            raise RuntimeError("lease lost before publish checkpoint")


def fail_transient(db: DB, task_id: str, worker: str, error: str, delays_minutes) -> str:
    """Retry after 1, 5, 15 minutes; then FAILED."""
    with db.tx() as c:
        t = c.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        if not t or t["state"] != "RUNNING" or t["lease_owner"] != worker:
            return "lease_lost"
        retries_done = t["attempts"] - 1
        if retries_done < len(delays_minutes):
            nxt = utcnow() + timedelta(minutes=delays_minutes[retries_done])
            c.execute("UPDATE tasks SET state='QUEUED', lease_owner=NULL, lease_expires_at=NULL,"
                      " next_attempt_at=?, error=?, updated_at=? WHERE id=?",
                      (iso(nxt), error[:2000], iso(), task_id))
            outcome = f"retry_at:{iso(nxt)}"
        else:
            c.execute("UPDATE tasks SET state='FAILED', lease_owner=NULL, lease_expires_at=NULL,"
                      " error=?, updated_at=? WHERE id=?", (error[:2000], iso(), task_id))
            outcome = "FAILED"
        record_audit_event(db, actor=worker, action="task.transient_failure", outcome=outcome,
                           project_id=t["project_id"], cycle=t["cycle"], version=t["input_sha"],
                           detail={"task_id": task_id, "error": error[:500]})
        return outcome


def block_task(db: DB, task_id: str, reason: str, actor: str = "system") -> None:
    """Permission, authentication and invalid-input failures: BLOCKED, no retry."""
    with db.tx() as c:
        t = c.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        if not t or TaskState(t["state"]) in TERMINAL_STATES:
            return
        c.execute("UPDATE tasks SET state='BLOCKED', lease_owner=NULL, lease_expires_at=NULL,"
                  " error=?, updated_at=? WHERE id=?", (reason[:2000], iso(), task_id))
        record_audit_event(db, actor=actor, action="task.blocked", outcome="BLOCKED",
                           project_id=t["project_id"], cycle=t["cycle"], version=t["input_sha"],
                           detail={"task_id": task_id, "reason": reason[:500]})


def supersede_open_tasks(db: DB, project_id: str, *, before_cycle: int | None = None,
                         stage: str | None = None, except_id: str | None = None,
                         actor: str = "system") -> int:
    """Mark non-terminal tasks SUPERSEDED (older cycle or a replaced stage assignment)."""
    clauses = ["project_id=?", "state IN ('QUEUED','RUNNING','WAITING_FOUNDER','BLOCKED')"]
    args: list = [project_id]
    if before_cycle is not None:
        clauses.append("cycle<?")
        args.append(before_cycle)
    if stage is not None:
        clauses.append("stage=?")
        args.append(stage)
    if except_id is not None:
        clauses.append("id<>?")
        args.append(except_id)
    with db.tx() as c:
        cur = c.execute(f"UPDATE tasks SET state='SUPERSEDED', lease_owner=NULL, lease_expires_at=NULL,"
                        f" updated_at=? WHERE {' AND '.join(clauses)}", (iso(), *args))
        if cur.rowcount:
            record_audit_event(db, actor=actor, action="task.supersede", outcome=str(cur.rowcount),
                               project_id=project_id, detail={"before_cycle": before_cycle, "stage": stage})
        return cur.rowcount


def recover_expired_leases(db: DB, grace_seconds: int) -> list[str]:
    """Only leases expired for longer than the grace period are re-queued."""
    cutoff = iso(utcnow() - timedelta(seconds=grace_seconds))
    with db.tx() as c:
        rows = c.execute("SELECT id, project_id, cycle, lease_owner FROM tasks WHERE state='RUNNING'"
                         " AND external=0 AND lease_expires_at IS NOT NULL AND lease_expires_at<?",
                         (cutoff,)).fetchall()
        for r in rows:
            c.execute("UPDATE tasks SET state='QUEUED', lease_owner=NULL, lease_expires_at=NULL,"
                      " next_attempt_at=?, updated_at=? WHERE id=? AND state='RUNNING'",
                      (iso(), iso(), r["id"]))
            record_audit_event(db, actor="scheduler", action="task.lease_recovered", outcome="QUEUED",
                               project_id=r["project_id"], cycle=r["cycle"],
                               detail={"task_id": r["id"], "previous_owner": r["lease_owner"]})
    return [r["id"] for r in rows]
