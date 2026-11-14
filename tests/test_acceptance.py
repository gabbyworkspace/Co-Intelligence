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


def approve_close(h, sha=None, actor=FOUNDER, cycle=1, client_id=None, channel=None):
    """G chooses APPROVE AND CLOSE in the JARVIS session; KITT then records it on GitHub."""
    p = h.project()
    out = h.decide("delivery_approve_close", login=actor, client_id=client_id, channel=channel, cycle=cycle,
                   sha=sha or p["current_delivery_sha"])
    h.run_all()
    return out


# 1
def test_unconfirmed_founder_discussion_does_not_start(h):
    assert h.say("Let's discuss a widget project. Thoughts?") == "not_command"
    unconfirmed = dict(BRIEF, confirmed=False)
    assert h.decide("project_start", brief=unconfirmed, issue_number=7) == "rejected"
    assert h.decide("project_start", issue_number=7) == "rejected"  # no brief
    assert h.decide("project_start", brief=BRIEF, statement="", issue_number=7) == "rejected"
    # a GitHub comment can never start a project, even with a complete confirmed brief
    assert h.say("/project start\n```json\n" + json.dumps(BRIEF) + "\n```") == "rejected"
    assert h.say("> /project start\n```json\n" + json.dumps(BRIEF) + "\n```") == "not_command"
    assert h.db.one("SELECT COUNT(*) n FROM projects")["n"] == 0
    assert h.db.one("SELECT COUNT(*) n FROM tasks")["n"] == 0


def test_only_founder_can_start(h):
    assert h.decide("project_start", login="kitt-bot", brief=BRIEF, issue_number=7) == "rejected"
    assert h.db.one("SELECT COUNT(*) n FROM projects")["n"] == 0


def test_confirmed_brief_submitted_from_kitt_session_to_github(h):
    assert h.decide("project_start", brief=dict(BRIEF), statement="Confirmed, start it.") == "accepted"
    p = h.project()
    assert p["issue_number"] == 101 and h.gh.issues[0][0] == "[Project] Widget"   # tracking issue created
    brief = json.loads(h.gh.get_file("CI-TEST/brief/confirmed-brief.json", p["head_sha"]))
    assert brief["confirmed"] is True and brief["_coint"]["channel"] == "kitt_session"
    ap = h.db.one("SELECT * FROM approvals WHERE kind='brief'")
    assert ap["channel"] == "kitt_session" and ap["attestation_id"].startswith("dec-")
    assert any("Founder decision recorded" in b and "Confirmed, start it." in b for _, b in h.gh.comments)


# 2
def test_initial_gate_blocks_premature_handoff(make_h):
    h = make_h(manual=("KITT",))
    h.start()
    t = h.tasks(task_type="create_document")[0]
    # KITT (manual) publishes and hands off to FOUNDER
    sha = h.gh.commit_files("co-intel/CI-TEST", {"CI-TEST/brief/brief.json": "{}",
                                                 "CI-TEST/documents/project-document.md": "# d"}, "kitt")
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
                     ("GRONK", "council_draft"), ("JARVIS", "develop_and_deliver"),
                     ("KITT", "delivery_review"), ("JARVIS", "finalize_delivery")]
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
        body = h.gh.get_file(f"council/CI-TEST/reviews/{t['role']}.md", t["published_sha"])
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
    assert h.decide("project_start", brief=BRIEF, issue_number=7, decision_id="dup-decision-1") == "accepted"
    assert h.decide("project_start", brief=BRIEF, issue_number=7, decision_id="dup-decision-1") == "accepted"
    assert h.db.one("SELECT COUNT(*) n FROM projects")["n"] == 1
    assert h.say("/project status", actor=FOUNDER, comment_id=55) == "ok"
    assert h.say("/project status", actor=FOUNDER, comment_id=55) == "duplicate"  # webhook + recovery
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
    sha = h.gh.commit_files("co-intel/CI-TEST", {"CI-TEST/brief/brief.json": "{}",
                                                 "CI-TEST/documents/project-document.md": "# d"}, "kitt")
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
    assert approve_close(h, sha=p["current_delivery_sha"][:12]) == "rejected"  # short SHA
    assert approve_close(h, client_id="some-other-app") == "rejected"  # not the JARVIS session app
    assert approve_close(h, channel="kitt_session") == "rejected"      # final approval is G <-> JARVIS only
    # GitHub comments are never approval evidence: not from KITT, not even from G's own account
    cmd = f"/delivery approve-close 1 {p['current_delivery_sha']}"
    assert h.say(cmd, actor="kitt-bot") == "rejected"
    assert h.say(cmd, actor=FOUNDER) == "rejected"
    assert h.project()["status"] == "ACTIVE"
    assert h.db.one("SELECT COUNT(*) n FROM closures")["n"] == 0
    assert h.final_count() == 0


