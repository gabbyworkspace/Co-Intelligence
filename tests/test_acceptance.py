"""The 14 acceptance tests from the specification, plus related guards."""
import json

from coint import queue as Q
from coint.config import COUNCIL_ROLES
from coint.email_report import process_email_outbox
from coint.errors import InvalidInput
from coint.scheduler import recover_pending_tasks
from coint.webhook import VerifiedEvent, persist_delivery
from conftest import BRIEF, Harness
from fakes import FOUNDER, default_output


def approve_close(h, sha=None, actor=FOUNDER, cycle=1):
    p = h.project()
    return h.say(f"/delivery approve-close {cycle} {sha or p['current_delivery_sha']}", actor=actor)


# 1
def test_unconfirmed_founder_discussion_does_not_start(h):
    assert h.say("Let's discuss a widget project. Thoughts?") == "not_command"
    unconfirmed = dict(BRIEF, confirmed=False)
    assert h.say("/project start\n```json\n" + json.dumps(unconfirmed) + "\n```") == "rejected"
    assert h.say("/project start") == "rejected"  # no brief
    assert h.say("> /project start\n```json\n" + json.dumps(BRIEF) + "\n```") == "not_command"
    assert h.db.one("SELECT COUNT(*) n FROM projects")["n"] == 0
    assert h.db.one("SELECT COUNT(*) n FROM tasks")["n"] == 0


def test_only_founder_can_start(h):
    assert h.say("/project start\n```json\n" + json.dumps(BRIEF) + "\n```", actor="kitt-bot") == "rejected"
    assert h.db.one("SELECT COUNT(*) n FROM projects")["n"] == 0


# 2
def test_initial_gate_blocks_premature_handoff(make_h):
    h = make_h(manual=("KITT",))
    h.start()
    t = h.tasks(task_type="create_document")[0]
    # KITT (manual) publishes and hands off to FOUNDER
    sha = h.gh.commit_files("co-intel/CI-TEST", {"projects/CI-TEST/brief/brief.json": "{}",
                                                 "projects/CI-TEST/documents/project-document.md": "# d"}, "kitt")
    manifest = {"project_id": "CI-TEST", "task_id": t["id"], "revision": 1, "source_role": "KITT",
                "files": ["brief/brief.json", "documents/project-document.md"], "expected_outputs": [],
                "next_action": "G reviews"}
    # KITT tries to skip G and hand off to JARVIS -> rejected
    bad = f"/handoff JARVIS create_document 1 {sha}\n```json\n{json.dumps(manifest)}\n```"
    assert h.say(bad, actor="kitt-bot") == "rejected"
    ok = f"/handoff FOUNDER create_document 1 {sha}\n```json\n{json.dumps(manifest)}\n```"
    assert h.say(ok, actor="kitt-bot") == "ok"
    h.run_all()
    p = h.project()
    assert p["stage"] == "FOUNDER_INITIAL_REVIEW"
    assert h.tasks(task_type="apply_decisions") == []
    assert [x["state"] for x in h.tasks(role="FOUNDER")] == ["WAITING_FOUNDER"]
    # nobody but G can pass the gate
    assert h.say(f"/initial approve 1 {p['current_document_sha']}", actor="jarvis-bot") == "rejected"
    assert h.project()["stage"] == "FOUNDER_INITIAL_REVIEW"


# 3
def test_kitt_jarvis_required_sequence(h):
    h.to_final_review()
    seq = [(t["role"], t["task_type"]) for t in h.tasks() if t["state"] == "COMPLETED"]
    order = [x for x in seq if x[0] in ("KITT", "JARVIS", "FOUNDER", "GRONK")]
    assert order == [("KITT", "create_document"), ("FOUNDER", "founder_initial_review"),
                     ("KITT", "apply_decisions"), ("JARVIS", "doc_review"), ("KITT", "finalize_documents"),
                     ("JARVIS", "freeze_council_package"), ("GRONK", "council_dispatch"),
                     ("GRONK", "council_draft"), ("JARVIS", "develop_and_deliver")]
    assert h.project()["stage"] == "FOUNDER_FINAL_REVIEW"


