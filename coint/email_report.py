"""JARVIS Gmail sends (durable outbox, never blind duplicates):

  review_package  Step 11: "[Review Required]" package to baileys.resystem@gmail.com
                  when the finalized delivery reaches G's final review.
  final_report    Step 12: "[Project Closed]" report to g@resystem.org, only after
                  completed development, validated JARVIS-session approval, KITT's
                  GitHub record of it, and recorded closure.
"""
from __future__ import annotations

import json
from datetime import timedelta
from email.message import EmailMessage
from email.utils import formatdate

from .audit import record_audit_event
from .config import FINAL_REPORT_FROM, FINAL_REPORT_TO, GITHUB_URL, REVIEW_PACKAGE_TO
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
    att = db.one("SELECT * FROM founder_decisions WHERE decision_id=?", approval["attestation_id"] or "")
    if approval["channel"] != "jarvis_session" or not att or att["outcome"] != "accepted" or \
            att["channel"] != "jarvis_session" or att["decision_type"] != "delivery_approve_close" or \
            att["sha"] != approval["sha"] or att["github_login"].lower() != engine.s.founder_login.lower() or \
            att["oauth_client_id"] != engine.s.jarvis_oauth_client_id:
        raise PermanentError("approval is not backed by a validated founder decision from the JARVIS session")  # 3
    rec = [t for t in db.all("SELECT * FROM tasks WHERE project_id=? AND cycle=? AND task_type='record_founder_decision'"
                             " AND state='COMPLETED'", row["project_id"], row["cycle"])
           if json.loads(t["manifest"])["context"].get("decision_id") == att["decision_id"]]
    if not rec:
        raise PermanentError("KITT has not recorded G's approval on GitHub")                # 3
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
    if db.one("SELECT 1 FROM email_outbox WHERE project_id=? AND cycle=? AND state='SENT' AND kind='final_report'",
              row["project_id"], row["cycle"]):
        raise PermanentError("a confirmed final email already exists for this closure")   # 6
    disp = json.loads(gh.get_file(root + "reviews/jarvis/finding-dispositions.json", closure["delivery_sha"]) or "{}")
    return {"project": project, "closure": closure, "approval": approval, "delivery": d,
            "verification": json.loads(ver_raw), "report": report, "dispositions": disp.get("dispositions", []),
            "kitt_record_sha": rec[0]["published_sha"]}


class Superseded(Exception):
    """The review package is no longer for the current delivery."""


def check_review_preconditions(engine, row) -> dict:
    db, gh = engine.db, engine.gh
    project = engine.project(row["project_id"])
    if project["status"] == "CLOSED" or project["stage"] != "FOUNDER_FINAL_REVIEW" or \
            project["current_cycle"] != row["cycle"] or project["current_delivery_sha"] != row["delivery_sha"]:
        raise Superseded("delivery is no longer awaiting G's final review")
    d = db.one("SELECT * FROM deliveries WHERE project_id=? AND cycle=? AND delivery_sha=?",
               row["project_id"], row["cycle"], row["delivery_sha"])
    if not d:
        raise PermanentError("no delivery record for this version")
    root, sha = f"projects/{project['id']}/", row["delivery_sha"]
    files = {k: gh.get_file(root + k, sha) for k in (
        "delivery/final-report.md", "verification/verification-report.json", "reviews/kitt/delivery-review.md")}
    if not files["delivery/final-report.md"] or not files["verification/verification-report.json"]:
        raise PermanentError("review package artifacts missing at the delivery SHA")
    return {"project": project, "delivery": d, "files": files,
            "verification": json.loads(files["verification/verification-report.json"])}


