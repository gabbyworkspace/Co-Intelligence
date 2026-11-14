"""Workflow engine: event intake, commands, task execution, routing, council,
founder gates, closure."""
from __future__ import annotations

import json
import logging
import os
import socket
import threading

from . import queue as Q
from .adapters import AgentRequest, build_adapter
from .audit import record_audit_event
from .authz import authorize_action, is_founder
from .commands import ParseError, parse_command
from .config import COUNCIL_ROLES, FINAL_REPORT_TO, GITHUB_URL, REVIEW_PACKAGE_TO, Settings
from .db import DB, dumps, iso
from .errors import (CommandRejected, InvalidInput, PermanentError, StaleAssignment,
                     TransientError)
from . import layout as L
from .github import GitHubClient
from .models import (EXPECTED_OUTPUTS, PROJECT_DIRS, ROUTES, STAGE_TASK,
                     VERDICTS, ProjectStatus, Stage, TaskState)

log = logging.getLogger("coint.workflow")
PROMPT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "prompts")
ROLE_PROMPT = {"KITT": "kitt.md", "JARVIS": "jarvis.md", "GRONK": "gronk.md"}
ALLOWED_PREFIXES = tuple(d + "/" for d in PROJECT_DIRS)


def _read_prompt(name: str) -> str:
    with open(os.path.join(PROMPT_DIR, name), encoding="utf-8") as fh:
        return fh.read()