def test_stale_approval_after_new_cycle_rejected(h):
    h.to_final_review()
    old = h.project()["current_delivery_sha"]
    h.decide("delivery_changes", cycle=1, sha=old, changes=["x"], route="development")
    h.run_all()
    assert h.project()["current_cycle"] == 2
    assert approve_close(h, sha=old, cycle=1) == "rejected"
    assert approve_close(h, sha=old, cycle=2) == "rejected"


# 10
def test_requested_changes_create_new_cycle_without_email(h):
    h.to_final_review()
    p = h.project()
    assert h.decide("delivery_changes", cycle=1, sha=p["current_delivery_sha"], changes=["rename button"],
                    route="documents") == "accepted"
    # validated in the JARVIS session, but no effect until KITT records it on GitHub
    assert h.project()["stage"] == "FOUNDER_DECISION_REFERENCE" and h.project()["current_cycle"] == 1
    ref = h.tasks(task_type="publish_decision_reference")[0]
    assert ref["role"] == "JARVIS" and h.engine.run_task(ref["id"]) == "completed"
    reference = json.loads(h.gh.get_file("decisions/CI-TEST/v1.json",
                                         h.tasks(task_type="publish_decision_reference")[0]["published_sha"]))
    assert reference["decision"] == "REQUEST_CHANGES" and reference["delivery_sha"] == p["current_delivery_sha"]
    assert reference["delivery_tag"] == "CI-TEST-v1" and reference["requested_changes"] == ["rename button"]
    assert h.project()["stage"] == "FOUNDER_DECISION_RECORDING" and h.project()["current_cycle"] == 1
    rec = h.tasks(task_type="record_founder_decision")[0]
    assert rec["role"] == "KITT"
    h.engine.run_task(rec["id"])
    p2 = h.project()
    assert p2["current_cycle"] == 2 and p2["stage"] == "KITT_APPLY_DECISIONS"
    assert all(t["state"] in ("COMPLETED", "SUPERSEDED") for t in h.tasks(cycle=1))
    h.run_all()
    assert h.project()["stage"] == "FOUNDER_FINAL_REVIEW"
    assert h.project()["current_delivery_sha"] != p["current_delivery_sha"]
    assert h.final_count() == 0
    process_email_outbox(h.engine)  # only the Version 2 review package goes out
    assert [m["Subject"].split("]")[0] for m in h.gmail.sends] == ["[Review Required"]
    assert "Version 2" in h.gmail.sends[0]["Subject"] and h.gmail.sends[0]["To"] == "baileys.resystem@gmail.com"
    assert not any("Project Closed" in b for _, b in h.gh.comments)
    assert h.db.one("SELECT COUNT(*) n FROM closures")["n"] == 0


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
    assert approve_close(h) == "accepted"
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
    row = h.final_row()
    assert row["state"] == "SENT" and row["gmail_message_id"] and row["accepted_at"]
    assert "Recorded on GitHub by KITT" in text
    assert process_email_outbox(h.engine) == {}  # never twice


def test_email_waits_for_issue_close_and_blocks_on_failed_verification(make_h):
    def failing(role, tt, meta, inputs):
        out = default_output(role, tt, meta, inputs)
        if tt in ("develop_and_deliver", "finalize_delivery"):
            out["files"]["verification/verification-report.json"] = json.dumps(
                {"development_complete": True, "status": "failed", "checks": [{"name": "AC1", "result": "failed"}]})
        return out
    h = make_h(scripts={"JARVIS": failing})
    h.to_final_review()
    assert approve_close(h) == "rejected"           # verification must pass first
    assert h.final_count() == 0


# 13
def test_uncertain_email_outcome_is_reconciled_not_resent(make_h):
    h = make_h(gmail_mode="uncertain_but_sent")
    h.to_final_review()
    approve_close(h)
    assert list(process_email_outbox(h.engine).values()) == ["uncertain"]
    assert h.final_row()["state"] == "SEND_UNCERTAIN"
    assert list(process_email_outbox(h.engine).values()) == ["reconciled_sent"]
    assert len(h.gmail.sends) == 1
    assert h.final_row()["state"] == "SENT"


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
    assert h.final_row()["state"] == "PENDING"


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
    assert h.final_row()["state"] == "SEND_UNCERTAIN"
    assert h.project()["status"] == "CLOSED"
    process_email_outbox(h.engine)
    assert h.final_row()["state"] == "SENT"
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


