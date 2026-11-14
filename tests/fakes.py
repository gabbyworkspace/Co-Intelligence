"""In-memory fakes for GitHub, agents and Gmail (tests only)."""
from __future__ import annotations

import hashlib
import json

from coint.adapters.base import AgentAdapter
from coint.config import AdapterConfig, ROLES, Settings
from coint.errors import InvalidInput
from coint.gmail import DefinitePreSendFailure, UncertainSendOutcome

FOUNDER = "g-founder"


def make_settings(db_path: str, **kw) -> Settings:
    adapters = {r: AdapterConfig(role=r, kind="fake", github_login=f"{r.lower()}-bot") for r in ROLES}
    s = Settings(founder_login=FOUNDER, db_path=db_path, webhook_secret="s3cret", github_app_id=None,
                 github_app_private_key=None, github_installation_id=None, github_repo_id=None,
                 app_bot_login="co-intel[bot]", gmail_client_id=None, gmail_client_secret=None,
                 gmail_refresh_token=None, adapters=adapters, retry_delays_minutes=(0, 0, 0),
                 kitt_oauth_client_id="kitt-app", kitt_oauth_client_secret="x",
                 jarvis_oauth_client_id="jarvis-app", jarvis_oauth_client_secret="y")
    for k, v in kw.items():
        setattr(s, k, v)
    return s


class FakeGitHub:
    def __init__(self):
        self.commits = {}
        self.branches = {}
        root = self._new_sha("root")
        self.commits[root] = {"README.md": "# Co-Intelligence"}
        self.branches["main"] = root
        self.comments = []        # (issue, body)
        self.closed = []
        self.repo_comments = []   # what the REST scan returns
        self.n = 0

    @staticmethod
    def _new_sha(seed: str) -> str:
        return hashlib.sha1(seed.encode()).hexdigest()

    def get_commit(self, sha):
        if sha not in self.commits:
            raise InvalidInput(f"no commit {sha}")
        return {"sha": sha}

    def get_file(self, path, ref):
        if ref not in self.commits:
            raise InvalidInput(f"no commit {ref}")
        return self.commits[ref].get(path)

    def file_exists(self, path, ref):
        return self.get_file(path, ref) is not None

    def branch_head(self, branch):
        return self.branches.get(branch)

    def default_branch_head(self):
        return self.branches["main"]

    def commit_files(self, branch, files, message):
        self.n += 1
        head = self.branches.get(branch) or self.branches["main"]
        sha = self._new_sha(f"{head}{self.n}{json.dumps(files, sort_keys=True)}")
        self.commits[sha] = {**self.commits[head], **files}
        self.branches[branch] = sha
        return sha

    def create_comment(self, issue, body):
        self.comments.append((issue, body))
        return {"id": len(self.comments), "html_url": f"https://github.com/x/issues/{issue}#c{len(self.comments)}"}

    def create_issue(self, title, body):
        self.issues = getattr(self, "issues", [])
        self.issues.append((title, body))
        return 100 + len(self.issues)

    def create_tag(self, name, sha):
        self.tags = getattr(self, "tags", {})
        if name in self.tags and self.tags[name] != sha:
            from coint.errors import PermissionDenied
            raise PermissionDenied("tag exists elsewhere")
        self.tags[name] = sha

    def close_issue(self, issue):
        self.closed.append(issue)

    def add_labels(self, issue, labels):
        pass

    def list_repo_comments(self, since):
        return list(self.repo_comments)


DELIVERY_FILES = {
    "reviews/jarvis/finding-dispositions.json": json.dumps(
        {"dispositions": [{"finding_id": "F-001", "disposition": "accepted"}]}),
    "documents/implementation-document.md": "impl",
    "verification/verification-report.json": json.dumps(
        {"development_complete": True, "status": "passed",
         "checks": [{"name": "AC1", "result": "passed", "evidence": "pytest ok"}], "limitations": ["demo only"]}),
    "development/app.py": "print('hi')",
    "delivery/delivery.md": "delivered",
    "delivery/final-report.md": "Summary. Handover: run app.py",
}


