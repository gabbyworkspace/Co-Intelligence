"""Workflow stages, task states, task types, and the routing table.

Execution state (TaskState) and workflow stage (Stage) are tracked separately:
a project has exactly one current Stage; each task has its own TaskState.
"""
from __future__ import annotations

from enum import Enum


class TaskState(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    WAITING_FOUNDER = "WAITING_FOUNDER"
    BLOCKED = "BLOCKED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    SUPERSEDED = "SUPERSEDED"


TERMINAL_STATES = {TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED, TaskState.SUPERSEDED}


class Stage(str, Enum):
    KITT_DRAFT = "KITT_DRAFT"                          # 2
    FOUNDER_INITIAL_REVIEW = "FOUNDER_INITIAL_REVIEW"  # 3
    KITT_APPLY_DECISIONS = "KITT_APPLY_DECISIONS"      # 4
    JARVIS_DOC_REVIEW = "JARVIS_DOC_REVIEW"            # 5
    KITT_FINALIZE = "KITT_FINALIZE"                    # 6
    JARVIS_COUNCIL_PACKAGE = "JARVIS_COUNCIL_PACKAGE"  # 7
    COUNCIL_REVIEW = "COUNCIL_REVIEW"                  # 8
    GRONK_DRAFT = "GRONK_DRAFT"                        # 9-10
    JARVIS_DEVELOPMENT = "JARVIS_DEVELOPMENT"          # 10/11 develop + verify
    KITT_DELIVERY_REVIEW = "KITT_DELIVERY_REVIEW"      # step 10: KITT reviews delivery
    JARVIS_FINALIZE_DELIVERY = "JARVIS_FINALIZE_DELIVERY"  # step 10: JARVIS addresses KITT findings
    FOUNDER_FINAL_REVIEW = "FOUNDER_FINAL_REVIEW"      # step 11: G <-> JARVIS session
    FOUNDER_DECISION_REFERENCE = "FOUNDER_DECISION_REFERENCE"  # JARVIS publishes decisions/<ID>/v<N>.json
    FOUNDER_DECISION_RECORDING = "FOUNDER_DECISION_RECORDING"  # KITT records G's decision on GitHub
    FOUNDER_DECISION = "FOUNDER_DECISION"              # loop limit / blockers escalation
    CLOSED = "CLOSED"                                  # 14


class ProjectStatus(str, Enum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    CLOSED = "CLOSED"


# stage -> (role, task_type)
STAGE_TASK = {
    Stage.KITT_DRAFT: ("KITT", "create_document"),
    Stage.FOUNDER_INITIAL_REVIEW: ("FOUNDER", "founder_initial_review"),
    Stage.KITT_APPLY_DECISIONS: ("KITT", "apply_decisions"),
    Stage.JARVIS_DOC_REVIEW: ("JARVIS", "doc_review"),
    Stage.KITT_FINALIZE: ("KITT", "finalize_documents"),
    Stage.JARVIS_COUNCIL_PACKAGE: ("JARVIS", "freeze_council_package"),
    Stage.COUNCIL_REVIEW: ("GRONK", "council_dispatch"),
    Stage.GRONK_DRAFT: ("GRONK", "council_draft"),
    Stage.JARVIS_DEVELOPMENT: ("JARVIS", "develop_and_deliver"),
    Stage.KITT_DELIVERY_REVIEW: ("KITT", "delivery_review"),
    Stage.JARVIS_FINALIZE_DELIVERY: ("JARVIS", "finalize_delivery"),
    Stage.FOUNDER_FINAL_REVIEW: ("FOUNDER", "founder_final_review"),
    Stage.FOUNDER_DECISION_REFERENCE: ("JARVIS", "publish_decision_reference"),
    Stage.FOUNDER_DECISION_RECORDING: ("KITT", "record_founder_decision"),
    Stage.FOUNDER_DECISION: ("FOUNDER", "founder_decision"),
}

FOUNDER_STAGES = {Stage.FOUNDER_INITIAL_REVIEW, Stage.FOUNDER_FINAL_REVIEW, Stage.FOUNDER_DECISION}

# (task_type, verdict) -> next stage. Model output can only pick a verdict from
# this table; it can never name an arbitrary next role or stage.
ROUTES = {
    ("create_document", "done"): Stage.FOUNDER_INITIAL_REVIEW,
    ("apply_decisions", "done"): Stage.JARVIS_DOC_REVIEW,
    ("doc_review", "changes_requested"): Stage.KITT_FINALIZE,
    ("doc_review", "accepted"): Stage.KITT_FINALIZE,
    ("finalize_documents", "done"): Stage.JARVIS_COUNCIL_PACKAGE,
    ("freeze_council_package", "frozen"): Stage.COUNCIL_REVIEW,
    ("freeze_council_package", "feedback_not_addressed"): Stage.KITT_FINALIZE,
    ("council_draft", "done"): Stage.JARVIS_DEVELOPMENT,
    ("develop_and_deliver", "submitted"): Stage.KITT_DELIVERY_REVIEW,
    ("develop_and_deliver", "requires_founder_decision"): Stage.FOUNDER_DECISION,
    ("delivery_review", "accepted"): Stage.JARVIS_FINALIZE_DELIVERY,
    ("delivery_review", "changes_requested"): Stage.JARVIS_FINALIZE_DELIVERY,
    ("finalize_delivery", "submitted"): Stage.FOUNDER_FINAL_REVIEW,
    ("finalize_delivery", "requires_founder_decision"): Stage.FOUNDER_DECISION,
}

# Allowed (source_role, task_type) -> destination roles for explicit /handoff.
HANDOFF_ALLOWED = {
    ("KITT", "create_document"): {"FOUNDER"},
    ("KITT", "apply_decisions"): {"JARVIS"},
    ("JARVIS", "doc_review"): {"KITT"},
    ("KITT", "finalize_documents"): {"JARVIS"},
    ("JARVIS", "freeze_council_package"): {"GRONK", "KITT"},
    ("COUNCIL_1", "council_review"): {"GRONK"},
    ("COUNCIL_2", "council_review"): {"GRONK"},
    ("COUNCIL_3", "council_review"): {"GRONK"},
    ("COUNCIL_4", "council_review"): {"GRONK"},
    ("GRONK", "council_draft"): {"JARVIS"},
    ("JARVIS", "develop_and_deliver"): {"KITT"},
    ("KITT", "delivery_review"): {"JARVIS"},
    ("JARVIS", "finalize_delivery"): {"FOUNDER"},
    ("KITT", "record_founder_decision"): {"JARVIS"},
}

# Expected outputs per task type (logical paths; see coint/layout.py for repo locations).
EXPECTED_OUTPUTS = {
    "create_document": ["brief/brief.json", "documents/project-document.md"],
    "apply_decisions": ["documents/project-document.md", "approvals/initial-decisions.md"],
    "doc_review": ["reviews/jarvis/doc-review.md"],
    "finalize_documents": ["documents/project-document.md", "documents/feedback-response.md"],
    "freeze_council_package": ["council/packages/manifest.json"],
    "council_review": [],  # council/reviews/<role>.md, checked specially
    "council_draft": [
        "council/drafts/proposed-final-draft.md",
        "council/drafts/findings-index.json",
        "council/drafts/conflict-decision-log.md",
        "council/drafts/unresolved-blockers.md",
    ],
    "develop_and_deliver": [
        "reviews/jarvis/finding-dispositions.json",
        "documents/implementation-document.md",
        "verification/verification-report.json",
        "delivery/delivery.md",
        "delivery/final-report.md",
    ],
    "delivery_review": ["reviews/kitt/delivery-review.md", "reviews/kitt/delivery-findings.json"],
    "finalize_delivery": [
        "reviews/jarvis/kitt-findings-response.json",
        "reviews/jarvis/finding-dispositions.json",
        "documents/implementation-document.md",
        "verification/verification-report.json",
        "delivery/delivery.md",
        "delivery/final-report.md",
    ],
    "record_founder_decision": [],  # approvals/founder-decision-<decision_id>.md, checked specially
}

VERDICTS = {}
for (tt, verdict) in ROUTES:
    VERDICTS.setdefault(tt, set()).add(verdict)
VERDICTS["council_review"] = {"done"}
VERDICTS["record_founder_decision"] = {"recorded"}

PROJECT_DIRS = [
    "brief", "documents", "assets", "reviews/jarvis", "reviews/kitt", "council/packages",
    "council/reviews", "council/drafts", "development", "verification",
    "delivery", "approvals",
]
