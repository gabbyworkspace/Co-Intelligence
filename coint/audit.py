from __future__ import annotations

import logging

from .db import DB, dumps, iso

log = logging.getLogger("coint.audit")


def record_audit_event(db: DB, *, actor: str, action: str, outcome: str,
                       project_id: str | None = None, cycle: int | None = None,
                       version: str | None = None, detail=None) -> None:
    """Record actor, action, version, timestamp and outcome. Joins any open tx."""
    with db.tx() as c:
        c.execute(
            "INSERT INTO audit_events(ts, actor, action, project_id, cycle, version, outcome, detail)"
            " VALUES (?,?,?,?,?,?,?,?)",
            (iso(), actor, action, project_id, cycle, version, outcome,
             dumps(detail) if detail is not None else None),
        )
    log.info("audit actor=%s action=%s project=%s cycle=%s version=%s outcome=%s",
             actor, action, project_id, cycle, version, outcome)
