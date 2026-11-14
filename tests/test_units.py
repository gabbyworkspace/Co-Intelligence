import hashlib
import hmac
import json
from datetime import datetime, timezone

import pytest

from coint import queue as Q
from coint.commands import ParseError, parse_command
from coint.config import ConfigError, load_settings
from coint.errors import AuthError, InvalidInput, TransientError
from coint.scheduler import JOBS, cron_matches, founder_reminders
from coint.webhook import WebhookRejected, verify_webhook
from conftest import BRIEF
from fakes import FOUNDER, default_output, make_settings

SHA = "a" * 40


# ---------------------------------------------------------------- webhook
def _sign(body, secret="s3cret"):
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _hdr(body, event="issue_comment", sig=None):
    return {"X-Hub-Signature-256": sig or _sign(body), "X-GitHub-Event": event,
            "X-GitHub-Delivery": "72d3162e-cc78-11e3-81ab-4c9367dc0958"}


def test_webhook_valid(tmp_path):
    s = make_settings(str(tmp_path / "d"))
    body = json.dumps({"action": "created", "repository": {"full_name": "gabbyworkspace/Co-Intelligence"}}).encode()
    ev = verify_webhook(s, _hdr(body), body)
    assert ev.event == "issue_comment" and ev.action == "created"


@pytest.mark.parametrize("mutate,status", [
    (lambda b, h: h.update({"X-Hub-Signature-256": "sha256=" + "0" * 64}), 401),
    (lambda b, h: h.pop("X-Hub-Signature-256"), 401),
    (lambda b, h: h.update({"X-GitHub-Event": "push"}), 202),
    (lambda b, h: h.update({"X-GitHub-Delivery": "bad delivery!"}), 400),
])
def test_webhook_rejections(tmp_path, mutate, status):
    s = make_settings(str(tmp_path / "d"))
    body = json.dumps({"repository": {"full_name": "gabbyworkspace/Co-Intelligence"}}).encode()
    h = _hdr(body)
    mutate(body, h)
    with pytest.raises(WebhookRejected) as e:
        verify_webhook(s, h, body)
    assert e.value.status == status


def test_webhook_wrong_repo(tmp_path):
    s = make_settings(str(tmp_path / "d"))
    body = json.dumps({"repository": {"full_name": "evil/Co-Intelligence"}}).encode()
    with pytest.raises(WebhookRejected) as e:
        verify_webhook(s, _hdr(body), body)
    assert e.value.status == 403


# ---------------------------------------------------------------- parser
def test_parse_only_top_level():
    assert parse_command("hello\n/project pause") is None
    assert parse_command("> /project pause") is None
    assert parse_command("```\n/project pause\n```") is None
    assert parse_command("  /project pause") is None
    assert parse_command("/other thing") is None
    assert parse_command("/project pause").name == "project pause"


def test_parse_args_and_payloads():
    c = parse_command(f"/initial approve 1 {SHA}")
    assert c.args == {"cycle": 1, "sha": SHA}
    with pytest.raises(ParseError):
        parse_command(f"/initial changes 1 {SHA}")  # needs changes list
    with pytest.raises(ParseError):
        parse_command("/initial approve 0 " + SHA)
    with pytest.raises(ParseError):
        parse_command("/initial approve 1 abc123")
    with pytest.raises(ParseError):
        parse_command(f"/delivery changes 1 {SHA}\n```json\n{{\"changes\":[\"x\"]}}\n```")  # missing route
    c = parse_command(f"/delivery changes 2 {SHA}\n```json\n{{\"changes\":[\"x\"],\"route\":\"development\"}}\n```")
    assert c.payload["route"] == "development"
    with pytest.raises(ParseError):
        parse_command("/project start\n```json\n{\"title\": \"x\"}\n```")
    with pytest.raises(ParseError):
        parse_command(f"/handoff JARVIS doc_review 1 {SHA}")  # no manifest
    with pytest.raises(ParseError):
        parse_command(f"/handoff NOBODY doc_review 1 {SHA}\n```json\n{{}}\n```")


def test_quoted_json_block_is_not_payload():
    body = "/project start\n> ```json\n> " + json.dumps(BRIEF) + "\n> ```"
    with pytest.raises(ParseError):
        parse_command(body)


# ---------------------------------------------------------------- config
def test_founder_username_required(monkeypatch):
    monkeypatch.delenv("FOUNDER_GITHUB_USERNAME", raising=False)
    with pytest.raises(ConfigError):
        load_settings()