# ---------------------------------------------------------------- step 10-12 flow
def test_step10_kitt_reviews_delivery_and_jarvis_addresses_findings(h):
    h.to_final_review()
    kr = h.tasks(task_type="delivery_review")[0]
    fin = h.tasks(task_type="finalize_delivery")[0]
    dev = h.tasks(task_type="develop_and_deliver")[0]
    assert kr["role"] == "KITT" and kr["input_sha"] == dev["published_sha"]
    assert fin["role"] == "JARVIS" and fin["input_sha"] == kr["published_sha"]
    # the version G sees is JARVIS's finalized one, not the pre-review delivery
    assert h.project()["current_delivery_sha"] == fin["published_sha"] != dev["published_sha"]
    # KITT never received a founder gate for the final delivery
    assert [t["task_type"] for t in h.tasks(role="FOUNDER")] == ["founder_initial_review", "founder_final_review"]
    assert any("for JARVIS to present to G" in b for _, b in h.gh.comments)


def test_finalize_must_answer_every_kitt_finding(make_h):
    def ignores(role, tt, meta, inputs):
        out = default_output(role, tt, meta, inputs, {})
        if tt == "finalize_delivery":
            out["files"]["reviews/jarvis/kitt-findings-response.json"] = json.dumps({"responses": []})
        return out
    h = make_h(scripts={"JARVIS": ignores})
    h.to_final_review(send_review=False)
    t = h.tasks(task_type="finalize_delivery")[0]
    assert t["state"] == "BLOCKED" and "K-1" in t["error"]
    assert h.project()["stage"] == "JARVIS_FINALIZE_DELIVERY"


def test_step11_review_package_emailed_to_baileys(h):
    h.to_final_review()
    assert len(h.review_sends) == 1
    m = h.review_sends[0]
    p = h.project()
    assert m["To"] == "baileys.resystem@gmail.com" and m["From"] == "jarvis.resystem@gmail.com" and m["Cc"] is None
    assert m["Subject"].startswith("[Review Required] CI-TEST — Widget — Version 1")
    body = m.get_content()
    assert p["current_delivery_sha"] in body and "AC1: passed" in body and "demo only" in body
    assert "no reply is required" in body and "Project Closed" not in m["Subject"]
    assert f"CI-TEST v1 {p['current_delivery_sha']}" in body
    item = h.engine.pending_reviews(channel="jarvis_session")[0]
    assert item["review_package_email"]["state"] == "SENT"
    assert item["review_package_email"]["chat_confirmation"] == \
        "The review package has been emailed to baileys.resystem@gmail.com."
    assert h.engine.pending_reviews(channel="kitt_session") == []   # final review is not KITT's to present


def test_step11_review_package_failure_reported_not_confirmed(make_h):
    from coint.errors import AuthError
    h = make_h()
    h.to_final_review(send_review=False)

    def denied(raw):
        raise AuthError("Gmail 401 on send")
    h.gmail.send_raw = denied
    assert list(process_email_outbox(h.engine).values()) == ["blocked"]
    em = h.engine.pending_reviews(channel="jarvis_session")[0]["review_package_email"]
    assert em["state"] == "BLOCKED" and "401" in em["error"] and em["chat_confirmation"] is None
    assert any("Review package email" in b and "not sent" in b for _, b in h.gh.comments)


def test_kitt_record_required_before_closure_and_must_cite_decision(make_h):
    def lazy_record(role, tt, meta, inputs):
        if tt == "record_founder_decision":
            return {"verdict": "recorded", "input_sha": meta["input_sha"], "summary": "G approved, trust me",
                    "files": {"approvals/note.md": "approved"}, "next_action": "close"}
        return default_output(role, tt, meta, inputs, {})
    h = make_h(scripts={"KITT": lazy_record})
    h.adapters["KITT"].script = None
    h.to_final_review()
    h.adapters["KITT"].script = lazy_record
    assert h.decide("delivery_approve_close", cycle=1, sha=h.project()["current_delivery_sha"]) == "accepted"
    assert h.project()["status"] == "ACTIVE" and h.project()["stage"] == "FOUNDER_DECISION_REFERENCE"
    h.run_all()
    rec = h.tasks(task_type="record_founder_decision")[0]
    assert rec["state"] == "BLOCKED"            # an agent statement without the validated reference is refused
    assert h.project()["status"] == "ACTIVE" and h.final_count() == 0 and h.gh.closed == []


def test_jarvis_session_cannot_make_initial_decisions(h):
    h.start()
    h.run_all()
    sha = h.project()["current_document_sha"]
    assert h.decide("initial_approve", channel="jarvis_session", cycle=1, sha=sha) == "rejected"
    assert h.decide("project_start", channel="jarvis_session", brief=BRIEF) == "rejected"
    assert h.project()["stage"] == "FOUNDER_INITIAL_REVIEW"


