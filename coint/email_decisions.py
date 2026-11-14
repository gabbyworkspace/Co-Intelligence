"""G's final decision by email reply (optional channel, G's choice 2026-11-14).

G may answer a "[Review Required]" package by email instead of in the JARVIS
chat. A reply counts only if ALL of these hold:

  1. Sender: the From address is one of FOUNDER_DECISION_EMAILS (default g@resystem.org,baileys.resystem@gmail.com).
  2. Authentication: Gmail's own Authentication-Results header (authserv-id
     mx.google.com, the top-most one) shows dmarc=pass, or dkim=pass for the
     From domain. Headers added by the sender are ignored, so they cannot fake this.
  3. Binding to the exact version: the message replies in the review-package
     thread (References/In-Reply-To holds that email's Message-ID), or its new
     text names `<PROJECT_ID> v<N>` and the full 40-character delivery SHA.
  4. Current version: that delivery is still the one awaiting G's final review.
  5. Explicit action: the new text (quoted history ignored) contains exactly one of
     APPROVE AND CLOSE or REQUEST CHANGES. Requests for changes need `Route:
     documents|development` and at least one change line.

Accepted replies become the same founder decision as a chat decision: JARVIS
publishes the decision reference, KITT records it on GitHub, and only then does
closure or Version N+1 happen. Every reply examined is logged in
`email_decisions` and the audit log; rejected replies are reported on the
tracking issue.
"""
from __future__ import annotations

import hashlib
import re
from email.utils import parseaddr

from .audit import record_audit_event
from .db import iso
from .kitt_session import Attestation

QUOTE_START = re.compile(r"^(On .+wrote:|-{2,}\s*Original Message\s*-{2,}|From: .+|_{5,})\s*$", re.I)
SHA_RE = re.compile(r"\b[0-9a-f]{40}\b")
# G 2026-11-14: a short close reply in the version's review thread counts as APPROVE AND CLOSE.
SHORT_CLOSE = re.compile(r"^\s*(close|closed|approve|approved|approve and close)\s*[.!]*\s*$", re.I)


def new_text(body: str) -> str:
    """Drop quoted history: '>' lines and everything after a reply header."""
    out = []
    for line in body.replace("\r\n", "\n").split("\n"):
        if QUOTE_START.match(line.strip()):
            break
        if line.lstrip().startswith(">"):
            continue
        out.append(line)
    return "\n".join(out).strip()


def parse_decision(text: str) -> dict:
    up = text.upper()
    approve, changes = "APPROVE AND CLOSE" in up, "REQUEST CHANGES" in up
    if approve == changes:
        raise ValueError("reply must contain exactly one of APPROVE AND CLOSE or REQUEST CHANGES")
    if approve:
        return {"decision_type": "delivery_approve_close"}
    route = re.search(r"^\s*route\s*:\s*(documents|development)\s*$", text, re.I | re.M)
    items = [m.group(1).strip() for m in re.finditer(r"^\s*(?:[-*•]|\d+[.)])\s+(.+)$", text, re.M)]
    if not route or not items:
        raise ValueError("REQUEST CHANGES needs 'Route: documents' or 'Route: development' and at least one "
                         "'- change' line")
    return {"decision_type": "delivery_changes", "route": route.group(1).lower(), "changes": items}


def gmail_authenticated(headers: list[tuple[str, str]], from_addr: str) -> bool:
    domain = from_addr.rsplit("@", 1)[-1].lower()
    ar = [v for k, v in headers if k.lower() == "authentication-results"]
    if not ar or not ar[0].strip().lower().startswith("mx.google.com"):
        return False
    top = ar[0].lower()
    if re.search(r"\bdmarc=pass\b", top):
        return True
    for m in re.finditer(r"dkim=pass[^;]*?header\.(?:i|d)=@?([a-z0-9.-]+)", top):
        if m.group(1) == domain or m.group(1).endswith("." + domain):
            return True
    return False


