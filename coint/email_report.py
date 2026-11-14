"""Post-closure final report email through the JARVIS Gmail account.

Durable outbox keyed by (project, cycle, approval). Never sends before closure;
never blindly re-sends after an uncertain outcome.
"""
from __future__ import annotations

import json
from datetime import timedelta
from email.message import EmailMessage
from email.utils import formatdate

from .audit import record_audit_event
from .config import FINAL_REPORT_FROM, FINAL_REPORT_TO, GITHUB_URL
from .db import iso, parse_iso, utcnow
from .errors import PermanentError
from .gmail import DefinitePreSendFailure, UncertainSendOutcome

UNCERTAIN_STALE_SENDING_MINUTES = 10


class NotReady(Exception):
    """Preconditions not yet met (e.g. issue close still pending); try later."""


def _set(db, row_id, **kw):
    kw["updated_at"] = iso()
    cols = ", ".join(f"{k}=?" for k in kw)
    with db.tx() as c:
        c.execute(f"UPDATE email_outbox SET {cols} WHERE id=?", (*kw.values(), row_id))


def check_preconditions(engine, row) -> dict:
    """The six mandatory checks. Returns context for composing the email."""
    db, gh = engine.db, engine.gh
    project = engine.project(row["project_id"])
    closure = db.one("SELECT * FROM closures WHERE project_id=? AND cycle=?", row["project_id"], row["cycle"])
    approval = db.one("SELECT * FROM approvals WHERE id=?", row["approval_id"])
    if not closure or closure["approval_id"] != row["approval_id"]:
        raise PermanentError("no closure record for this approval")                       # 4
    if project["status"] != "CLOSED":
        raise PermanentError("project is not closed")                                     # 4
    if not closure["issue_closed_at"]:
        raise NotReady("tracking issue close not yet confirmed")                          # 4
    if not approval or approval["decision"] != "approve-close" or \
            approval["actor"].lower() != engine.s.founder_login.lower() or \
            approval["sha"] != closure["delivery_sha"] or approval["sha"] != project["current_delivery_sha"] or \
            approval["cycle"] != row["cycle"]:
        raise PermanentError("approval does not match the exact current delivery")         # 3
    d = db.one("SELECT * FROM deliveries WHERE project_id=? AND cycle=? AND delivery_sha=?",
               row["project_id"], row["cycle"], closure["delivery_sha"])
    if not d or not d["development_complete"]:
        raise PermanentError("development not complete")                                  # 1
    root = f"projects/{project['id']}/"
    ver_raw = gh.get_file(root + "verification/verification-report.json", closure["delivery_sha"])
    if not ver_raw or d["verification_status"] != "passed":
        raise PermanentError("required verification evidence missing or not passed")       # 2
    report = gh.get_file(root + d["final_report_path"], closure["delivery_sha"])
    if not report:
        raise PermanentError("final report artifact missing")                             # 5
    if db.one("SELECT 1 FROM email_outbox WHERE project_id=? AND cycle=? AND state='SENT'", row["project_id"], row["cycle"]):
        raise PermanentError("a confirmed final email already exists for this closure")   # 6
    disp = json.loads(gh.get_file(root + "reviews/jarvis/finding-dispositions.json", closure["delivery_sha"]) or "{}")
    return {"project": project, "closure": closure, "approval": approval, "delivery": d,
            "verification": json.loads(ver_raw), "report": report, "dispositions": disp.get("dispositions", [])}


def compose(ctx: dict, rfc822_message_id: str) -> EmailMessage:
    p, cl, ap, ver = ctx["project"], ctx["closure"], ctx["approval"], ctx["verification"]
    sha, root = cl["delivery_sha"], f"projects/{p['id']}"
    blob = f"{GITHUB_URL}/blob/{sha}/{root}"
    checks = "\n".join(f"  - {c.get('name')}: {c.get('result')} — {c.get('evidence', '')}" for c in ver.get("checks", []))
    lims = "\n".join(f"  - {x}" for x in ver.get("limitations", [])) or "  - none recorded"
    disp = "\n".join(f"  - {x.get('finding_id')}: {x.get('disposition')}" + (f" — {x['reason']}" if x.get("reason") else "")
                     for x in ctx["dispositions"]) or "  - no council findings"
    body = f"""Project {p['id']} — {p['title']} has been approved and closed by G.

EXACT APPROVED VERSION
  Version {cl['cycle']} · delivery commit {sha}
  {GITHUB_URL}/commit/{sha}

FINAL DOCUMENTS AND DELIVERABLES
  Delivery:                {blob}/delivery/delivery.md
  Final report:            {blob}/delivery/final-report.md
  Implementation document: {blob}/documents/implementation-document.md
  Development outputs:     {GITHUB_URL}/tree/{sha}/{root}/development
  Verification report:     {blob}/verification/verification-report.json

VERIFICATION RESULTS ({ver.get('status')})
{checks}
  Limitations:
{lims}

COUNCIL OUTCOME AND FINDING DISPOSITIONS
  Council package: {p['current_package_sha']}
{disp}

G'S APPROVAL AND CLOSURE
  Approved by @{ap['actor']} at {ap['created_at']} — {ap['comment_url'] or 'comment #' + str(ap['comment_id'])}
  Closure recorded {cl['closed_at']}; tracking issue {GITHUB_URL}/issues/{p['issue_number']} closed {cl['issue_closed_at']}

COMPLETION SUMMARY, DELIVERED SCOPE AND HANDOVER (final report)
----------------------------------------------------------------
{ctx['report']}
"""
    msg = EmailMessage()
    msg["From"] = FINAL_REPORT_FROM
    msg["To"] = FINAL_REPORT_TO          # fixed; no CC/BCC ever
    msg["Subject"] = f"[Project Closed] {p['id']} — {p['title']} — Version {cl['cycle']}"
    msg["Date"] = formatdate(localtime=False)
    msg["Message-ID"] = rfc822_message_id
    msg.set_content(body)
    return msg