def compose_review(ctx: dict, row) -> EmailMessage:
    p, ver, sha = ctx["project"], ctx["verification"], row["delivery_sha"]
    blob = f"{GITHUB_URL}/blob/{sha}/projects/{p['id']}"
    checks = "\n".join(f"  - {c.get('name')}: {c.get('result')} — {c.get('evidence', '')}" for c in ver.get("checks", []))
    lims = "\n".join(f"  - {x}" for x in ver.get("limitations", [])) or "  - none recorded"
    body = f"""REVIEW REQUIRED — this is NOT a closure notice.

Project:          {p['id']} — {p['title']}
Cycle / version:  Version {row['cycle']}
Exact delivery:   {sha}
                  {GITHUB_URL}/commit/{sha}

Delivery:         {blob}/delivery/delivery.md
Final report:     {blob}/delivery/final-report.md
Verification:     {blob}/verification/verification-report.json
KITT review:      {blob}/reviews/kitt/delivery-review.md

VERIFICATION RESULTS ({ver.get('status')})
{checks}

LIMITATIONS
{lims}

HOW TO DECIDE
G reviews and decides in the JARVIS chat: APPROVE AND CLOSE or REQUEST CHANGES.
No email reply is required, and replies to this email are not treated as decisions.

COMPLETION SUMMARY (final report draft)
---------------------------------------
{ctx['files']['delivery/final-report.md']}
"""
    msg = EmailMessage()
    msg["From"] = FINAL_REPORT_FROM
    msg["To"] = REVIEW_PACKAGE_TO
    msg["Subject"] = f"[Review Required] {p['id']} — {p['title']} — Version {row['cycle']} — {sha[:12]}"
    msg["Date"] = formatdate(localtime=False)
    msg["Message-ID"] = row["rfc822_message_id"]
    msg.set_content(body)
    return msg


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
  Approved by G (@{ap['actor']}) at {ap['created_at']} in the authorized JARVIS session
  Founder decision ID: {ap['attestation_id']}
  Recorded on GitHub by KITT: {GITHUB_URL}/commit/{ctx['kitt_record_sha']}
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


FIXED_RECIPIENT = {"final_report": FINAL_REPORT_TO, "review_package": REVIEW_PACKAGE_TO}


def _notify_failure(engine, row, text):
    project = engine.project(row["project_id"])
    if project and row["kind"] == "review_package":
        with engine.db.tx() as c:
            engine.comment(c, project, f"⚠️ Review package email to {REVIEW_PACKAGE_TO} for Version {row['cycle']} "
                                       f"(`{row['delivery_sha']}`): {text}", f"remail:{row['id']}:{row['attempts']}:{text[:20]}")
        engine.dispatch_outbox()


def send_email(engine, row) -> str:
    """Send one outbox row if all checks for its kind pass."""
    db = engine.db
    if row["state"] == "SENT":
        return "already_sent"
    if engine.gmail is None:
        _set(db, row["id"], state="BLOCKED", last_error="Gmail sending integration not configured")
        _notify_failure(engine, row, "not sent — Gmail sending integration not configured")
        return "blocked"
    try:
        if row["to_addr"] != FIXED_RECIPIENT[row["kind"]]:
            raise PermanentError("recipient does not match the fixed recipient for this email kind")
        if row["kind"] == "review_package":
            msg = compose_review(check_review_preconditions(engine, row), row)
        else:
            msg = compose(check_preconditions(engine, row), row["rfc822_message_id"])
        if engine.gmail.authorized_address() != FINAL_REPORT_FROM:
            raise PermanentError("authorized Gmail account is not the JARVIS sender")
        assert msg["To"] == FIXED_RECIPIENT[row["kind"]] and not msg["Cc"] and not msg["Bcc"]
    except Superseded as e:
        _set(db, row["id"], state="CANCELLED", last_error=str(e))
        return "cancelled"
    except NotReady as e:
        _set(db, row["id"], next_attempt_at=iso(utcnow() + timedelta(minutes=5)), last_error=str(e))
        return "not_ready"
    except PermanentError as e:
        _set(db, row["id"], state="BLOCKED", last_error=str(e))
        record_audit_event(db, actor="JARVIS", action=f"email.{row['kind']}", outcome="BLOCKED",
                           project_id=row["project_id"], cycle=row["cycle"], detail={"reason": str(e)})
        _notify_failure(engine, row, f"not sent — {e}")
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
        record_audit_event(db, actor="JARVIS", action=f"email.{row['kind']}", outcome="SEND_UNCERTAIN",
                           project_id=row["project_id"], cycle=row["cycle"])
        _notify_failure(engine, row, "outcome uncertain — reconciling with the mailbox before any resend")
        return "uncertain"
    except PermanentError as e:
        _set(db, row["id"], state="BLOCKED", last_error=str(e))
        _notify_failure(engine, row, f"not sent — {e}")
        return "blocked"
    _set(db, row["id"], state="SENT", gmail_message_id=res.get("id"), accepted_at=iso(), last_error=None)
    record_audit_event(db, actor="JARVIS", action=f"email.{row['kind']}", outcome="SENT(api-accepted)",
                       project_id=row["project_id"], cycle=row["cycle"],
                       detail={"gmail_message_id": res.get("id"), "to": row["to_addr"]})
    return "sent"


send_final_report = send_email  # backwards-compatible name


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
        out[row["email_key"]] = send_email(engine, row)
    return out