def test_recipient_cannot_be_overridden(monkeypatch):
    monkeypatch.setenv("FOUNDER_GITHUB_USERNAME", "someone")
    monkeypatch.setenv("FINAL_REPORT_TO", "attacker@example.com")
    with pytest.raises(ConfigError):
        load_settings()


def test_default_adapters_unsupported(monkeypatch):
    from coint.adapters import build_adapter
    monkeypatch.setenv("FOUNDER_GITHUB_USERNAME", "someone")
    s = load_settings()
    assert all(build_adapter(c).problems() for c in s.adapters.values())


# ---------------------------------------------------------------- authz / commands
def test_edits_and_bots_not_executed(h):
    body = "/project start\n```json\n" + json.dumps(BRIEF) + "\n```"
    assert h.say(body, created_at="2026-01-01T00:00:00Z", updated_at="2026-01-01T00:05:00Z") == "rejected"
    assert h.say(body, actor="co-intel[bot]") == "bot"
    assert h.say(body, actor="other", actor_type="Bot") == "bot"
    assert h.db.one("SELECT COUNT(*) n FROM projects")["n"] == 0


def test_comment_edited_webhook_ignored(h):
    from coint.webhook import VerifiedEvent, persist_delivery
    ev = VerifiedEvent("dddd-1111", "issue_comment", "edited",
                       {"comment": {"id": 1}, "sender": {"login": FOUNDER}, "issue": {"number": 7}})
    persist_delivery(h.db, ev)
    assert h.engine.process_delivery("dddd-1111") == "ignored_edit"


def test_pause_blocks_claims_and_resume(h):
    h.start()
    assert h.say("/project pause", actor="kitt-bot") == "rejected"
    assert h.say("/project pause") == "rejected"          # GitHub comment, even from G
    assert h.decide("project_pause", login="kitt-bot") == "rejected"
    assert h.decide("project_pause") == "accepted"
    tid = h.tasks(task_type="create_document")[0]["id"]
    assert Q.claim_task(h.db, tid, "w", 60) is False
    assert h.decide("project_resume") == "accepted"
    h.run_all()
    assert h.project()["stage"] == "FOUNDER_INITIAL_REVIEW"


def test_handoff_by_wrong_identity_rejected(make_h):
    h = make_h(manual=("KITT",))
    h.start()
    t = h.tasks(task_type="create_document")[0]
    sha = h.gh.commit_files("co-intel/CI-TEST", {"projects/CI-TEST/brief/brief.json": "{}",
                                                 "projects/CI-TEST/documents/project-document.md": "#"}, "m")
    m = {"project_id": "CI-TEST", "task_id": t["id"], "revision": 1, "source_role": "KITT",
         "files": ["brief/brief.json", "documents/project-document.md"], "expected_outputs": [], "next_action": "x"}
    body = f"/handoff FOUNDER create_document 1 {sha}\n```json\n{json.dumps(m)}\n```"
    assert h.say(body, actor="jarvis-bot") == "rejected"
    # unpublished file -> rejected
    m2 = dict(m, files=["documents/missing.md"])
    assert h.say(f"/handoff FOUNDER create_document 1 {sha}\n```json\n{json.dumps(m2)}\n```", actor="kitt-bot") == "rejected"
    # unknown commit -> rejected
    assert h.say(f"/handoff FOUNDER create_document 1 {'b' * 40}\n```json\n{json.dumps(m)}\n```",
                 actor="kitt-bot") == "rejected"


def test_initial_changes_revises_same_cycle(h):
    h.start()
    h.run_all()
    sha = h.project()["current_document_sha"]
    assert h.decide("initial_changes", cycle=1, sha=sha) == "rejected"  # changes list required
    assert h.decide("initial_changes", cycle=1, sha=sha, changes=["add risks"]) == "accepted"
    p = h.project()
    assert p["current_cycle"] == 1 and p["assignment_rev"] == 2 and p["stage"] == "KITT_DRAFT"
    h.run_all()
    p = h.project()
    assert p["stage"] == "FOUNDER_INITIAL_REVIEW" and p["current_document_sha"] != sha
    assert h.decide("initial_approve", cycle=1, sha=sha) == "rejected"  # stale document