def test_approval_gate_pauses_when_jarvis_session_unavailable(make_h):
    h = make_h(jarvis_oauth_client_id=None, jarvis_oauth_client_secret=None)
    h.to_final_review()
    assert approve_close(h) == "rejected"
    assert h.project()["stage"] == "FOUNDER_FINAL_REVIEW" and h.project()["status"] == "ACTIVE"
    assert h.tasks(task_type="record_founder_decision") == [] and h.final_count() == 0



# ---------------------------------------------------------------- WORKFLOW.md v2.0 layout
def test_workflow_v2_layout_tags_closure_and_ledger(h):
    h.to_final_review()
    p = h.project()
    sha, gh = p["current_delivery_sha"], h.gh
    for name in ("DELIVERY.md", "FINAL-REPORT.md", "VERIFICATION.json", "VERIFICATION.md", "KITT_REVIEW.md",
                 "FINDINGS.json", "FINDINGS.md", "IMPLEMENTATION.md", "development/app.py"):
        assert gh.get_file(f"deliveries/CI-TEST/v1/{name}", sha) is not None, name
    assert gh.get_file("council/CI-TEST/MANIFEST.json", sha) is not None
    assert gh.get_file("council/CI-TEST/reviews/COUNCIL_1.md", sha) is not None
    assert gh.get_file("CI-TEST/documents/project-document.md", sha) is not None
    assert gh.tags["CI-TEST-v1"] == sha
    assert "review_package" in gh.get_file("ledger/emails.jsonl", gh.branch_head("co-intel/CI-TEST"))
    assert approve_close(h) == "accepted"
    head = gh.branch_head("co-intel/CI-TEST")
    assert gh.get_file("decisions/CI-TEST/v1.json", head) and gh.get_file("decisions/CI-TEST/v1.KITT_RECORD.md", head)
    closure = json.loads(gh.get_file("closure/CI-TEST/CLOSURE.json", head))
    assert closure["delivery_sha"] == sha and closure["delivery_tag"] == "CI-TEST-v1"
    assert "CI-TEST-v1-closed" in gh.tags
    process_email_outbox(h.engine)
    head = gh.branch_head("co-intel/CI-TEST")
    closure = json.loads(gh.get_file("closure/CI-TEST/CLOSURE.json", head))
    assert closure["final_report_email"]["state"] == "SENT" and closure["final_report_email"]["gmail_message_id"]
    ledger = [json.loads(x) for x in gh.get_file("ledger/emails.jsonl", head).splitlines()]
    assert [e["kind"] for e in ledger] == ["review_package", "final_report"]
    assert ledger[1]["to"] == "g@resystem.org" and ledger[0]["to"] == "baileys.resystem@gmail.com"


def test_adopt_published_brief_like_flow_test_001(h):
    sha = h.gh.commit_files("main", {"FLOW-TEST-001/INITIAL-BRIEF-v1.0.md": "# FLOW-TEST-001 brief"}, "kitt")
    assert h.decide("project_start", project_id="FLOW-TEST-001", title="Co-Intelligence Workflow Test",
                    brief_ref={"path": "FLOW-TEST-001/INITIAL-BRIEF-v1.0.md", "sha": sha}, issue_number=2,
                    statement="I explicitly CONFIRM the initial brief v1.0") == "rejected"   # confirmed flag missing
    assert h.decide("project_start", project_id="FLOW-TEST-001", title="Co-Intelligence Workflow Test",
                    brief_ref={"path": "FLOW-TEST-001/INITIAL-BRIEF-v1.0.md", "sha": "b" * 40}, issue_number=2,
                    confirmed=True) == "rejected"                                                 # wrong version
    assert h.decide("project_start", project_id="FLOW-TEST-001", title="Co-Intelligence Workflow Test",
                    brief_ref={"path": "FLOW-TEST-001/INITIAL-BRIEF-v1.0.md", "sha": sha}, issue_number=2,
                    confirmed=True) == "accepted"
    t = h.tasks(task_type="create_document")[0]
    assert t["input_sha"] == sha
    assert json.loads(t["manifest"])["files"][0]["repo_path"] == "FLOW-TEST-001/INITIAL-BRIEF-v1.0.md"
    h.run_all()
    assert "brief/INITIAL-BRIEF-v1.0.md" in h.adapters["KITT"].calls[0][2]
    assert h.engine.project("FLOW-TEST-001")["stage"] == "FOUNDER_INITIAL_REVIEW"