class Engine:
    def __init__(self, settings: Settings, db: DB, gh: GitHubClient, *, adapters=None, gmail=None):
        self.s = settings
        self.db = db
        self.gh = gh
        self.adapters = adapters or {r: build_adapter(c) for r, c in settings.adapters.items()}
        self.gmail = gmail
        from .kitt_session import SessionVerifier
        self.kitt_verifier = SessionVerifier(settings, "kitt_session")
        self.jarvis_verifier = SessionVerifier(settings, "jarvis_session")
        self.worker_id = f"{socket.gethostname()}:{os.getpid()}"

    # ------------------------------------------------------------------ helpers
    def project(self, pid: str):
        return self.db.one("SELECT * FROM projects WHERE id=?", pid)

    def project_by_issue(self, issue: int):
        return self.db.one("SELECT * FROM projects WHERE issue_number=?", issue)

    def _outbox(self, c, project_id: str, kind: str, payload: dict, dedupe_key: str | None = None):
        c.execute("INSERT OR IGNORE INTO outbox(project_id, kind, payload, dedupe_key, created_at)"
                  " VALUES (?,?,?,?,?)", (project_id, kind, dumps(payload), dedupe_key, iso()))

    def comment(self, c, project, body: str, dedupe_key: str | None = None):
        self._outbox(c, project["id"], "comment", {"issue": project["issue_number"], "body": body}, dedupe_key)

    def dispatch_outbox(self, limit: int = 50) -> int:
        """Deliver pending GitHub side effects (comments, issue close). At-least-once;
        comments carry dedupe keys in the DB so a crash re-sends at most one comment."""
        n, failed_projects = 0, set()
        for row in self.db.all("SELECT * FROM outbox WHERE dispatched_at IS NULL ORDER BY id LIMIT ?", limit):
            if row["project_id"] in failed_projects:
                continue  # keep per-project order (e.g. CLOSURE.json before the issue is closed)
            p = json.loads(row["payload"])
            try:
                if row["kind"] == "comment":
                    self.gh.create_comment(p["issue"], p["body"])
                elif row["kind"] == "close_issue":
                    self.gh.close_issue(p["issue"])
                    with self.db.tx() as c:
                        c.execute("UPDATE closures SET issue_closed_at=? WHERE project_id=? AND cycle=?"
                                  " AND issue_closed_at IS NULL", (iso(), row["project_id"], p["cycle"]))
                elif row["kind"] == "label":
                    self.gh.add_labels(p["issue"], p["labels"])
                elif row["kind"] == "commit":
                    self.gh.commit_files(p["branch"], p["files"], p["message"])
                elif row["kind"] == "tag":
                    self.gh.create_tag(p["name"], p["sha"])
                elif row["kind"] == "ledger":
                    head = self.gh.branch_head(p["branch"]) or self.gh.default_branch_head()
                    current = self.gh.get_file(L.LEDGER_PATH, head) or ""
                    if p["entry"]["key"] not in current:  # idempotent append
                        line = json.dumps(p["entry"], sort_keys=True)
                        self.gh.commit_files(p["branch"], {L.LEDGER_PATH: current + line + "\n"},
                                             f"[coint] ledger: {p['entry']['kind']} {p['entry']['key']}")
                with self.db.tx() as c:
                    c.execute("UPDATE outbox SET dispatched_at=?, attempts=attempts+1 WHERE id=?", (iso(), row["id"]))
                n += 1
            except Exception as e:  # noqa: BLE001 - retried by recovery
                failed_projects.add(row["project_id"])
                with self.db.tx() as c:
                    c.execute("UPDATE outbox SET attempts=attempts+1, last_error=? WHERE id=?", (str(e)[:500], row["id"]))
        return n

    # ------------------------------------------------------------- event intake
    def process_delivery(self, delivery_id: str) -> str:
        row = self.db.one("SELECT * FROM webhook_deliveries WHERE delivery_id=?", delivery_id)
        if not row or row["status"] != "RECEIVED":
            return "skip"
        payload = json.loads(row["payload"])
        ev, action = row["event"], row["action"]
        try:
            if ev == "issue_comment" and action == "created":
                cm = payload["comment"]
                outcome = self.handle_comment(
                    issue=payload["issue"]["number"], comment_id=cm["id"], body=cm.get("body") or "",
                    actor=payload["sender"]["login"], actor_type=payload["sender"].get("type", "User"),
                    created_at=cm.get("created_at"), updated_at=cm.get("updated_at"), url=cm.get("html_url"))
            elif ev == "issue_comment":
                record_audit_event(self.db, actor=payload["sender"]["login"], action=f"comment.{action}",
                                   outcome="ignored_not_executed",
                                   detail={"comment_id": payload["comment"]["id"]})
                outcome = "ignored_edit"
            elif ev == "issues" and action == "closed":
                outcome = self.handle_issue_closed(payload["issue"]["number"], payload["sender"]["login"])
            elif ev in ("check_run", "check_suite") and action == "completed":
                obj = payload[ev]
                with self.db.tx() as c:
                    c.execute("INSERT OR REPLACE INTO check_results VALUES (?,?,?,?,?)",
                              (obj["head_sha"], obj.get("name") or f"suite:{obj['id']}", obj.get("status"),
                               obj.get("conclusion"), iso()))
                outcome = "check_recorded"
            else:
                outcome = "ignored"
            with self.db.tx() as c:
                c.execute("UPDATE webhook_deliveries SET status='PROCESSED', processed_at=?, error=NULL"
                          " WHERE delivery_id=?", (iso(), delivery_id))
            return outcome
        except Exception as e:  # noqa: BLE001 - stays RECEIVED, recovery retries
            log.exception("delivery %s failed", delivery_id)
            with self.db.tx() as c:
                c.execute("UPDATE webhook_deliveries SET error=? WHERE delivery_id=?", (str(e)[:1000], delivery_id))
            return "error"

    def handle_comment(self, *, issue: int, comment_id: int, body: str, actor: str, actor_type: str = "User",
                       created_at: str | None = None, updated_at: str | None = None, url: str | None = None) -> str:
        if self.db.one("SELECT 1 FROM processed_comments WHERE comment_id=?", comment_id):
            return "duplicate"
        project = self.project_by_issue(issue)

        def done(c, outcome, command=None):
            c.execute("INSERT OR IGNORE INTO processed_comments VALUES (?,?,?,?,?,?)",
                      (comment_id, issue, actor, command, outcome, iso()))

        if actor_type == "Bot" or (self.s.app_bot_login and actor.lower() == self.s.app_bot_login.lower()):
            with self.db.tx() as c:
                done(c, "bot_comment_ignored")
            return "bot"
        try:
            cmd = parse_command(body)
        except ParseError as e:
            with self.db.tx() as c:
                done(c, f"rejected: {e}")
                if project:
                    self.comment(c, project, f"⛔ Command rejected for @{actor}: {e}", f"rej:{comment_id}")
                else:
                    self._outbox(c, "-", "comment", {"issue": issue, "body": f"⛔ Command rejected for @{actor}: {e}"},
                                 f"rej:{comment_id}")
            record_audit_event(self.db, actor=actor, action="command.parse", outcome="rejected",
                               project_id=project["id"] if project else None, detail={"error": str(e)})
            return "rejected"
        if cmd is None:
            with self.db.tx() as c:
                done(c, "not_command")
            return "not_command"
        if created_at and updated_at and created_at != updated_at:
            with self.db.tx() as c:
                done(c, "edited_before_processing", cmd.name)
                if project:
                    self.comment(c, project, f"⛔ `{cmd.name}` was edited before it was processed and was not "
                                             "executed. Post a new comment instead.", f"rej:{comment_id}")
            record_audit_event(self.db, actor=actor, action=cmd.name, outcome="rejected_edited",
                               project_id=project["id"] if project else None)
            return "rejected"
        ctx = {"issue": issue, "comment_id": comment_id, "url": url, "actor": actor}
        try:
            handler = getattr(self, "cmd_" + cmd.name.replace(" ", "_").replace("-", "_"))
            with self.db.tx() as c:
                result = handler(c, project, cmd, ctx)
                done(c, "ok:" + (result or ""), cmd.name)
            record_audit_event(self.db, actor=actor, action=cmd.name, outcome="accepted",
                               project_id=(project or self.project_by_issue(issue) or {"id": None})["id"],
                               cycle=cmd.args.get("cycle"), version=cmd.args.get("sha"))
            return "ok"
        except CommandRejected as e:
            with self.db.tx() as c:
                done(c, f"rejected: {e}", cmd.name)
                if project:
                    self.comment(c, project, f"⛔ `{cmd.name}` rejected: {e}", f"rej:{comment_id}")
                else:
                    self._outbox(c, "-", "comment", {"issue": issue, "body": f"⛔ `{cmd.name}` rejected: {e}"},
                                 f"rej:{comment_id}")
            record_audit_event(self.db, actor=actor, action=cmd.name, outcome="rejected",
                               project_id=project["id"] if project else None,
                               cycle=cmd.args.get("cycle"), version=cmd.args.get("sha"), detail={"reason": str(e)})
            return "rejected"

    def handle_issue_closed(self, issue: int, actor: str) -> str:
        project = self.project_by_issue(issue)
        if not project:
            return "no_project"
        closure = self.db.one("SELECT * FROM closures WHERE project_id=? AND cycle=?",
                              project["id"], project["current_cycle"])
        if closure:
            with self.db.tx() as c:
                c.execute("UPDATE closures SET issue_closed_at=COALESCE(issue_closed_at, ?) WHERE project_id=? AND cycle=?",
                          (iso(), project["id"], project["current_cycle"]))
            return "closure_confirmed"
        with self.db.tx() as c:
            self.comment(c, project, "ℹ️ This issue was closed without a validated founder approval. That is **not** "
                                     "approval: the project remains open in the automation and no final report "
                                     "will be sent. G must approve through KITT (`delivery_approve_close` via the "
                                     "authorized KITT session).")
        record_audit_event(self.db, actor=actor, action="issue.closed_without_approval", outcome="ignored",
                           project_id=project["id"], cycle=project["current_cycle"])
        return "ignored_plain_close"

    # ------------------------------------------------------------------ commands
    def cmd_project_start(self, c, project, cmd, ctx):
        authorize_action(self.s, ctx["actor"], "project start", project, channel=ctx.get("channel", "github_comment"))
        if project:
            raise CommandRejected(f"Project {project['id']} already exists for this issue.")
        brief = cmd.payload
        pid = brief.get("project_id") or f"CI-{ctx['issue']:04d}"
        if c.execute("SELECT 1 FROM projects WHERE id=?", (pid,)).fetchone():
            raise CommandRejected(f"Project ID {pid} is already in use.")
        base = ctx.get("brief_sha")
        if not base:
            raise CommandRejected("Confirmed brief was not published to GitHub.")
        now = iso()
        c.execute("INSERT INTO projects(id, title, issue_number, branch, stage, status, brief_json, head_sha,"
                  " created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                  (pid, str(brief["title"]), ctx["issue"], self.s.project_branch_prefix + pid,
                   Stage.KITT_DRAFT.value, ProjectStatus.ACTIVE.value, dumps(brief), base, now, now))
        c.execute("INSERT INTO approvals(project_id, cycle, kind, decision, actor, sha, comment_id, comment_url,"
                  " details, channel, attestation_id, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                  (pid, 1, "brief", "confirmed", ctx["actor"], base, ctx["comment_id"], ctx["url"], dumps(brief),
                   ctx.get("channel", "system"), ctx.get("attestation_id"), now))
        project = c.execute("SELECT * FROM projects WHERE id=?", (pid,)).fetchone()
        self.comment(c, project, f"✅ Project **{pid}** started from G's confirmed brief (cycle 1), submitted "
                                 f"through the authorized KITT session. Brief: "
                                 f"`{ctx['brief_files'][0]['repo_path']}` @ `{base}`. Branch `{project['branch']}`. KITT is drafting the project document.")
        self.enqueue_stage(c, project, Stage.KITT_DRAFT, base,
                           files=ctx["brief_files"],
                           context={"brief": brief, "founder_decision": ctx["url"]}, source_role="FOUNDER")
        return pid

    def _require_stage(self, project, stage: Stage, cycle: int):
        if not project:
            raise CommandRejected("No project exists for this issue. G must start it through the KITT session (project_start).")
        if project["status"] == ProjectStatus.CLOSED.value:
            raise CommandRejected("Project is closed.")
        if cycle != project["current_cycle"]:
            raise CommandRejected(f"Stale cycle {cycle}; current cycle is {project['current_cycle']}.")
        if project["stage"] != stage.value:
            raise CommandRejected(f"Project is at stage {project['stage']}, not {stage.value}.")

    def _approval(self, c, project, kind, decision, ctx, sha, details) -> int:
        cur = c.execute("INSERT INTO approvals(project_id, cycle, kind, decision, actor, sha, comment_id, comment_url,"
                        " details, channel, attestation_id, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                        (project["id"], project["current_cycle"], kind, decision, ctx["actor"], sha,
                         ctx["comment_id"], ctx["url"], dumps(details), ctx.get("channel", "system"),
                         ctx.get("attestation_id"), iso()))
        return cur.lastrowid

    def _complete_gate(self, c, project):
        c.execute("UPDATE tasks SET state='COMPLETED', updated_at=? WHERE project_id=? AND state='WAITING_FOUNDER'",
                  (iso(), project["id"]))

    def cmd_initial_approve(self, c, project, cmd, ctx):
        authorize_action(self.s, ctx["actor"], "initial approve", project, channel=ctx.get("channel", "github_comment"))
        self._require_stage(project, Stage.FOUNDER_INITIAL_REVIEW, cmd.args["cycle"])
        if cmd.args["sha"] != project["current_document_sha"]:
            raise CommandRejected(f"Stale document SHA. Current document version is {project['current_document_sha']}.")
        self._approval(c, project, "initial", "approve", ctx, cmd.args["sha"], cmd.payload)
        self._complete_gate(c, project)
        self.enqueue_stage(c, project, Stage.KITT_APPLY_DECISIONS, cmd.args["sha"],
                           context={"founder_decisions": cmd.payload.get("decisions", []),
                                    "founder_comment": ctx["url"]}, source_role="FOUNDER")
        return "approved"

    def cmd_initial_changes(self, c, project, cmd, ctx):
        authorize_action(self.s, ctx["actor"], "initial changes", project, channel=ctx.get("channel", "github_comment"))
        self._require_stage(project, Stage.FOUNDER_INITIAL_REVIEW, cmd.args["cycle"])
        if cmd.args["sha"] != project["current_document_sha"]:
            raise CommandRejected(f"Stale document SHA. Current document version is {project['current_document_sha']}.")
        self._approval(c, project, "initial", "changes", ctx, cmd.args["sha"], cmd.payload)
        self._complete_gate(c, project)
        c.execute("UPDATE projects SET assignment_rev=assignment_rev+1 WHERE id=?", (project["id"],))
        project = c.execute("SELECT * FROM projects WHERE id=?", (project["id"],)).fetchone()
        self.enqueue_stage(c, project, Stage.KITT_DRAFT, cmd.args["sha"],
                           context={"brief": json.loads(project["brief_json"]),
                                    "founder_requested_changes": cmd.payload["changes"],
                                    "founder_comment": ctx["url"]}, source_role="FOUNDER")
        return "changes"

    def cmd_delivery_changes(self, c, project, cmd, ctx):
        """G -> REQUEST CHANGES in the JARVIS session. Takes effect once KITT records it."""
        authorize_action(self.s, ctx["actor"], "delivery changes", project, channel=ctx.get("channel", "github_comment"))
        self._require_stage(project, Stage.FOUNDER_FINAL_REVIEW, cmd.args["cycle"])
        if cmd.args["sha"] != project["current_delivery_sha"]:
            raise CommandRejected(f"Stale delivery SHA. Current delivery is {project['current_delivery_sha']}.")
        approval_id = self._approval(c, project, "delivery", "changes", ctx, cmd.args["sha"], cmd.payload)
        self._hand_decision_to_kitt(c, project, ctx, "delivery_changes", cmd, approval_id)
        return "changes_pending_kitt_record"

    def cmd_delivery_approve_close(self, c, project, cmd, ctx):
        """G -> APPROVE AND CLOSE in the JARVIS session. Closure happens once KITT records it."""
        authorize_action(self.s, ctx["actor"], "delivery approve-close", project, channel=ctx.get("channel", "github_comment"))
        self.validate_founder_approval(c, project, cmd.args["cycle"], cmd.args["sha"], ctx["actor"])
        approval_id = self._approval(c, project, "delivery", "approve-close", ctx, cmd.args["sha"], cmd.payload)
        self._hand_decision_to_kitt(c, project, ctx, "delivery_approve_close", cmd, approval_id)
        return "approval_pending_kitt_record"

    def _hand_decision_to_kitt(self, c, project, ctx, dtype, cmd, approval_id):
        """JARVIS passes the validated decision reference to KITT for GitHub recording."""
        self._complete_gate(c, project)
        did = ctx["attestation_id"]
        context = {"decision_id": did, "decision_type": dtype, "approval_id": approval_id,
                   "cycle": cmd.args["cycle"], "delivery_sha": cmd.args["sha"],
                   "founder_statement": cmd.payload.get("founder_statement", ""),
                   "changes": cmd.payload.get("changes", []), "route": cmd.payload.get("route"),
                   "record_file": f"approvals/founder-decision-{did}.md"}
        self.enqueue_stage(c, project, Stage.FOUNDER_DECISION_REFERENCE, cmd.args["sha"],
                           files=self._delivery_files(c, project), context=context, source_role="JARVIS")

    def _delivery_files(self, c, project) -> list:
        prev = self._latest_task(c, project["id"], project["current_cycle"], "finalize_delivery") or \
            self._latest_task(c, project["id"], project["current_cycle"], "develop_and_deliver")
        if not prev:
            return []
        return self._merge_files(json.loads(prev["manifest"])["files"],
                                 json.loads(prev["output"] or "{}").get("_published_files", []), prev["published_sha"],
                                 project["id"], prev["cycle"])

    def _apply_recorded_decision(self, c, project, task, record_sha):
        """Effect of a founder decision after KITT has recorded it on GitHub."""
        ctxd = json.loads(task["manifest"])["context"]
        dec = c.execute("SELECT * FROM founder_decisions WHERE decision_id=?", (ctxd["decision_id"],)).fetchone()
        approval = c.execute("SELECT * FROM approvals WHERE id=?", (ctxd["approval_id"],)).fetchone()
        if not dec or dec["outcome"] != "accepted" or dec["channel"] != "jarvis_session" \
                or dec["sha"] != project["current_delivery_sha"] or dec["cycle"] != project["current_cycle"] \
                or not approval or approval["attestation_id"] != dec["decision_id"]:
            raise InvalidInput("recorded decision does not match a validated JARVIS-session founder decision "
                               "for the current delivery")
        if ctxd["decision_type"] == "delivery_approve_close":
            delivery = self.validate_founder_approval(c, project, dec["cycle"], dec["sha"], approval["actor"],
                                                      stage=Stage.FOUNDER_DECISION_RECORDING)
            self.close_project(c, project, approval["id"], delivery, record_sha=record_sha)
            return
        new_cycle = project["current_cycle"] + 1
        files = self._delivery_files(c, project)
        c.execute("UPDATE projects SET current_cycle=?, assignment_rev=1, revision_loops=0, updated_at=? WHERE id=?",
                  (new_cycle, iso(), project["id"]))
        Q.supersede_open_tasks(self.db, project["id"], before_cycle=new_cycle, actor="KITT")
        c.execute("UPDATE email_outbox SET state='CANCELLED', updated_at=? WHERE project_id=? AND cycle<?"
                  " AND kind='review_package' AND state IN ('PENDING','BLOCKED')", (iso(), project["id"], new_cycle))
        project = c.execute("SELECT * FROM projects WHERE id=?", (project["id"],)).fetchone()
        stage = Stage.KITT_APPLY_DECISIONS if ctxd["route"] == "documents" else Stage.JARVIS_DEVELOPMENT
        self.comment(c, project, f"🔁 KITT recorded G's REQUEST CHANGES (decision `{dec['decision_id']}`, record "
                                 f"`{record_sha}`) for Version {new_cycle - 1} delivery `{dec['sha']}`. "
                                 f"**Version {new_cycle}** started; previous cycle preserved at that SHA. "
                                 f"Routing to {STAGE_TASK[stage][0]}. No closure and no final report.")
        self.enqueue_stage(c, project, stage, record_sha, files=files,
                           context={"founder_requested_changes": ctxd["changes"], "previous_cycle": new_cycle - 1,
                                    "previous_delivery_sha": dec["sha"], "founder_decision": dec["decision_id"]},
                           source_role="KITT")

    def cmd_project_status(self, c, project, cmd, ctx):
        authorize_action(self.s, ctx["actor"], "project status", project, channel=ctx.get("channel", "github_comment"))
        if not project:
            raise CommandRejected("No project exists for this issue.")
        rows = c.execute("SELECT role, task_type, state, input_sha, error FROM tasks WHERE project_id=? AND cycle=?"
                         " ORDER BY created_at", (project["id"], project["current_cycle"])).fetchall()
        lines = [f"**{project['id']} — {project['title']}**",
                 f"- Status: {project['status']} · Stage: {project['stage']} · Version/cycle: {project['current_cycle']}"
                 f" · Revision loops: {project['revision_loops']}/{self.s.max_revision_loops}",
                 f"- Document SHA: `{project['current_document_sha']}` · Package SHA: `{project['current_package_sha']}`"
                 f" · Delivery SHA: `{project['current_delivery_sha']}`", "", "| Role | Task | State | Input SHA |",
                 "|---|---|---|---|"]
        lines += [f"| {r['role']} | {r['task_type']} | {r['state']} | `{r['input_sha'][:12]}` |" for r in rows]
        self.comment(c, project, "\n".join(lines), f"status:{ctx['comment_id']}")
        return "status"

    def cmd_project_pause(self, c, project, cmd, ctx):
        authorize_action(self.s, ctx["actor"], "project pause", project, channel=ctx.get("channel", "github_comment"))
        if not project or project["status"] != ProjectStatus.ACTIVE.value:
            raise CommandRejected("Only an active project can be paused.")
        c.execute("UPDATE projects SET status='PAUSED', updated_at=? WHERE id=?", (iso(), project["id"]))
        self.comment(c, project, "⏸️ Project paused by G. No new tasks will start until G resumes through KITT.")
        return "paused"

    def cmd_project_resume(self, c, project, cmd, ctx):
        authorize_action(self.s, ctx["actor"], "project resume", project, channel=ctx.get("channel", "github_comment"))
        if not project or project["status"] == ProjectStatus.CLOSED.value:
            raise CommandRejected("No resumable project.")
        if project["stage"] == Stage.FOUNDER_DECISION.value:
            reason = json.loads(project["blocked_reason"] or "{}")
            want = reason.get("channel", "kitt_session")
            if ctx.get("channel") != want:
                raise CommandRejected(f"This escalation must be decided by G in the "
                                      f"{'KITT' if want == 'kitt_session' else 'JARVIS'} session.")
            decisions = cmd.payload.get("decisions")
            if not isinstance(decisions, list) or not decisions:
                raise CommandRejected("Project awaits G's decision: `project_resume` needs a non-empty "
                                      "`decisions` list.")
            self._complete_gate(c, project)
            c.execute("UPDATE projects SET status='ACTIVE', revision_loops=0, assignment_rev=assignment_rev+1,"
                      " blocked_reason=NULL, updated_at=? WHERE id=?", (iso(), project["id"]))
            Q.supersede_open_tasks(self.db, project["id"], stage=reason.get("resume_stage"), actor=ctx["actor"])
            project = c.execute("SELECT * FROM projects WHERE id=?", (project["id"],)).fetchone()
            self.enqueue_stage(c, project, Stage(reason["resume_stage"]), reason["input_sha"],
                               files=reason.get("files", []),
                               context={**reason.get("context", {}), "founder_decisions": decisions,
                                        "founder_comment": ctx["url"]}, source_role="FOUNDER")
        else:
            c.execute("UPDATE projects SET status='ACTIVE', updated_at=? WHERE id=?", (iso(), project["id"]))
            c.execute("UPDATE tasks SET state='QUEUED', attempts=0, next_attempt_at=?, error=NULL, updated_at=?"
                      " WHERE project_id=? AND cycle=? AND state='BLOCKED'",
                      (iso(), iso(), project["id"], project["current_cycle"]))
        self.comment(c, project, "▶️ Project resumed by G.")
        return "resumed"

    def cmd_handoff(self, c, project, cmd, ctx):
        if not project:
            raise CommandRejected("No project exists for this issue.")
        m, a = cmd.payload, cmd.args
        if m["project_id"] != project["id"]:
            raise CommandRejected("Manifest project_id does not match this tracking issue.")
        task = c.execute("SELECT * FROM tasks WHERE id=? AND project_id=?", (m["task_id"], project["id"])).fetchone()
        if not task or task["state"] != "RUNNING" or not task["external"]:
            raise CommandRejected(f"Task {m['task_id']} is not an open assigned task (it may be superseded or done).")
        if task["task_type"] != a["task_type"] or task["cycle"] != a["cycle"]:
            raise CommandRejected("Task type or cycle does not match the assigned task.")
        if task["cycle"] != project["current_cycle"] or m["revision"] != task["assignment_rev"]:
            raise CommandRejected("Obsolete assignment: cycle/revision is not current.")
        role = authorize_action(self.s, ctx["actor"], "handoff", project, task=task, dest_role=a["role"])
        if m["source_role"].upper() != role:
            raise CommandRejected("source_role does not match the assigned role.")
        verdict = m.get("verdict") or self._verdict_for_dest(task["task_type"], a["role"])
        files = {}
        # Exact version only: every listed file must exist at the referenced commit.
        try:
            self.gh.get_commit(a["sha"])
        except InvalidInput:
            raise CommandRejected(f"Commit {a['sha']} not found in {self.s.repo_full_name}.")
        for rel in m["files"]:
            path = L.repo_path(project["id"], task["cycle"], rel)
            content = self.gh.get_file(path, a["sha"])
            if content is None:
                raise CommandRejected(f"File {path} does not exist at {a['sha']}. Publish files before handoff.")
            files[rel] = content
        output = {"verdict": verdict, "files": files, "summary": m.get("summary", ""),
                  "blockers": m.get("blockers", []), "limitations": m.get("limitations", []),
                  "next_action": m["next_action"], "input_sha": task["input_sha"]}
        self.validate_output(task, output, project)
        self.complete_and_route(c, task, output, a["sha"], actor=ctx["actor"], external=True,
                                handoff_comment_id=ctx["comment_id"])
        return "handoff"

    @staticmethod
    def _verdict_for_dest(task_type: str, dest: str) -> str:
        options = [v for (tt, v), st in ROUTES.items() if tt == task_type and STAGE_TASK[st][0] == dest]
        if task_type == "council_review":
            return "done"
        if len(options) != 1:
            raise CommandRejected("Manifest must include `verdict` for this task type: "
                                  + ", ".join(sorted(VERDICTS.get(task_type, []))))
        return options[0]

    # --------------------------------------------------------------- enqueueing
    @staticmethod
    def _merge_files(base: list, paths: list, sha: str, pid: str | None = None, cycle: int | None = None) -> list:
        """Merge published logical paths (at commit `sha`) into a manifest file list.
        With pid/cycle the WORKFLOW.md repo path is pinned, so later cycles read the right version."""
        out = {f["path"]: f for f in base}
        for p in paths:
            entry = {"path": p, "sha": sha}
            if pid is not None:
                entry["repo_path"] = L.repo_path(pid, cycle, p)
            out[p] = entry
        return sorted(out.values(), key=lambda f: f["path"])

    def enqueue_stage(self, c, project, stage: Stage, input_sha: str, *, files=None, context=None,
                      source_role: str = "SYSTEM", role_override: str | None = None):
        role, task_type = STAGE_TASK[stage]
        if role_override:
            role, task_type = role_override, "council_review"
        c.execute("UPDATE projects SET stage=?, updated_at=? WHERE id=?", (stage.value, iso(), project["id"]))
        project = c.execute("SELECT * FROM projects WHERE id=?", (project["id"],)).fetchone()
        manifest = {
            "project_id": project["id"], "cycle": project["current_cycle"], "revision": project["assignment_rev"],
            "source_role": source_role, "dest_role": role, "task_type": task_type, "input_sha": input_sha,
            "files": files or [], "expected_outputs": EXPECTED_OUTPUTS.get(task_type, [])
            if task_type != "council_review" else [f"council/reviews/{role}.md"],
            "next_action": f"{role}: perform {task_type}", "context": context or {},
        }
        if role == "FOUNDER":
            state, external = TaskState.WAITING_FOUNDER, False
        elif task_type in ("council_dispatch", "publish_decision_reference"):  # mechanical, never a model call
            state, external = TaskState.QUEUED, False
        else:
            external = bool(getattr(self.adapters.get(role), "external", False))
            state = TaskState.RUNNING if external else TaskState.QUEUED
        deadline = self.s.council_timeout_minutes if task_type == "council_review" else (
            None if role == "FOUNDER" else self.s.stage_timeout_minutes)
        tid, created = Q.enqueue_task(self.db, project_id=project["id"], cycle=project["current_cycle"],
                                      stage=stage.value, role=role, task_type=task_type, input_sha=input_sha,
                                      assignment_rev=project["assignment_rev"], manifest=manifest, state=state,
                                      external=external, deadline_minutes=deadline)
        if not created:
            return tid
        manifest["task_id"] = tid
        c.execute("UPDATE tasks SET manifest=? WHERE id=?", (dumps(manifest), tid))
        if external:
            c.execute("UPDATE tasks SET lease_owner='external', heartbeat_at=? WHERE id=?", (iso(), tid))
            self.comment(c, project, self._assignment_comment(project, manifest), f"assign:{tid}")
        if role == "FOUNDER":
            self.comment(c, project, self._founder_gate_comment(project, stage, input_sha, context or {}),
                         f"gate:{tid}")
        if stage == Stage.FOUNDER_FINAL_REVIEW:
            # Step 11.3: JARVIS emails the review package (Review Required, never "Project Closed").
            cyc = project["current_cycle"]
            c.execute("INSERT OR IGNORE INTO email_outbox(email_key, kind, to_addr, delivery_sha, project_id, cycle,"
                      " approval_id, state, rfc822_message_id, next_attempt_at, created_at, updated_at)"
                      " VALUES (?, 'review_package', ?,?,?,?, NULL, 'PENDING', ?,?,?,?)",
                      (f"review:{project['id']}|{cyc}|{input_sha}", REVIEW_PACKAGE_TO, input_sha, project["id"], cyc,
                       f"<coint-review-{project['id']}-v{cyc}-{input_sha[:12]}@co-intelligence.resystem.org>",
                       iso(), iso(), iso()))
        return tid

    def _assignment_comment(self, project, m) -> str:
        login = self.s.adapters[m["dest_role"]].github_login
        return (f"📋 **Assignment** for {m['dest_role']} (@{login}) — task `{m['task_id']}`\n\n"
                f"- Project `{m['project_id']}` · cycle {m['cycle']} · revision {m['revision']}\n"
                f"- Task type `{m['task_type']}` · input commit `{m['input_sha']}`\n"
                f"- Inputs: " + (", ".join(f"`{f['path']}@{f['sha'][:12]}`" for f in m["files"]) or "(context only)") +
                "\n- Expected outputs: " +
                ", ".join(f"`{p}` → `{L.repo_path(m['project_id'], m['cycle'], p)}`" for p in m["expected_outputs"]) +
                f"\n\nPublish the files on branch `{project['branch']}` first, then comment:\n"
                f"```\n/handoff <next_role> {m['task_type']} {m['cycle']} <commit_sha>\n```\nwith a ```json manifest "
                f"(project_id, task_id, revision, source_role, files, expected_outputs, next_action, verdict).")

    @staticmethod
    def gate_channel(stage: Stage, context: dict | None = None) -> str:
        """Which founder session owns a gate (role summary)."""
        if stage == Stage.FOUNDER_FINAL_REVIEW:
            return "jarvis_session"
        if stage == Stage.FOUNDER_DECISION:
            return (context or {}).get("channel", "kitt_session")
        return "kitt_session"

    def _founder_gate_comment(self, project, stage, sha, context) -> str:
        """Review notification on the tracking issue, addressed to the agent who presents it to G."""
        cyc, pid = project["current_cycle"], project["id"]
        tree = f"{GITHUB_URL}/tree/{sha}/{pid}"
        dv = f"{GITHUB_URL}/blob/{sha}/deliveries/{pid}/v{cyc}"
        if self.gate_channel(stage, context) == "jarvis_session":
            who, login, where = "JARVIS", self.s.adapters["JARVIS"].github_login, "the JARVIS chat"
            pending = "`/jarvis/pending`"
        else:
            who, login, where = "KITT", self.s.adapters["KITT"].github_login, "KITT's ChatGPT"
            pending = "`listPendingFounderReviews`"
        head = (f"📨 **Review Required — for {who} to present to G**{f' (@{login})' if login else ''} · "
                f"`{pid}` · Version {cyc}\n\n")
        tail = (f"\n\n{who}: present this to G in {where} ({pending}). Submit only G's explicit decision, in G's own "
                f"words, through the authorized {who} session integration. A GitHub comment or agent statement is "
                "**not** a decision and will be rejected.")
        if stage == Stage.FOUNDER_INITIAL_REVIEW:
            return head + (f"KITT's project document is ready for G's initial review.\n\n- Exact version: `{sha}`\n"
                           f"- Files: {tree}\n- Decisions: `initial_approve` or `initial_changes` "
                           f"(with `changes`), `project_id` `{pid}`, `cycle` {cyc}, `sha` `{sha}`.") + tail
        if stage == Stage.FOUNDER_FINAL_REVIEW:
            return head + (f"KITT has reviewed the delivery and JARVIS has addressed the findings — "
                           f"**Awaiting Founder Final Review** (G ↔ JARVIS).\n\n"
                           f"- Exact delivery: tag `{L.delivery_tag(pid, cyc)}` · commit `{sha}`\n"
                           f"- Delivery: {dv}/DELIVERY.md · Final report draft: {dv}/FINAL-REPORT.md\n"
                           f"- Verification: {dv}/VERIFICATION.md · KITT review: {dv}/KITT_REVIEW.md · "
                           f"Findings: {dv}/FINDINGS.md\n"
                           f"- Review package email → {REVIEW_PACKAGE_TO} (status in `/jarvis/pending`)\n"
                           f"- G chooses **APPROVE AND CLOSE** (`delivery_approve_close`) or **REQUEST CHANGES** "
                           f"(`delivery_changes` with `changes` and `route`), `project_id` `{pid}`, `cycle` {cyc}, "
                           f"`sha` `{sha}`. KITT then records the decision on GitHub.") + tail
        return head + (f"G's decision is required before work can continue: {context.get('reason', '')}\n\n"
                       f"- Reference version `{sha}` · {tree}\n- Decision: `project_resume` with `decisions`.") + tail

    # --------------------------------------------------- trusted founder channel
    def pending_reviews(self, include_content: bool = True, max_chars: int = 20000,
                        channel: str | None = None) -> list[dict]:
        """Founder questions / review packages awaiting G, for the session that owns them."""
        out = []
        for p in self.db.all("SELECT * FROM projects WHERE status IN ('ACTIVE','PAUSED')"):
            gate = self.db.one("SELECT * FROM tasks WHERE project_id=? AND state='WAITING_FOUNDER'"
                               " ORDER BY created_at DESC LIMIT 1", p["id"])
            if not gate:
                continue
            stage, sha = Stage(gate["stage"]), gate["input_sha"]
            gctx = json.loads(gate["manifest"]).get("context", {})
            owner = self.gate_channel(stage, gctx)
            if channel and owner != channel:
                continue
            item = {"project_id": p["id"], "title": p["title"], "stage": stage.value, "cycle": p["current_cycle"],
                    "sha": sha, "tracking_issue": f"{GITHUB_URL}/issues/{p['issue_number']}",
                    "files_url": f"{GITHUB_URL}/tree/{sha}/" + (f"deliveries/{p['id']}/v{p['current_cycle']}"
                                                                if stage == Stage.FOUNDER_FINAL_REVIEW else p["id"]),
                    "waiting_since": gate["created_at"]}
            if stage == Stage.FOUNDER_INITIAL_REVIEW:
                item["allowed_decisions"], paths = ["initial_approve", "initial_changes"], [
                    "documents/project-document.md"]
            elif stage == Stage.FOUNDER_FINAL_REVIEW:
                item["delivery_tag"] = L.delivery_tag(p["id"], p["current_cycle"])
                item["allowed_decisions"], paths = ["delivery_approve_close", "delivery_changes"], [
                    "delivery/delivery.md", "delivery/final-report.md", "verification/verification-report.json",
                    "reviews/jarvis/finding-dispositions.json", "reviews/kitt/delivery-review.md",
                    "reviews/jarvis/kitt-findings-response.json"]
                em = self.db.one("SELECT * FROM email_outbox WHERE kind='review_package' AND project_id=? AND cycle=?"
                                 " AND delivery_sha=?", p["id"], p["current_cycle"], sha)
                item["review_package_email"] = {
                    "to": REVIEW_PACKAGE_TO, "state": em["state"] if em else "NOT_QUEUED",
                    "gmail_message_id": em["gmail_message_id"] if em else None,
                    "accepted_at": em["accepted_at"] if em else None,
                    "error": em["last_error"] if em and em["state"] != "SENT" else None,
                    "chat_confirmation": (f"The review package has been emailed to {REVIEW_PACKAGE_TO}."
                                          if em and em["state"] == "SENT" else None),
                    "instruction": ("Say chat_confirmation verbatim only when state is SENT. Otherwise report the "
                                    "state and error accurately; never claim it was sent."),
                }
            else:
                item["allowed_decisions"], paths = ["project_resume"], []
                item["question"] = gctx.get("reason", "")
            if include_content:
                item["documents"] = {}
                for rel in paths:
                    try:
                        txt = self.gh.get_file(L.repo_path(p["id"], p["current_cycle"], rel), sha)
                    except Exception:  # noqa: BLE001
                        txt = None
                    if txt is not None:
                        item["documents"][rel] = txt[:max_chars] + ("\n…[truncated]" if len(txt) > max_chars else "")
            item["owner_session"] = owner
            out.append(item)
        return out

    def founder_decision(self, att, req: dict) -> dict:
        """Execute one explicit founder decision verified by KittSessionVerifier.

        Returns {"status": http_status, "outcome": ..., "message": ...}."""
        import hashlib
        import re
        from .commands import (Command, ParseError, validate_brief, validate_brief_ref, validate_changes,
                               _cycle, _sha)
        from .kitt_session import CHANNEL_DECISIONS, DECISION_TYPES, channel_app

        did = str(req.get("decision_id") or "")
        if not re.match(r"^[A-Za-z0-9-]{8,64}$", did):
            return {"status": 400, "outcome": "rejected", "message": "decision_id must be 8-64 chars [A-Za-z0-9-]"}
        rhash = hashlib.sha256(dumps(req).encode()).hexdigest()
        prev = self.db.one("SELECT * FROM founder_decisions WHERE decision_id=?", did)
        if prev:
            if prev["request_hash"] != rhash:
                return {"status": 409, "outcome": "rejected", "message": "decision_id reused with different content"}
            return {"status": 200 if prev["outcome"] == "accepted" else 400, "outcome": prev["outcome"],
                    "message": prev["detail"] or "", "duplicate": True}
        dtype = req.get("decision_type")
        action = DECISION_TYPES.get(dtype)
        channel = att.channel
        if channel not in CHANNEL_DECISIONS or not channel_app(self.s, channel)[0] or \
                att.oauth_client_id != channel_app(self.s, channel)[0]:
            record_audit_event(self.db, actor=att.github_login, action=f"founder_decision.{dtype}",
                               outcome="rejected", detail={"decision_id": did, "reason": "untrusted session app"})
            return {"status": 401, "outcome": "rejected", "message": "not an authorized founder session"}

        def record(outcome, detail, project_id=None):
            with self.db.tx() as c:
                c.execute("INSERT OR IGNORE INTO founder_decisions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                          (did, str(dtype), project_id or req.get("project_id"), req.get("cycle"), req.get("sha"),
                           dumps(req), rhash, att.github_login, att.github_user_id, att.oauth_client_id,
                           att.token_fingerprint, channel, outcome, detail, iso()))
            record_audit_event(self.db, actor=att.github_login, action=f"founder_decision.{dtype}", outcome=outcome,
                               project_id=project_id or req.get("project_id"), cycle=req.get("cycle"),
                               version=req.get("sha"), detail={"decision_id": did, "channel": "kitt_session",
                                                               "detail": detail, "session": channel})

        def reject(msg, project=None):
            record("rejected", msg, project["id"] if project else None)
            if project:
                with self.db.tx() as c:
                    self.comment(c, project, f"⛔ Founder decision `{did}` ({dtype}) from the "
                                             f"{channel.replace('_', ' ')} was rejected: {msg}", f"fdrej:{did}")
                self.dispatch_outbox()
            return {"status": 400, "outcome": "rejected", "message": msg}

        if not action:
            return reject(f"decision_type must be one of {sorted(CHANNEL_DECISIONS[channel])}")
        if dtype not in CHANNEL_DECISIONS[channel]:
            owner = "JARVIS" if channel == "kitt_session" else "KITT"
            return reject(f"`{dtype}` cannot be decided in the {channel.replace('_', ' ')}; G makes this decision "
                          f"with {owner}.", self.project(str(req.get("project_id") or "")))
        statement = str(req.get("founder_statement") or "").strip()
        if not statement:
            return reject("founder_statement (G's decision in G's own words) is required")
        try:
            args, payload = {}, {}
            if dtype == "project_start":
                payload = validate_brief(req.get("brief")) if req.get("brief") is not None or \
                    not req.get("brief_ref") else validate_brief_ref(req)
            else:
                if dtype not in ("project_pause", "project_resume"):
                    args = {"cycle": _cycle(str(req.get("cycle", ""))), "sha": _sha(str(req.get("sha", "")))}
                for k in ("changes", "route", "decisions"):
                    if k in req:
                        payload[k] = req[k]
                if dtype in ("initial_changes", "delivery_changes"):
                    validate_changes(payload, need_route=(dtype == "delivery_changes"))
        except ParseError as e:
            return reject(str(e))
        payload["founder_statement"] = statement

        project = None
        brief_sha, brief_files = None, []
        if dtype == "project_start":
            pid = payload.get("project_id")
            if pid and self.project(pid):
                return reject(f"Project ID {pid} is already in use.")
            issue = req.get("issue_number")
            if issue is not None:
                if self.project_by_issue(int(issue)):
                    return reject("That tracking issue already has a project.")
                issue = int(issue)
            else:
                issue = self.gh.create_issue(
                    f"[Project] {payload['title']}",
                    "Tracking issue created from G's confirmed brief submitted through the authorized KITT session."
                    f"\n\nFounder decision `{did}`.\n\n```json\n{json.dumps(payload, indent=2)}\n```")
            pid = pid or f"CI-{issue:04d}"
            payload["project_id"] = pid
            if payload.get("brief_ref"):
                # Adopt a brief KITT already published (e.g. FLOW-TEST-001/INITIAL-BRIEF-v1.0.md) at its exact SHA.
                ref = payload["brief_ref"]
                try:
                    exists = self.gh.get_file(ref["path"], ref["sha"]) is not None
                except InvalidInput:
                    exists = False
                if not exists:
                    return reject(f"brief_ref {ref['path']} does not exist at {ref['sha']}.")
                brief_sha = ref["sha"]
                brief_files = [{"path": "brief/" + ref["path"].rsplit("/", 1)[-1], "sha": ref["sha"],
                                "repo_path": ref["path"]}]
            else:
                rp = L.repo_path(pid, 1, "brief/confirmed-brief.json")
                brief_sha = self.gh.commit_files(
                    self.s.project_branch_prefix + pid,
                    {rp: json.dumps({**payload, "_coint": {"project_id": pid, "cycle": 1, "revision": 1,
                                                           "decision_id": did, "confirmed_by": att.github_login,
                                                           "channel": "kitt_session"}}, indent=2) + "\n"},
                    f"[coint] {pid} confirmed brief from KITT session\n\nfounder decision: {did}")
                brief_files = [{"path": "brief/confirmed-brief.json", "sha": brief_sha, "repo_path": rp}]
        else:
            project = self.project(str(req.get("project_id") or ""))
            if not project:
                return reject("Unknown project_id.")
            issue = project["issue_number"]

        ctx = {"issue": issue, "comment_id": None, "url": f"{channel}:{did}", "actor": att.github_login,
               "channel": channel, "attestation_id": did, "brief_sha": brief_sha, "brief_files": brief_files}
        cmd = Command(action, args, payload)
        handler = getattr(self, "cmd_" + action.replace(" ", "_").replace("-", "_"))
        try:
            with self.db.tx() as c:
                result = handler(c, project, cmd, ctx)
                project = project or c.execute("SELECT * FROM projects WHERE issue_number=?", (issue,)).fetchone()
                record("accepted", result or "", project["id"])
                self.comment(c, project, self._decision_record_comment(att, did, dtype, req, statement),
                             f"fdok:{did}")
        except CommandRejected as e:
            return reject(str(e), project)
        self.dispatch_outbox()
        return {"status": 200, "outcome": "accepted", "message": result or "", "project_id": project["id"],
                "decision_id": did}

    @staticmethod
    def _decision_record_comment(att, did, dtype, req, statement) -> str:
        quoted = "\n".join("> " + line for line in statement.splitlines())
        if att.channel == "jarvis_session":
            title = (f"✅ **Founder decision validated (JARVIS session)** — `{dtype}` · decision `{did}` · "
                     "passed to KITT for GitHub recording; no effect until KITT records it")
        else:
            title = f"🧾 **Founder decision recorded (KITT session)** — `{dtype}` · decision `{did}`"
        sess = "JARVIS" if att.channel == "jarvis_session" else "KITT"
        return (f"{title}\n\n"
                f"- Project `{req.get('project_id', '(new)')}` · cycle {req.get('cycle', 1)} · version "
                f"`{req.get('sha', '—')}`\n- Channel: authorized {sess} session (GitHub OAuth app "
                f"`{att.oauth_client_id}`); identity verified as @{att.github_login} (id {att.github_user_id}); "
                f"token fingerprint `{att.token_fingerprint[:12]}`\n- G's statement:\n{quoted}")

    # ---------------------------------------------------------------- execution
    def run_task(self, task_id: str) -> str:
        """Claim and execute one task. Safe to call concurrently from webhook
        pickup and scheduled recovery: only one claim can succeed."""
        if not Q.claim_task(self.db, task_id, self.worker_id, self.s.lease_seconds):
            return "not_claimed"
        task = Q.get_task(self.db, task_id)
        project = self.project(task["project_id"])
        stop = threading.Event()
        hb = threading.Thread(target=self._heartbeat_loop, args=(task_id, stop), daemon=True)
        hb.start()
        try:
            self._assert_current(task, project)
            if task["task_type"] == "publish_decision_reference":
                return self._publish_decision_reference(task, project)
            if task["task_type"] == "council_dispatch":
                with self.db.tx() as c:
                    self._assert_current(task, self.project(task["project_id"]))
                    self.dispatch_council(c, project, task)
                return "dispatched"
            if task["checkpoint"]:
                output = json.loads(task["checkpoint"])
            else:
                inputs = self.load_manifest(project, task)
                output = self.run_agent(task["role"], task, inputs)
                self.validate_output(task, output, project)
                Q.save_checkpoint(self.db, task_id, self.worker_id, output)  # checkpoint before external actions
            sha = task["published_sha"] or self.publish_output(task, output, project)
            if not task["published_sha"]:
                Q.save_published_sha(self.db, task_id, self.worker_id, sha)
            with self.db.tx() as c:
                self.complete_and_route(c, Q.get_task(self.db, task_id), output, sha, actor=task["role"])
            return "completed"
        except StaleAssignment as e:
            with self.db.tx() as c:
                c.execute("UPDATE tasks SET state='SUPERSEDED', lease_owner=NULL, error=?, updated_at=? WHERE id=?",
                          (str(e), iso(), task_id))
            record_audit_event(self.db, actor=self.worker_id, action="task.reject_obsolete", outcome="SUPERSEDED",
                               project_id=task["project_id"], cycle=task["cycle"], detail={"task_id": task_id})
            return "superseded"
        except TransientError as e:
            return Q.fail_transient(self.db, task_id, self.worker_id, str(e), self.s.retry_delays_minutes)
        except PermanentError as e:
            Q.block_task(self.db, task_id, f"{type(e).__name__}: {e}", actor=self.worker_id)
            with self.db.tx() as c:
                self.comment(c, project, f"🚫 Task `{task_id}` ({task['role']} {task['task_type']}) is **BLOCKED**: "
                                         f"{type(e).__name__}: {e}\n\nFix the cause, then G can resume through KITT (`project_resume`).",
                             f"blocked:{task_id}:{task['attempts']}")
            return "blocked"
        finally:
            stop.set()
            hb.join(timeout=5)
            self.dispatch_outbox()

    def _heartbeat_loop(self, task_id: str, stop: threading.Event):
        while not stop.wait(self.s.heartbeat_seconds):
            if not Q.heartbeat(self.db, task_id, self.worker_id, self.s.lease_seconds):
                return

    def _assert_current(self, task, project):
        if task["state"] in ("SUPERSEDED", "CANCELLED"):
            raise StaleAssignment("task superseded")
        if task["cycle"] != project["current_cycle"]:
            raise StaleAssignment(f"cycle {task['cycle']} replaced by {project['current_cycle']}")
        if task["assignment_rev"] != project["assignment_rev"]:
            raise StaleAssignment("assignment revision replaced")
        if task["task_type"] == "council_review":
            if project["stage"] != Stage.COUNCIL_REVIEW.value or task["input_sha"] != project["current_package_sha"]:
                raise StaleAssignment("council package replaced")
        elif task["stage"] != project["stage"]:
            raise StaleAssignment(f"stage moved to {project['stage']}")

    def load_manifest(self, project, task) -> dict[str, str]:
        """Fetch the exact input version (never a moving 'latest')."""
        m = json.loads(task["manifest"])
        self.gh.get_commit(task["input_sha"])  # must exist (unmerged commits allowed)
        inputs = {}
        for f in m["files"]:
            path = L.file_repo_path(project["id"], task["cycle"], f)
            content = self.gh.get_file(path, f["sha"])
            if content is None:
                raise InvalidInput(f"required input {path} missing at {f['sha']}")
            inputs[f["path"]] = content
        return inputs

    def run_agent(self, role: str, task, inputs: dict[str, str]) -> dict:
        adapter = self.adapters[role]
        m = json.loads(task["manifest"])
        prompt_file = ROLE_PROMPT.get(role, "council_reviewer.md")
        system = "\n\n".join([_read_prompt("common.md"), _read_prompt(prompt_file), _read_prompt("OUTPUT_SCHEMA.md")])
        meta = {k: m[k] for k in ("project_id", "cycle", "revision", "task_id", "task_type", "input_sha",
                                  "source_role", "expected_outputs")}
        meta["your_role"] = role
        meta["allowed_verdicts"] = sorted(VERDICTS[task["task_type"]])
        parts = [f"TASK:\n{json.dumps(meta, indent=2)}",
                 "Echo `input_sha` exactly in your JSON output.",
                 "<repository_data kind=\"task_context\">\n" + json.dumps(m.get("context", {}), indent=2)
                 + "\n</repository_data>"]
        for path, content in sorted(inputs.items()):
            parts.append(f"<repository_data path=\"{path}\">\n{content}\n</repository_data>")
        return adapter.run(AgentRequest(role=role, task_type=task["task_type"], system=system,
                                        user="\n\n".join(parts)))

    def validate_output(self, task, output: dict, project) -> None:
        """Schema, files, input version and completeness."""
        tt = task["task_type"]
        if output.get("verdict") not in VERDICTS.get(tt, set()):
            raise InvalidInput(f"verdict {output.get('verdict')!r} not allowed for {tt}")
        if output.get("input_sha") != task["input_sha"]:
            raise InvalidInput(f"output was produced for input {output.get('input_sha')!r}, expected {task['input_sha']}")
        files = output.get("files")
        if not isinstance(files, dict):
            raise InvalidInput("`files` must be an object of path -> content")
        for p, content in files.items():
            if not isinstance(content, str) or ".." in p.split("/") or p.startswith("/") \
                    or not p.startswith(ALLOWED_PREFIXES):
                raise InvalidInput(f"invalid output path {p!r}")
        required = list(EXPECTED_OUTPUTS.get(tt, []))
        if tt == "record_founder_decision":
            required = [json.loads(task["manifest"])["context"]["record_file"]]
        if tt == "council_review":
            required = [f"council/reviews/{task['role']}.md"]
            if task["input_sha"] not in files.get(required[0], ""):
                raise InvalidInput("council review must state the exact frozen package SHA it reviewed")
        if tt == "freeze_council_package" and output["verdict"] == "feedback_not_addressed":
            required = ["reviews/jarvis/doc-review.md"]
        missing = [p for p in required if not (files.get(p) or "").strip()]
        if missing:
            raise InvalidInput(f"missing required outputs: {missing}")
        if tt == "freeze_council_package" and output["verdict"] == "frozen":
            man = _json(files, "council/packages/manifest.json")
            if not isinstance(man.get("includes"), list) or not man["includes"]:
                raise InvalidInput("council manifest `includes` must be a non-empty list")
            for k in ("approved_requirements", "acceptance_criteria", "open_questions"):
                if not isinstance(man.get(k), list):
                    raise InvalidInput(f"council manifest `{k}` must be a list")
        if tt == "council_draft":
            idx = _json(files, "council/drafts/findings-index.json")
            if not isinstance(idx.get("findings"), list):
                raise InvalidInput("findings-index.json needs a `findings` list")
        if tt == "delivery_review":
            kf = _json(files, "reviews/kitt/delivery-findings.json").get("findings")
            if not isinstance(kf, list) or any(not isinstance(f, dict) or not f.get("id") for f in kf):
                raise InvalidInput("delivery-findings.json needs a `findings` list of objects with `id`")
        if tt == "record_founder_decision":
            ctxd = json.loads(task["manifest"])["context"]
            rec = files.get(ctxd["record_file"], "")
            for needle in (ctxd["decision_id"], ctxd["decision_type"], ctxd["delivery_sha"]):
                if needle not in rec:
                    raise InvalidInput(f"KITT's decision record must cite {needle!r} (validated decision reference)")
        if tt == "finalize_delivery":
            resp = _json(files, "reviews/jarvis/kitt-findings-response.json").get("responses")
            if not isinstance(resp, list):
                raise InvalidInput("kitt-findings-response.json needs a `responses` list")
            missing = self._kitt_findings_for(task) - {r.get("finding_id") for r in resp}
            if missing:
                raise InvalidInput(f"KITT findings not addressed: {sorted(missing)}")
        if tt in ("develop_and_deliver", "finalize_delivery"):
            ver = _json(files, "verification/verification-report.json")
            if ver.get("status") not in ("passed", "failed", "partial") or not isinstance(ver.get("checks"), list):
                raise InvalidInput("verification report needs status passed|failed|partial and a checks list")
            if not isinstance(ver.get("development_complete"), bool):
                raise InvalidInput("verification report needs boolean development_complete")
            disp = _json(files, "reviews/jarvis/finding-dispositions.json").get("dispositions")
            if not isinstance(disp, list):
                raise InvalidInput("finding-dispositions.json needs a `dispositions` list")
            ok = {"accepted", "rejected", "resolved", "requires_founder_decision"}
            for d in disp:
                if d.get("disposition") not in ok:
                    raise InvalidInput(f"bad disposition {d}")
                if d["disposition"] in ("rejected", "requires_founder_decision") and not d.get("reason"):
                    raise InvalidInput(f"disposition for {d.get('finding_id')} needs a reason")
            findings = self._findings_for(task)
            have = {d.get("finding_id") for d in disp}
            if findings - have:
                raise InvalidInput(f"findings without disposition: {sorted(findings - have)}")

    def _kitt_findings_for(self, task) -> set:
        m = json.loads(task["manifest"])
        f = next((f for f in m["files"] if f["path"] == "reviews/kitt/delivery-findings.json"), None)
        if not f:
            return set()
        raw = self.gh.get_file(L.file_repo_path(task["project_id"], task["cycle"], f), f["sha"]) or "{}"
        return {x.get("id") for x in json.loads(raw).get("findings", [])}

    def _findings_for(self, task) -> set:
        m = json.loads(task["manifest"])
        f = next((f for f in m["files"] if f["path"] == "council/drafts/findings-index.json"), None)
        if not f:
            return set()
        raw = self.gh.get_file(L.file_repo_path(task["project_id"], task["cycle"], f), f["sha"]) or "{}"
        return {x.get("id") for x in json.loads(raw).get("findings", [])}

    def publish_output(self, task, output: dict, project) -> str:
        """Publish artifacts with cycle/revision metadata; returns the exact commit SHA."""
        meta = {"project_id": task["project_id"], "cycle": task["cycle"], "revision": task["assignment_rev"],
                "task_id": task["id"], "role": task["role"], "task_type": task["task_type"],
                "input_sha": task["input_sha"]}
        files = {}
        for rel, content in output["files"].items():
            if rel.endswith(".json"):
                obj = json.loads(content)
                if isinstance(obj, dict):
                    obj["_coint"] = meta
                content = json.dumps(obj, indent=2) + "\n"
            elif rel.endswith(".md"):
                content = f"<!-- coint-meta: {json.dumps(meta, sort_keys=True)} -->\n" + content
            files[L.repo_path(project["id"], task["cycle"], rel)] = content
            files.update(L.derived_files(project["id"], task["cycle"], rel, content))
        msg = (f"[coint] {task['project_id']} v{task['cycle']} r{task['assignment_rev']} {task['role']} "
               f"{task['task_type']}\n\ntask: {task['id']}\ninput: {task['input_sha']}")
        return self.gh.commit_files(project["branch"], files, msg)

    # -------------------------------------------------------- completion/routing
    def complete_and_route(self, c, task, output: dict, output_sha: str, *, actor: str, external: bool = False,
                           handoff_comment_id: int | None = None):
        """Atomically persist completion, handoff record and the next-stage work + outbox events."""
        project = c.execute("SELECT * FROM projects WHERE id=?", (task["project_id"],)).fetchone()
        self._assert_current(task, project)
        owner_ok = "lease_owner='external'" if external else "lease_owner=?"
        args = () if external else (self.worker_id,)
        published = sorted(output["files"].keys())
        stored = {k: v for k, v in output.items() if k != "files"}
        stored["_published_files"] = published
        cur = c.execute(f"UPDATE tasks SET state='COMPLETED', output=?, published_sha=?, lease_owner=NULL,"
                        f" lease_expires_at=NULL, updated_at=? WHERE id=? AND state='RUNNING' AND {owner_ok}",
                        (dumps(stored), output_sha, iso(), task["id"], *args))
        if cur.rowcount != 1:
            raise StaleAssignment("task no longer owned/running")
        m = json.loads(task["manifest"])
        files = self._merge_files(m["files"], published, output_sha, task["project_id"], task["cycle"])
        tt, verdict, pid = task["task_type"], output["verdict"], project["id"]
        c.execute("UPDATE projects SET head_sha=?, updated_at=? WHERE id=?", (output_sha, iso(), pid))

        if tt == "council_review":
            self._record_handoff(c, task, "GRONK", output_sha, files, output, handoff_comment_id)
            self.collect_council_reviews(c, project, task["input_sha"])
            return
        if tt == "record_founder_decision":
            self._record_handoff(c, task, "JARVIS", output_sha, files, output, handoff_comment_id)
            self._apply_recorded_decision(c, project, task, output_sha)
            return
        next_stage = ROUTES[(tt, verdict)]
        if tt == "create_document":
            c.execute("UPDATE projects SET current_document_sha=? WHERE id=?", (output_sha, pid))
        if tt == "freeze_council_package" and verdict == "frozen":
            man = json.loads(output["files"]["council/packages/manifest.json"])
            c.execute("INSERT OR IGNORE INTO council_packages VALUES (?,?,?,?,?)",
                      (pid, task["cycle"], output_sha, dumps(man), iso()))
            c.execute("UPDATE projects SET current_package_sha=? WHERE id=?", (output_sha, pid))
            files = [f for f in files if f["path"] in set(man["includes"]) | {"council/packages/manifest.json"}]
            files = [{**f, "sha": output_sha} for f in files]
        if tt == "finalize_delivery":
            ver = json.loads(output["files"]["verification/verification-report.json"])
            disp = json.loads(output["files"]["reviews/jarvis/finding-dispositions.json"])["dispositions"]
            blockers = list(output.get("blockers") or []) + list(ver.get("unresolved_issues") or []) + \
                [d["finding_id"] for d in disp if d["disposition"] == "requires_founder_decision"]
            c.execute("INSERT OR REPLACE INTO deliveries VALUES (?,?,?,?,?,?,?,?,?)",
                      (pid, task["cycle"], output_sha, int(ver["development_complete"]), ver["status"],
                       dumps(ver), dumps(blockers), "delivery/final-report.md", iso()))
            if verdict == "submitted":
                c.execute("UPDATE projects SET current_delivery_sha=? WHERE id=?", (output_sha, pid))
                self._outbox(c, pid, "tag", {"name": L.delivery_tag(pid, task["cycle"]), "sha": output_sha},
                             f"tag:{L.delivery_tag(pid, task['cycle'])}")
        returns_to_kitt = (tt == "doc_review" and verdict == "changes_requested") or \
                          (tt == "freeze_council_package" and verdict == "feedback_not_addressed")
        if returns_to_kitt:
            if project["revision_loops"] >= self.s.max_revision_loops:
                reason = {"kind": "loop_limit", "resume_stage": next_stage.value, "channel": "kitt_session",
                          "input_sha": output_sha,
                          "files": files, "context": {"jarvis_feedback": output.get("summary", "")},
                          "reason": f"KITT↔JARVIS revision loop limit ({self.s.max_revision_loops}) reached."}
                c.execute("UPDATE projects SET blocked_reason=? WHERE id=?", (dumps(reason), pid))
                self._record_handoff(c, task, "FOUNDER", output_sha, files, output, handoff_comment_id)
                c.execute("UPDATE projects SET stage=? WHERE id=?", (Stage.FOUNDER_DECISION.value, pid))
                self.enqueue_stage(c, project, Stage.FOUNDER_DECISION, output_sha, files=files,
                                   context=reason, source_role=task["role"])
                record_audit_event(self.db, actor=actor, action="workflow.loop_limit", outcome="BLOCKED",
                                   project_id=pid, cycle=task["cycle"], version=output_sha)
                return
            c.execute("UPDATE projects SET revision_loops=revision_loops+1 WHERE id=?", (pid,))
        if next_stage == Stage.FOUNDER_DECISION:
            reason = {"kind": "development_decision", "resume_stage": Stage.JARVIS_DEVELOPMENT.value,
                      "channel": "jarvis_session", "input_sha": output_sha, "files": files, "context": {},
                      "reason": "JARVIS flagged findings that require G's decision (see "
                                "reviews/jarvis/finding-dispositions.json)."}
            c.execute("UPDATE projects SET blocked_reason=? WHERE id=?", (dumps(reason), pid))
            next_ctx = reason
        else:
            next_ctx = {"previous_summary": output.get("summary", ""), "previous_role": task["role"],
                        "previous_verdict": verdict}
            if next_stage == Stage.KITT_FINALIZE:
                next_ctx["jarvis_feedback_file"] = "reviews/jarvis/doc-review.md"
            if next_stage == Stage.JARVIS_FINALIZE_DELIVERY:
                next_ctx["kitt_review_files"] = ["reviews/kitt/delivery-review.md", "reviews/kitt/delivery-findings.json"]
            if "context" in m and "founder_requested_changes" in m["context"]:
                next_ctx["founder_requested_changes"] = m["context"]["founder_requested_changes"]
        dest = STAGE_TASK[next_stage][0]
        self._record_handoff(c, task, dest, output_sha, files, output, handoff_comment_id)
        self.enqueue_stage(c, project, next_stage, output_sha, files=files, context=next_ctx, source_role=task["role"])

    def _record_handoff(self, c, task, dest, output_sha, files, output, comment_id):
        nxt = f"{dest}: proceed with exact input {output_sha}"
        expected = EXPECTED_OUTPUTS.get(task["task_type"], [])
        c.execute("INSERT INTO handoffs(project_id, task_id, cycle, revision, source_role, dest_role, task_type,"
                  " input_sha, output_sha, manifest, expected_outputs, next_action, comment_id, created_at)"
                  " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                  (task["project_id"], task["id"], task["cycle"], task["assignment_rev"], task["role"], dest,
                   task["task_type"], task["input_sha"], output_sha, dumps(files), dumps(expected), nxt,
                   comment_id, iso()))
        project = c.execute("SELECT * FROM projects WHERE id=?", (task["project_id"],)).fetchone()
        body = (f"🔀 **Handoff** `{task['project_id']}` · task `{task['id']}` · cycle {task['cycle']} · "
                f"revision {task['assignment_rev']}\n\n- {task['role']} → {dest} · task type `{task['task_type']}` · "
                f"verdict `{output['verdict']}`\n- Input commit `{task['input_sha']}` → output commit "
                f"[`{output_sha}`]({GITHUB_URL}/commit/{output_sha})\n- Manifest: "
                + ", ".join(f"`{f['path']}@{f['sha'][:12]}`" for f in files)
                + "\n- Expected outputs: " + (", ".join(f"`{p}`" for p in expected) or "—")
                + f"\n- Next action: {nxt}\n\n{output.get('summary', '')}")
        self.comment(c, project, body, f"handoff:{task['id']}")

    def _publish_decision_reference(self, task, project) -> str:
        """JARVIS writes the validated decision reference (decisions/<ID>/v<N>.json) and hands it to KITT."""
        import hashlib
        ctxd = json.loads(task["manifest"])["context"]
        dec = self.db.one("SELECT * FROM founder_decisions WHERE decision_id=?", ctxd["decision_id"])
        if not dec or dec["outcome"] != "accepted" or dec["channel"] != "jarvis_session":
            raise InvalidInput("no accepted JARVIS-session founder decision for this reference")
        pid, cyc = project["id"], task["cycle"]
        verbatim = ctxd.get("founder_statement", "")
        ref = {
            "project_id": pid, "version": str(cyc), "cycle": str(cyc),
            "delivery_tag": L.delivery_tag(pid, cyc), "delivery_sha": ctxd["delivery_sha"],
            "decision": "APPROVE_AND_CLOSE" if ctxd["decision_type"] == "delivery_approve_close" else "REQUEST_CHANGES",
            "g_verbatim": verbatim, "g_verbatim_sha256": hashlib.sha256(verbatim.encode()).hexdigest(),
            "requested_changes": ctxd.get("changes", []), "route": ctxd.get("route"),
            "source": f"JARVIS session (GitHub OAuth app {dec['oauth_client_id']})",
            "session_ref": f"founder_decision:{dec['decision_id']}",
            "github_identity": {"login": dec["github_login"], "id": dec["github_user_id"],
                                "token_fingerprint_prefix": dec["token_fingerprint"][:12]},
            "decided_at_utc": dec["received_at"][:19] + "Z",
            "validated_by": "automation: JARVIS session verifier (GitHub OAuth app + founder identity)",
            "checks": {"source": True, "explicit": True, "exact_version": True, "current": True,
                       "preconditions": True},
        }
        path = L.decision_ref_path(pid, cyc)
        sha = task["published_sha"] or self.gh.commit_files(
            project["branch"], {path: json.dumps(ref, indent=2) + "\n"},
            f"[coint] {pid} v{cyc} founder decision reference {dec['decision_id']}")
        if not task["published_sha"]:
            Q.save_published_sha(self.db, task["id"], self.worker_id, sha)
        with self.db.tx() as c:
            t = Q.get_task(self.db, task["id"])
            self._assert_current(t, self.project(pid))
            cur = c.execute("UPDATE tasks SET state='COMPLETED', output=?, lease_owner=NULL, updated_at=?"
                            " WHERE id=? AND state='RUNNING' AND lease_owner=?",
                            (dumps({"verdict": "published", "_published_files": [], "decision_reference": path}),
                             iso(), task["id"], self.worker_id))
            if cur.rowcount != 1:
                raise StaleAssignment("task no longer owned")
            files = json.loads(task["manifest"])["files"] + [
                {"path": "decision/reference.json", "sha": sha, "repo_path": path}]
            context = {**ctxd, "decision_reference": path, "decision_reference_sha": sha}
            self.comment(c, self.project(pid), f"📌 JARVIS published the validated decision reference "
                                               f"[`{path}`]({GITHUB_URL}/blob/{sha}/{path}) (`{sha}`) and passed it "
                                               "to KITT for GitHub recording.", f"decref:{task['id']}")
            self.enqueue_stage(c, self.project(pid), Stage.FOUNDER_DECISION_RECORDING, sha, files=files,
                               context=context, source_role="JARVIS")
        return "completed"

    # ------------------------------------------------------------------ council
    def dispatch_council(self, c, project, dispatch_task):
        """Four independently tracked review tasks, identical frozen package SHA."""
        pkg = project["current_package_sha"]
        if dispatch_task["input_sha"] != pkg:
            raise StaleAssignment("package replaced")
        m = json.loads(dispatch_task["manifest"])
        for role in COUNCIL_ROLES:
            self.enqueue_stage(c, project, Stage.COUNCIL_REVIEW, pkg, files=m["files"],
                               context={"package_sha": pkg, "brief": json.loads(project["brief_json"])},
                               source_role="GRONK", role_override=role)
        c.execute("UPDATE tasks SET state='COMPLETED', lease_owner=NULL, published_sha=?, output=?, updated_at=?"
                  " WHERE id=?", (pkg, dumps({"verdict": "dispatched", "reviewers": list(COUNCIL_ROLES)}), iso(),
                                 dispatch_task["id"]))
        self.comment(c, project, f"🏛️ GRONK distributed frozen package `{pkg}` to {', '.join(COUNCIL_ROLES)} "
                                 f"(four separately tracked reviews; timeout {self.s.council_timeout_minutes} min).",
                     f"council:{project['id']}:{pkg}")

    def collect_council_reviews(self, c, project, package_sha: str) -> bool:
        """Require four valid reviews for the same frozen package; then GRONK drafts."""
        rows = c.execute("SELECT * FROM tasks WHERE project_id=? AND cycle=? AND task_type='council_review'"
                         " AND input_sha=? AND assignment_rev=? AND state='COMPLETED'",
                         (project["id"], project["current_cycle"], package_sha, project["assignment_rev"])).fetchall()
        by_role = {r["role"]: r for r in rows}
        if set(by_role) != set(COUNCIL_ROLES) or package_sha != project["current_package_sha"]:
            return False
        dispatch = c.execute("SELECT manifest FROM tasks WHERE project_id=? AND cycle=? AND task_type='council_dispatch'"
                             " AND input_sha=?", (project["id"], project["current_cycle"], package_sha)).fetchone()
        files = json.loads(dispatch["manifest"])["files"]
        for role in COUNCIL_ROLES:
            files = self._merge_files(files, [f"council/reviews/{role}.md"], by_role[role]["published_sha"],
                                      project["id"], project["current_cycle"])
        latest = max(rows, key=lambda r: r["updated_at"])["published_sha"]
        self.enqueue_stage(c, project, Stage.GRONK_DRAFT, latest, files=files,
                           context={"package_sha": package_sha,
                                    "review_commits": {r: by_role[r]["published_sha"] for r in COUNCIL_ROLES}},
                           source_role="COUNCIL")
        return True

    # ------------------------------------------------------- approval / closure
    def validate_founder_approval(self, c, project, cycle: int, delivery_sha: str, actor: str,
                                  stage: Stage = Stage.FOUNDER_FINAL_REVIEW):
        if not is_founder(self.s, actor):
            raise CommandRejected("Only the configured founder may approve.")
        self._require_stage(project, stage, cycle)
        if delivery_sha != project["current_delivery_sha"]:
            raise CommandRejected(f"Stale delivery SHA; the current delivery is {project['current_delivery_sha']}.")
        d = c.execute("SELECT * FROM deliveries WHERE project_id=? AND cycle=? AND delivery_sha=?",
                      (project["id"], cycle, delivery_sha)).fetchone()
        if not d:
            raise CommandRejected("No delivery record for that version.")
        if not d["development_complete"]:
            raise CommandRejected("Development is not complete for this delivery.")
        if d["verification_status"] != "passed":
            raise CommandRejected(f"Verification status is `{d['verification_status']}`, not `passed`.")
        if any(ch.get("result") == "failed" for ch in json.loads(d["verification"]).get("checks", [])):
            raise CommandRejected("Verification contains failed checks.")
        blockers = json.loads(d["unresolved_blockers"])
        if blockers:
            raise CommandRejected(f"Unresolved blockers: {blockers}")
        if self.s.require_checks_pass:
            bad = c.execute("SELECT name, status, conclusion FROM check_results WHERE sha=? AND (status<>'completed'"
                            " OR conclusion NOT IN ('success','neutral','skipped'))", (delivery_sha,)).fetchall()
            if bad:
                raise CommandRejected("GitHub checks not passing on delivery: "
                                      + ", ".join(f"{b['name']}={b['conclusion'] or b['status']}" for b in bad))
        if not self.gh.file_exists(L.repo_path(project["id"], cycle, d["final_report_path"]), delivery_sha):
            raise CommandRejected("Final report artifact missing at the delivery SHA.")
        return d

    def close_project(self, c, project, approval_id: int, delivery, record_sha: str | None = None):
        cycle = project["current_cycle"]
        c.execute("INSERT INTO closures(project_id, cycle, approval_id, delivery_sha, closed_at) VALUES (?,?,?,?,?)",
                  (project["id"], cycle, approval_id, delivery["delivery_sha"], iso()))
        c.execute("UPDATE projects SET status='CLOSED', stage='CLOSED', updated_at=? WHERE id=?", (iso(), project["id"]))
        self._complete_gate(c, project)
        Q.supersede_open_tasks(self.db, project["id"], actor="founder-close")
        key = f"final:{project['id']}|{cycle}|{approval_id}"
        c.execute("INSERT OR IGNORE INTO email_outbox(email_key, kind, to_addr, delivery_sha, project_id, cycle,"
                  " approval_id, state, rfc822_message_id, next_attempt_at, created_at, updated_at)"
                  " VALUES (?, 'final_report', ?,?,?,?,?, 'PENDING', ?,?,?,?)",
                  (key, FINAL_REPORT_TO, delivery["delivery_sha"], project["id"], cycle, approval_id,
                   f"<coint-{project['id']}-v{cycle}-a{approval_id}@co-intelligence.resystem.org>", iso(), iso(), iso()))
        self.comment(c, project, f"🏁 KITT recorded G's APPROVE AND CLOSE for delivery `{delivery['delivery_sha']}` "
                                 f"(Version {cycle})" + (f", record `{record_sha}`" if record_sha else "")
                                 + ". Approval validated from the JARVIS session; closure recorded; closing this "
                                   "tracking issue. JARVIS will send the final report after closure validation.")
        approval = c.execute("SELECT * FROM approvals WHERE id=?", (approval_id,)).fetchone()
        closure_doc = {
            "project_id": project["id"], "title": project["title"], "version": cycle, "cycle": cycle,
            "delivery_tag": L.delivery_tag(project["id"], cycle), "delivery_sha": delivery["delivery_sha"],
            "decision_reference": L.decision_ref_path(project["id"], cycle),
            "founder_decision_id": approval["attestation_id"], "approved_by": approval["actor"],
            "approval_channel": approval["channel"], "kitt_record_sha": record_sha,
            "kitt_record": L.repo_path(project["id"], cycle, f"approvals/founder-decision-{approval['attestation_id']}.md"),
            "closed_at_utc": iso()[:19] + "Z", "final_report_email": {"state": "PENDING"},
        }
        self._outbox(c, project["id"], "commit", {
            "branch": project["branch"], "message": f"[coint] {project['id']} v{cycle} closure record",
            "files": {L.closure_path(project["id"]): json.dumps(closure_doc, indent=2) + "\n"}},
            f"closurejson:{project['id']}:{cycle}")
        self._outbox(c, project["id"], "tag", {"name": L.closed_tag(project["id"], cycle),
                                               "sha": record_sha or delivery["delivery_sha"]},
                     f"tag:{L.closed_tag(project['id'], cycle)}")
        self._outbox(c, project["id"], "close_issue", {"issue": project["issue_number"], "cycle": cycle},
                     f"close:{project['id']}:{cycle}")
        record_audit_event(self.db, actor=self.s.founder_login, action="project.close", outcome="CLOSED",
                           project_id=project["id"], cycle=cycle, version=delivery["delivery_sha"],
                           detail={"approval_id": approval_id})

    def _latest_task(self, c, pid, cycle, task_type):
        return c.execute("SELECT * FROM tasks WHERE project_id=? AND cycle=? AND task_type=? AND state='COMPLETED'"
                         " ORDER BY updated_at DESC LIMIT 1", (pid, cycle, task_type)).fetchone()


def _json(files: dict, path: str) -> dict:
    try:
        v = json.loads(files[path])
    except (KeyError, ValueError) as e:
        raise InvalidInput(f"{path} is not valid JSON: {e}")
    if not isinstance(v, dict):
        raise InvalidInput(f"{path} must be a JSON object")
    return v