# ---------------------------------------------------------------- loop limit
def test_revision_loop_limit_blocks_and_requests_founder(make_h):
    def never_ok(role, tt, meta, inputs):
        out = default_output(role, tt, meta, inputs)
        if tt == "freeze_council_package":
            out["verdict"] = "feedback_not_addressed"
            out["files"] = {"reviews/jarvis/doc-review.md": "still open"}
        return out
    h = make_h(scripts={"JARVIS": never_ok})
    h.to_final_review()
    p = h.project()
    assert p["stage"] == "FOUNDER_DECISION"
    assert len(h.tasks(task_type="finalize_documents")) == 3
    assert h.tasks(role="FOUNDER")[-1]["state"] == "WAITING_FOUNDER"
    assert h.decide("project_resume") == "rejected"  # decision required
    h.adapters["JARVIS"].script = None
    assert h.decide("project_resume", decisions=["accept doc as-is"]) == "accepted"
    h.run_all()
    assert h.project()["stage"] == "FOUNDER_FINAL_REVIEW"


# ---------------------------------------------------------------- failures
def test_transient_retries_then_fail(make_h):
    def boom(*a):
        raise TransientError("503")
    h = make_h(scripts={"KITT": boom})
    h.start()
    h.run_all()
    t = h.tasks(task_type="create_document")[0]
    assert t["state"] == "FAILED" and t["attempts"] == 4  # 1 + 3 retries


def test_permanent_errors_block(make_h):
    def auth(*a):
        raise AuthError("bad key")
    h = make_h(scripts={"KITT": auth})
    h.start()
    h.run_all()
    t = h.tasks(task_type="create_document")[0]
    assert t["state"] == "BLOCKED" and t["attempts"] == 1


def test_output_path_and_version_validation(make_h):
    def evil(role, tt, meta, inputs):
        out = default_output(role, tt, meta, inputs)
        out["files"]["../../.github/workflows/x.yml"] = "pwn"
        return out
    h = make_h(scripts={"KITT": evil})
    h.start()
    h.run_all()
    assert h.tasks(task_type="create_document")[0]["state"] == "BLOCKED"

    def wrong_version(role, tt, meta, inputs):
        out = default_output(role, tt, meta, inputs)
        out["input_sha"] = "c" * 40
        return out
    import os
    from conftest import Harness
    os.makedirs(h.path + ".b", exist_ok=True)
    import pathlib
    h2 = Harness(pathlib.Path(h.path + ".b"), scripts={"KITT": wrong_version})
    h2.start()
    h2.run_all()
    t = h2.tasks(task_type="create_document")[0]
    assert t["state"] == "BLOCKED" and "input" in t["error"]


def test_checkpoint_skips_model_on_retry(h):
    h.start()
    tid = h.tasks(task_type="create_document")[0]["id"]
    assert Q.claim_task(h.db, tid, h.engine.worker_id, 300)
    out = default_output("KITT", "create_document", {"input_sha": h.tasks()[0]["input_sha"]}, {})
    Q.save_checkpoint(h.db, tid, h.engine.worker_id, out)
    with h.db.tx() as c:
        c.execute("UPDATE tasks SET state='QUEUED', lease_owner=NULL WHERE id=?", (tid,))
    h.run_all()
    assert h.adapters["KITT"].calls == []
    assert h.project()["stage"] == "FOUNDER_INITIAL_REVIEW"


def test_artifacts_carry_cycle_revision_metadata(h):
    h.start()
    h.run_all()
    sha = h.project()["current_document_sha"]
    doc = h.gh.get_file("projects/CI-TEST/documents/project-document.md", sha)
    meta = json.loads(doc.split("coint-meta: ", 1)[1].split(" -->", 1)[0])
    assert meta["cycle"] == 1 and meta["revision"] == 1 and meta["role"] == "KITT"
    brief = json.loads(h.gh.get_file("projects/CI-TEST/brief/brief.json", sha))
    assert brief["_coint"]["input_sha"] == meta["input_sha"]
    assert h.db.one("SELECT COUNT(*) n FROM handoffs")["n"] == 1


# ---------------------------------------------------------------- scheduler
def test_cron_expressions():
    assert JOBS["founder_reminders"] == "17 5 * * *"
    assert cron_matches("17 5 * * *", datetime(2026, 11, 14, 5, 17, tzinfo=timezone.utc))
    assert not cron_matches("17 5 * * *", datetime(2026, 11, 14, 9, 17, tzinfo=timezone.utc))
    assert cron_matches("*/5 * * * *", datetime(2026, 1, 1, 0, 35))
    assert cron_matches("2,17,32,47 * * * *", datetime(2026, 1, 1, 3, 47))
    assert not cron_matches("2,17,32,47 * * * *", datetime(2026, 1, 1, 3, 45))