# 4
def test_four_reviewers_receive_same_package(h):
    h.to_final_review()
    p = h.project()
    reviews = h.tasks(task_type="council_review")
    assert sorted(t["role"] for t in reviews) == sorted(COUNCIL_ROLES)
    assert {t["input_sha"] for t in reviews} == {p["current_package_sha"]}
    for r in COUNCIL_ROLES:
        calls = h.adapters[r].calls
        assert len(calls) == 1 and calls[0][1] == p["current_package_sha"]
    # each review published separately and records the package SHA
    for t in reviews:
        body = h.gh.get_file(f"projects/CI-TEST/council/reviews/{t['role']}.md", t["published_sha"])
        assert p["current_package_sha"] in body


# 5
def test_missing_or_stale_reviews_block_council_completion(make_h):
    def stale(role, tt, meta, inputs):
        out = default_output(role, tt, meta, inputs)
        out["files"] = {f"council/reviews/{role}.md": "Package 0000000000000000000000000000000000000000"}
        return out
    h = make_h(scripts={"COUNCIL_3": stale})
    h.to_final_review()
    p = h.project()
    assert p["stage"] == "COUNCIL_REVIEW"
    assert h.tasks(task_type="council_draft") == []
    c3 = h.tasks(role="COUNCIL_3")[0]
    assert c3["state"] == "BLOCKED" and "package SHA" in c3["error"]
    # a result produced for an obsolete input version is rejected too
    t = dict(h.tasks(role="COUNCIL_1")[0])
    out = default_output("COUNCIL_1", "council_review", {"input_sha": "f" * 40}, {})
    try:
        h.engine.validate_output(t, out, p)
        raise AssertionError("expected rejection")
    except InvalidInput:
        pass
    with h.db.tx() as c:
        assert h.engine.collect_council_reviews(c, p, p["current_package_sha"]) is False


def test_missing_review_flagged_by_overdue_monitor(make_h):
    from coint.scheduler import monitor_overdue_tasks
    h = make_h(manual=("COUNCIL_2",), council_timeout_minutes=-1)
    h.to_final_review()
    assert h.project()["stage"] == "COUNCIL_REVIEW"
    flagged = monitor_overdue_tasks(h.engine)
    assert flagged == [h.tasks(role="COUNCIL_2")[0]["id"]]
    assert any("missing council review" in b for _, b in h.gh.comments)
    assert monitor_overdue_tasks(h.engine) == []  # flagged once


# 6
def test_council_draft_and_all_reviews_reach_jarvis(h):
    h.to_final_review()
    dev = h.tasks(task_type="develop_and_deliver")[0]
    paths = {f["path"] for f in json.loads(dev["manifest"])["files"]}
    for r in COUNCIL_ROLES:
        assert f"council/reviews/{r}.md" in paths
    for f in ("proposed-final-draft.md", "findings-index.json", "conflict-decision-log.md", "unresolved-blockers.md"):
        assert f"council/drafts/{f}" in paths
    seen = [c for c in h.adapters["JARVIS"].calls if c[0] == "develop_and_deliver"][0][2]
    assert {f"council/reviews/{r}.md" for r in COUNCIL_ROLES} <= set(seen)
    assert "council/drafts/proposed-final-draft.md" in seen


# 7
def test_duplicate_events_produce_one_logical_task(h):
    ev = VerifiedEvent("abc-123-def", "issue_comment", "created", {"x": 1})
    assert persist_delivery(h.db, ev) is True
    assert persist_delivery(h.db, ev) is False
    body = "/project start\n```json\n" + json.dumps(BRIEF) + "\n```"
    assert h.say(body, comment_id=55) == "ok"
    assert h.say(body, comment_id=55) == "duplicate"           # same comment via webhook + recovery
    p = h.project()
    for _ in range(2):
        Q.enqueue_task(h.db, project_id=p["id"], cycle=1, stage="KITT_DRAFT", role="KITT",
                       task_type="create_document", input_sha=p["head_sha"], assignment_rev=1, manifest={})
    assert len(h.tasks(task_type="create_document")) == 1
    # concurrent pickup: only one claim succeeds
    tid = h.tasks(task_type="create_document")[0]["id"]
    assert Q.claim_task(h.db, tid, "w1", 300) is True
    assert Q.claim_task(h.db, tid, "w2", 300) is False