def process_email_decisions(engine) -> dict:
    """Scheduled every 5 minutes. Reads the JARVIS inbox for founder replies."""
    s, db, gmail = engine.s, engine.db, engine.gmail
    if gmail is None or not s.email_decisions_enabled:
        return {"skipped": "email decisions disabled or Gmail not configured"}
    allowed = {a.lower() for a in s.founder_decision_emails}
    query = "in:inbox newer_than:30d (" + " OR ".join(f"from:{a}" for a in sorted(allowed)) + ")"
    out = {}
    for mid in gmail.list_message_ids(query):
        if db.one("SELECT 1 FROM email_decisions WHERE gmail_id=?", mid):
            continue
        out[mid] = _handle(engine, gmail.get_full_message(mid), allowed)
    return out


def _log(db, msg, outcome, detail=None, decision_id=None, project_id=None):
    with db.tx() as c:
        c.execute("INSERT OR IGNORE INTO email_decisions VALUES (?,?,?,?,?,?,?)",
                  (msg["id"], msg.get("from", ""), msg.get("message_id", ""), outcome, detail, decision_id, iso()))
    record_audit_event(db, actor=msg.get("from") or "unknown", action="email_decision.examine", outcome=outcome,
                       project_id=project_id, detail={"gmail_id": msg["id"], "detail": detail,
                                                     "decision_id": decision_id})
    return outcome


def _handle(engine, msg, allowed) -> str:
    db = engine.db
    headers = msg["headers"]
    h = {k.lower(): v for k, v in reversed(headers)}  # first occurrence wins
    from_addr = parseaddr(h.get("from", ""))[1].lower()
    msg["from"], msg["message_id"] = from_addr, h.get("message-id", "")
    if from_addr not in allowed:
        return _log(db, msg, "ignored", "sender not an authorized founder address")
    if not gmail_authenticated(headers, from_addr):
        return _log(db, msg, "rejected", "Gmail did not authenticate the sender (no dmarc/dkim pass)")
    text = new_text(msg.get("body", ""))
    short = bool(SHORT_CLOSE.match(text))
    if not short and "APPROVE AND CLOSE" not in text.upper() and "REQUEST CHANGES" not in text.upper():
        return _log(db, msg, "ignored", "no decision keyword")
    # Bind to an exact review package: thread reference, or explicit project/version/SHA in the new text.
    refs = set(re.findall(r"<[^>]+>", " ".join([h.get("in-reply-to", ""), h.get("references", "")])))
    pkg = None
    for row in db.all("SELECT * FROM email_outbox WHERE kind='review_package' AND state='SENT'"):
        if row["rfc822_message_id"] in refs:
            pkg = row
            break
    if pkg is None and short:
        return _log(db, msg, "rejected", "short close reply must be in the review-package thread")
    if pkg is None:
        for row in db.all("SELECT * FROM email_outbox WHERE kind='review_package' AND state='SENT'"):
            if row["delivery_sha"] in SHA_RE.findall(text) and \
                    re.search(rf"\b{re.escape(row['project_id'])}\s+v{row['cycle']}\b", text, re.I):
                pkg = row
                break
    if pkg is None:
        return _log(db, msg, "rejected", "reply is not bound to a review package (thread or project vN + full SHA)")
    try:
        dec = {"decision_type": "delivery_approve_close"} if short else parse_decision(text)
    except ValueError as e:
        engine_reject = _log(db, msg, "rejected", str(e), project_id=pkg["project_id"])
        _comment(engine, pkg["project_id"], f"⛔ Email from {from_addr} about Version {pkg['cycle']} "
                                            f"(`{pkg['delivery_sha']}`) was not accepted as a decision: {e}")
        return engine_reject
    did = "email-" + re.sub(r"[^A-Za-z0-9-]", "", msg["id"])[:56]
    att = Attestation(from_addr, 0, "gmail", hashlib.sha256(msg["message_id"].encode()).hexdigest(), "email")
    req = {"decision_id": did, "project_id": pkg["project_id"], "cycle": pkg["cycle"], "sha": pkg["delivery_sha"],
           "founder_statement": text[:4000], **dec}
    res = engine.founder_decision(att, req)
    return _log(db, msg, res["outcome"], res.get("message"), did, pkg["project_id"])


def _comment(engine, pid, body):
    project = engine.project(pid)
    if project:
        with engine.db.tx() as c:
            engine.comment(c, project, body)
        engine.dispatch_outbox()


__all__ = ["process_email_decisions", "parse_decision", "new_text", "gmail_authenticated"]