def test_reminder_once_per_day_and_never_advances(h):
    h.start()
    h.run_all()
    assert founder_reminders(h.engine) == ["CI-TEST"]
    assert founder_reminders(h.engine) == []
    assert h.project()["stage"] == "FOUNDER_INITIAL_REVIEW"


def test_invalid_input_unknown_commit(h):
    with pytest.raises(InvalidInput):
        h.gh.get_commit("e" * 40)


# ---------------------------------------------------------------- trusted KITT session
def test_kitt_comment_is_not_approval_evidence(h):
    h.start()
    h.run_all()
    sha = h.project()["current_document_sha"]
    claim = f"/initial approve 1 {sha}\n\nG approved this in our chat."
    assert h.say(claim, actor="kitt-bot") == "rejected"
    assert h.project()["stage"] == "FOUNDER_INITIAL_REVIEW"
    assert any("not approval evidence" in b for _, b in h.gh.comments)


def test_decision_bound_to_project_cycle_version(h):
    h.start()
    h.run_all()
    sha = h.project()["current_document_sha"]
    assert h.decide("initial_approve", cycle=2, sha=sha) == "rejected"
    assert h.decide("initial_approve", cycle=1, sha="d" * 40) == "rejected"
    assert h.decide("initial_approve", project_id="CI-NOPE", cycle=1, sha=sha) == "rejected"
    assert h.decide("delivery_approve_close", cycle=1, sha=sha) == "rejected"  # wrong stage
    assert h.decide("initial_approve", cycle=1, sha=sha, decision_id="same-id-123") == "accepted"
    # replaying the id with different content is refused
    res = h.engine.founder_decision(
        __import__("coint.kitt_session", fromlist=["Attestation"]).Attestation(FOUNDER, 1, "kitt-app", "f" * 64),
        {"decision_id": "same-id-123", "decision_type": "initial_changes", "project_id": "CI-TEST",
         "cycle": 1, "sha": sha, "changes": ["x"], "founder_statement": "x"})
    assert res["status"] == 409
    rows = h.db.all("SELECT outcome FROM founder_decisions")
    assert [r["outcome"] for r in rows].count("rejected") == 4


def test_email_requires_session_backed_approval(h):
    from coint.email_report import process_email_outbox
    h.to_final_review()
    assert h.decide("delivery_approve_close", cycle=1, sha=h.project()["current_delivery_sha"]) == "accepted"
    with h.db.tx() as c:  # tamper: approval no longer backed by a session decision
        c.execute("UPDATE approvals SET channel='github_comment' WHERE decision='approve-close'")
    assert list(process_email_outbox(h.engine).values()) == ["blocked"]
    assert h.gmail.sends == []


def test_verifier_blocks_when_unconfigured_and_checks_app_and_user(tmp_path, monkeypatch):
    from coint.errors import AuthError, PermissionDenied
    from coint.kitt_session import KittSessionVerifier, SessionUnavailable
    s = make_settings(str(tmp_path / "d"), kitt_oauth_client_id=None)
    with pytest.raises(SessionUnavailable):
        KittSessionVerifier(s).verify_founder("tok")
    s = make_settings(str(tmp_path / "d"))
    v = KittSessionVerifier(s)
    monkeypatch.setattr(v, "_check_token", lambda t: {"app": {"client_id": "kitt-app"},
                                                     "user": {"login": FOUNDER, "id": 9}})
    att = v.verify_founder("tok")
    assert att.github_login == FOUNDER and att.token_fingerprint != "tok"
    monkeypatch.setattr(v, "_check_token", lambda t: {"app": {"client_id": "other"}, "user": {"login": FOUNDER}})
    with pytest.raises(AuthError):
        v.verify_founder("tok")
    monkeypatch.setattr(v, "_check_token", lambda t: {"app": {"client_id": "kitt-app"}, "user": {"login": "kitt-bot"}})
    with pytest.raises(PermissionDenied):
        v.verify_founder("tok")


def test_pending_reviews_routed_to_kitt(h):
    h.to_final_review()
    items = h.engine.pending_reviews()
    assert len(items) == 1 and items[0]["stage"] == "FOUNDER_FINAL_REVIEW"
    assert items[0]["sha"] == h.project()["current_delivery_sha"]
    assert "delivery/final-report.md" in items[0]["documents"]
    assert any("for KITT to present to G" in b and "@kitt-bot" in b for _, b in h.gh.comments)