def default_output(role: str, task_type: str, meta: dict, inputs: dict, context: dict | None = None) -> dict:
    sha = meta["input_sha"]
    context = context or {}
    files = {}
    verdict = "done"
    if task_type == "create_document":
        files = {"brief/brief.json": json.dumps({"title": "T"}), "documents/project-document.md": "# Doc"}
    elif task_type == "apply_decisions":
        files = {"documents/project-document.md": "# Doc v2", "approvals/initial-decisions.md": "ok"}
    elif task_type == "doc_review":
        verdict = "changes_requested"
        files = {"reviews/jarvis/doc-review.md": "1. tighten AC"}
    elif task_type == "finalize_documents":
        files = {"documents/project-document.md": "# Doc v3", "documents/feedback-response.md": "done"}
    elif task_type == "freeze_council_package":
        verdict = "frozen"
        files = {"council/packages/manifest.json": json.dumps({
            "includes": ["documents/project-document.md"], "approved_requirements": ["R1"],
            "open_questions": [], "acceptance_criteria": ["AC1"]})}
    elif task_type == "council_review":
        files = {f"council/reviews/{role}.md": f"Package {sha}\nFinding: x"}
    elif task_type == "council_draft":
        files = {"council/drafts/proposed-final-draft.md": "draft",
                 "council/drafts/findings-index.json": json.dumps({"findings": [{"id": "F-001"}]}),
                 "council/drafts/conflict-decision-log.md": "none",
                 "council/drafts/unresolved-blockers.md": "none"}
    elif task_type == "develop_and_deliver":
        verdict = "submitted"
        files = dict(DELIVERY_FILES)
    elif task_type == "delivery_review":
        verdict = "changes_requested"
        files = {"reviews/kitt/delivery-review.md": "K-1: clarify handover",
                 "reviews/kitt/delivery-findings.json": json.dumps({"findings": [{"id": "K-1", "summary": "handover"}]})}
    elif task_type == "finalize_delivery":
        verdict = "submitted"
        files = dict(DELIVERY_FILES, **{
            "reviews/jarvis/kitt-findings-response.json": json.dumps(
                {"responses": [{"finding_id": "K-1", "action": "handover clarified"}]}),
            "delivery/final-report.md": "Summary. Handover (clarified): run app.py"})
    elif task_type == "record_founder_decision":
        verdict = "recorded"
        files = {context["record_file"]: f"Decision {context['decision_id']} {context['decision_type']} "
                                         f"cycle {context['cycle']} version {context['delivery_sha']}"}
    return {"verdict": verdict, "files": files, "summary": f"{role} {task_type}", "input_sha": sha,
            "blockers": [], "limitations": [], "next_action": "next"}


class FakeAdapter(AgentAdapter):
    def __init__(self, role, script=None, external=False):
        super().__init__(AdapterConfig(role=role, kind="fake", github_login=f"{role.lower()}-bot"))
        self.script = script        # callable(role, task_type, meta, inputs) -> dict | raises
        self.external = external
        self.calls = []

    def run(self, req):
        meta = json.loads(req.user.split("TASK:\n", 1)[1].split("\n\nEcho", 1)[0])
        inputs = {}
        for chunk in req.user.split('<repository_data path="')[1:]:
            path, rest = chunk.split('">\n', 1)
            inputs[path] = rest.rsplit("\n</repository_data>", 1)[0]
        ctx_raw = req.user.split('<repository_data kind="task_context">\n', 1)[1].split("\n</repository_data>", 1)[0]
        context = json.loads(ctx_raw)
        self.calls.append((meta["task_type"], meta["input_sha"], sorted(inputs)))
        if self.script:
            return self.script(self.cfg.role, meta["task_type"], meta, inputs)
        return default_output(self.cfg.role, meta["task_type"], meta, inputs, context)


class FakeGmail:
    def __init__(self, mode="ok"):
        self.mode = mode          # ok | uncertain_but_sent | uncertain_not_sent | presend_fail
        self.inbox = {}
        self.mailbox = {}         # message-id -> gmail id
        self.sends = []

    def authorized_address(self):
        return "jarvis.resystem@gmail.com"

    # inbox for founder email replies: id -> {"headers": [...], "body": str}
    inbox: dict = {}

    def list_message_ids(self, query):
        return list(self.inbox)

    def get_full_message(self, mid):
        return {"id": mid, "thread_id": "t", **self.inbox[mid]}

    def find_sent_by_message_id(self, mid):
        gid = self.mailbox.get(mid)
        return {"id": gid} if gid else None

    def send_raw(self, raw: bytes):
        import email
        import email.policy
        msg = email.message_from_bytes(raw, policy=email.policy.default)
        self.sends.append(msg)
        if self.mode == "presend_fail":
            raise DefinitePreSendFailure("connection refused")
        gid = f"gm-{len(self.sends)}"
        if self.mode == "uncertain_not_sent":
            raise UncertainSendOutcome("timeout")
        self.mailbox[msg["Message-ID"]] = gid
        if self.mode == "uncertain_but_sent":
            raise UncertainSendOutcome("timeout after send")
        return {"id": gid}