# 8
def test_scheduled_recovery_catches_missed_handoff(make_h):
    h = make_h(manual=("KITT",))
    h.start()
    t = h.tasks(task_type="create_document")[0]
    sha = h.gh.commit_files("co-intel/CI-TEST", {"projects/CI-TEST/brief/brief.json": "{}",
                                                 "projects/CI-TEST/documents/project-document.md": "# d"}, "kitt")
    manifest = {"project_id": "CI-TEST", "task_id": t["id"], "revision": 1, "source_role": "KITT",
                "files": ["brief/brief.json", "documents/project-document.md"], "expected_outputs": [],
                "next_action": "G reviews"}
    body = f"/handoff FOUNDER create_document 1 {sha}\n```json\n{json.dumps(manifest)}\n```"
    # webhook never arrived; the comment only exists on GitHub
    h.gh.repo_comments.append({"id": 9001, "issue_url": "https://api.github.com/repos/o/r/issues/7",
                               "body": body, "user": {"login": "kitt-bot", "type": "User"},
                               "created_at": "t", "updated_at": "t", "html_url": "u"})
    assert h.project()["stage"] == "KITT_DRAFT"
    res = recover_pending_tasks(h.engine)
    assert res["comments"] == 1
    assert h.project()["stage"] == "FOUNDER_INITIAL_REVIEW"
    assert h.project()["current_document_sha"] == sha
    assert recover_pending_tasks(h.engine)["comments"] == 0  # not processed twice


# 9
def test_unauthorized_or_stale_founder_approval_rejected(h):
    h.to_final_review()
    p = h.project()
    assert approve_close(h, actor="jarvis-bot") == "rejected"
    assert approve_close(h, sha="a" * 40) == "rejected"
    assert approve_close(h, cycle=2) == "rejected"
    assert h.say(f"/delivery approve-close 1 {p['current_delivery_sha'][:12]}") == "rejected"  # short SHA
    assert h.project()["status"] == "ACTIVE"
    assert h.db.one("SELECT COUNT(*) n FROM closures")["n"] == 0
    assert h.db.one("SELECT COUNT(*) n FROM email_outbox")["n"] == 0


def test_stale_approval_after_new_cycle_rejected(h):
    h.to_final_review()
    old = h.project()["current_delivery_sha"]
    h.say(f"/delivery changes 1 {old}\n```json\n" + json.dumps({"changes": ["x"], "route": "development"}) + "\n```")
    h.run_all()
    assert h.project()["current_cycle"] == 2
    assert approve_close(h, sha=old, cycle=1) == "rejected"
    assert approve_close(h, sha=old, cycle=2) == "rejected"


# 10
def test_requested_changes_create_new_cycle_without_email(h):
    h.to_final_review()
    p = h.project()
    h.say(f"/delivery changes 1 {p['current_delivery_sha']}\n```json\n"
          + json.dumps({"changes": ["rename button"], "route": "documents"}) + "\n```")
    p2 = h.project()
    assert p2["current_cycle"] == 2 and p2["stage"] == "KITT_APPLY_DECISIONS"
    assert all(t["state"] in ("COMPLETED", "SUPERSEDED") for t in h.tasks(cycle=1))
    h.run_all()
    assert h.project()["stage"] == "FOUNDER_FINAL_REVIEW"
    assert h.project()["current_delivery_sha"] != p["current_delivery_sha"]
    assert h.db.one("SELECT COUNT(*) n FROM email_outbox")["n"] == 0
    assert process_email_outbox(h.engine) == {}
    assert h.gmail.sends == []
    assert not any("Project Closed" in b for _, b in h.gh.comments)


# 11
def test_ordinary_issue_closure_sends_no_report(h):
    h.to_final_review()
    assert h.engine.handle_issue_closed(h.issue, FOUNDER) == "ignored_plain_close"
    h.engine.dispatch_outbox()
    assert h.project()["status"] == "ACTIVE"
    assert process_email_outbox(h.engine) == {}
    assert h.gmail.sends == []