def send_final_report(engine, row) -> str:
    """Send one outbox row if all closure checks pass."""
    db = engine.db
    if row["state"] == "SENT":
        return "already_sent"
    if engine.gmail is None:
        _set(db, row["id"], state="BLOCKED", last_error="Gmail adapter not configured")
        return "blocked"
    try:
        ctx = check_preconditions(engine, row)
        if engine.gmail.authorized_address() != FINAL_REPORT_FROM:
            raise PermanentError("authorized Gmail account is not the JARVIS sender")
        msg = compose(ctx, row["rfc822_message_id"])
        assert msg["To"] == FINAL_REPORT_TO and not msg["Cc"] and not msg["Bcc"]
    except NotReady as e:
        _set(db, row["id"], next_attempt_at=iso(utcnow() + timedelta(minutes=5)), last_error=str(e))
        return "not_ready"
    except PermanentError as e:
        _set(db, row["id"], state="BLOCKED", last_error=str(e))
        record_audit_event(db, actor="JARVIS", action="email.final_report", outcome="BLOCKED",
                           project_id=row["project_id"], cycle=row["cycle"], detail={"reason": str(e)})
        return "blocked"
    except DefinitePreSendFailure as e:
        _set(db, row["id"], next_attempt_at=iso(utcnow() + timedelta(minutes=5)), last_error=str(e))
        return "retry"

    # Persist SENDING before the call so a crash is detected as uncertain.
    _set(db, row["id"], state="SENDING", attempts=row["attempts"] + 1, attempt_started_at=iso(),
         subject=str(msg["Subject"]))
    try:
        res = engine.gmail.send_raw(msg.as_bytes())
    except DefinitePreSendFailure as e:
        delays = engine.s.retry_delays_minutes
        delay = delays[min(row["attempts"], len(delays) - 1)]
        _set(db, row["id"], state="PENDING", next_attempt_at=iso(utcnow() + timedelta(minutes=delay)), last_error=str(e))
        return "retry"
    except UncertainSendOutcome as e:
        _set(db, row["id"], state="SEND_UNCERTAIN", last_error=str(e))
        record_audit_event(db, actor="JARVIS", action="email.final_report", outcome="SEND_UNCERTAIN",
                           project_id=row["project_id"], cycle=row["cycle"])
        return "uncertain"
    except PermanentError as e:
        _set(db, row["id"], state="BLOCKED", last_error=str(e))
        return "blocked"
    _set(db, row["id"], state="SENT", gmail_message_id=res.get("id"), accepted_at=iso(), last_error=None)
    record_audit_event(db, actor="JARVIS", action="email.final_report", outcome="SENT(api-accepted)",
                       project_id=row["project_id"], cycle=row["cycle"],
                       detail={"gmail_message_id": res.get("id"), "to": FINAL_REPORT_TO})
    return "sent"


def reconcile_uncertain(engine, row) -> str:
    """Look for the message in the mailbox by its fixed Message-ID before any resend."""
    db = engine.db
    try:
        found = engine.gmail.find_sent_by_message_id(row["rfc822_message_id"])
    except DefinitePreSendFailure as e:
        _set(db, row["id"], last_error=f"reconcile failed: {e}")
        return "reconcile_failed"
    if found:
        _set(db, row["id"], state="SENT", gmail_message_id=found["id"], accepted_at=iso(),
             last_error="reconciled after uncertain outcome")
        record_audit_event(db, actor="JARVIS", action="email.reconcile", outcome="SENT(found)",
                           project_id=row["project_id"], cycle=row["cycle"])
        return "reconciled_sent"
    started = parse_iso(row["attempt_started_at"]) if row["attempt_started_at"] else utcnow()
    if utcnow() - started < timedelta(minutes=engine.s.email_reconcile_wait_minutes):
        return "waiting"
    _set(db, row["id"], state="PENDING", next_attempt_at=iso(), last_error="not found after reconcile window")
    record_audit_event(db, actor="JARVIS", action="email.reconcile", outcome="NOT_FOUND→PENDING",
                       project_id=row["project_id"], cycle=row["cycle"])
    return "requeued"


def process_email_outbox(engine) -> dict:
    """Closure email recovery job (every 5 minutes)."""
    db, out = engine.db, {}
    stale = iso(utcnow() - timedelta(minutes=UNCERTAIN_STALE_SENDING_MINUTES))
    with db.tx() as c:  # crashed mid-send -> uncertain
        c.execute("UPDATE email_outbox SET state='SEND_UNCERTAIN', last_error='process stopped during send',"
                  " updated_at=? WHERE state='SENDING' AND attempt_started_at<?", (iso(), stale))
    if engine.gmail is None:
        return {"skipped": "gmail not configured"}
    for row in db.all("SELECT * FROM email_outbox WHERE state='SEND_UNCERTAIN'"):
        out[row["email_key"]] = reconcile_uncertain(engine, row)
    for row in db.all("SELECT * FROM email_outbox WHERE state='PENDING' AND (next_attempt_at IS NULL OR next_attempt_at<=?)",
                      iso()):
        out[row["email_key"]] = send_final_report(engine, row)
    return out