# 12
def test_valid_development_approval_and_closure_enable_email(h):
    h.to_final_review()
    p = h.project()
    assert approve_close(h) == "ok"
    assert h.gh.closed == [h.issue]
    assert h.project()["status"] == "CLOSED"
    res = process_email_outbox(h.engine)
    assert list(res.values()) == ["sent"]
    assert len(h.gmail.sends) == 1
    m = h.gmail.sends[0]
    assert m["To"] == "g@resystem.org" and m["From"] == "jarvis.resystem@gmail.com"
    assert m["Cc"] is None and m["Bcc"] is None
    assert m["Subject"] == "[Project Closed] CI-TEST — Widget — Version 1"
    text = m.get_content()
    assert p["current_delivery_sha"] in text and "F-001: accepted" in text and "AC1: passed" in text
    row = h.db.one("SELECT * FROM email_outbox")
    assert row["state"] == "SENT" and row["gmail_message_id"] and row["accepted_at"]
    assert process_email_outbox(h.engine) == {}  # never twice


def test_email_waits_for_issue_close_and_blocks_on_failed_verification(make_h):
    def failing(role, tt, meta, inputs):
        out = default_output(role, tt, meta, inputs)
        if tt == "develop_and_deliver":
            out["files"]["verification/verification-report.json"] = json.dumps(
                {"development_complete": True, "status": "failed", "checks": [{"name": "AC1", "result": "failed"}]})
        return out
    h = make_h(scripts={"JARVIS": failing})
    h.to_final_review()
    assert approve_close(h) == "rejected"           # verification must pass first
    assert h.db.one("SELECT COUNT(*) n FROM email_outbox")["n"] == 0


# 13
def test_uncertain_email_outcome_is_reconciled_not_resent(make_h):
    h = make_h(gmail_mode="uncertain_but_sent")
    h.to_final_review()
    approve_close(h)
    assert list(process_email_outbox(h.engine).values()) == ["uncertain"]
    assert h.db.one("SELECT state FROM email_outbox")["state"] == "SEND_UNCERTAIN"
    assert list(process_email_outbox(h.engine).values()) == ["reconciled_sent"]
    assert len(h.gmail.sends) == 1
    assert h.db.one("SELECT state FROM email_outbox")["state"] == "SENT"


def test_uncertain_not_found_waits_before_any_resend(make_h):
    h = make_h(gmail_mode="uncertain_not_sent")
    h.to_final_review()
    approve_close(h)
    process_email_outbox(h.engine)
    for _ in range(3):
        assert list(process_email_outbox(h.engine).values()) == ["waiting"]
    assert len(h.gmail.sends) == 1


def test_definite_presend_failure_retries(make_h):
    h = make_h(gmail_mode="presend_fail")
    h.to_final_review()
    approve_close(h)
    assert list(process_email_outbox(h.engine).values()) == ["retry"]
    assert h.db.one("SELECT state FROM email_outbox")["state"] == "PENDING"


# 14
def test_restart_recovery_preserves_state(tmp_path):
    h = Harness(tmp_path, gmail_mode="uncertain_but_sent")
    h.to_final_review()
    approve_close(h)
    process_email_outbox(h.engine)
    before = {t: h.db.one(f"SELECT COUNT(*) n FROM {t}")["n"]
              for t in ("tasks", "approvals", "closures", "email_outbox", "audit_events", "handoffs")}
    h.restart()
    after = {t: h.db.one(f"SELECT COUNT(*) n FROM {t}")["n"] for t in before}
    assert after == before
    assert h.db.one("SELECT state FROM email_outbox")["state"] == "SEND_UNCERTAIN"
    assert h.project()["status"] == "CLOSED"
    process_email_outbox(h.engine)
    assert h.db.one("SELECT state FROM email_outbox")["state"] == "SENT"
    assert len(h.gmail.sends) == 1


def test_expired_lease_recovered_after_restart(tmp_path):
    h = Harness(tmp_path, lease_grace_seconds=0)
    h.start()
    tid = h.tasks(task_type="create_document")[0]["id"]
    assert Q.claim_task(h.db, tid, "crashed-worker", lease_seconds=-5)
    h.restart()
    assert recover_pending_tasks(h.engine)["leases"] == 1
    assert h.tasks(task_type="create_document")[0]["state"] == "COMPLETED"
    assert h.project()["stage"] == "FOUNDER_INITIAL_REVIEW"


def test_unexpired_lease_not_stolen(tmp_path):
    h = Harness(tmp_path)
    h.start()
    tid = h.tasks(task_type="create_document")[0]["id"]
    assert Q.claim_task(h.db, tid, "live-worker", lease_seconds=300)
    assert recover_pending_tasks(h.engine)["leases"] == 0
    assert h.tasks(task_type="create_document")[0]["lease_owner"] == "live-worker"
