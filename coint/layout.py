"""Repository layout — WORKFLOW.md v2.0.

Agents and the engine use stable *logical* paths (see prompts/OUTPUT_SCHEMA.md).
This module maps them to the repository layout the team documents in README.md:

    <PROJECT_ID>/                     brief, project document, assets, initial decisions, JARVIS doc review
    council/<PROJECT_ID>/             MANIFEST.json (frozen SHA), reviews/, drafts/ (GRONK return)
    deliveries/<PROJECT_ID>/v<N>/     delivery, VERIFICATION.md, FINDINGS.md, KITT_REVIEW.md, development/
    decisions/<PROJECT_ID>/v<N>.json  validated founder decision reference (written by JARVIS/engine)
    decisions/<PROJECT_ID>/v<N>.KITT_RECORD.md   KITT's GitHub record of that decision
    closure/<PROJECT_ID>/CLOSURE.json
    ledger/emails.jsonl               every email send result

Tags: <PROJECT_ID>-v<N> (final delivery version), <PROJECT_ID>-v<N>-closed.
"""
from __future__ import annotations

import json
import re

# Delivery-phase logical files -> names inside deliveries/<ID>/v<N>/
DELIVERY_NAMES = {
    "delivery/delivery.md": "DELIVERY.md",
    "delivery/final-report.md": "FINAL-REPORT.md",
    "verification/verification-report.json": "VERIFICATION.json",
    "reviews/kitt/delivery-review.md": "KITT_REVIEW.md",
    "reviews/kitt/delivery-findings.json": "KITT_FINDINGS.json",
    "reviews/jarvis/kitt-findings-response.json": "FINDINGS.json",
    "reviews/jarvis/finding-dispositions.json": "COUNCIL-DISPOSITIONS.json",
    "documents/implementation-document.md": "IMPLEMENTATION.md",
}
_RECORD_RE = re.compile(r"^approvals/founder-decision-([A-Za-z0-9-]+)\.md$")


def repo_path(pid: str, cycle: int, rel: str) -> str:
    if rel in DELIVERY_NAMES:
        return f"deliveries/{pid}/v{cycle}/{DELIVERY_NAMES[rel]}"
    if rel.startswith("development/"):
        return f"deliveries/{pid}/v{cycle}/{rel}"
    if rel == "council/packages/manifest.json":
        return f"council/{pid}/MANIFEST.json"
    if rel.startswith("council/reviews/") or rel.startswith("council/drafts/"):
        return f"council/{pid}/" + rel[len("council/"):]
    if _RECORD_RE.match(rel):
        return f"decisions/{pid}/v{cycle}.KITT_RECORD.md"
    return f"{pid}/{rel}"  # brief/, documents/, assets/, approvals/, reviews/jarvis/doc-review.md


def decision_ref_path(pid: str, cycle: int) -> str:
    return f"decisions/{pid}/v{cycle}.json"


def closure_path(pid: str) -> str:
    return f"closure/{pid}/CLOSURE.json"


LEDGER_PATH = "ledger/emails.jsonl"


def delivery_tag(pid: str, cycle: int) -> str:
    return f"{pid}-v{cycle}"


def closed_tag(pid: str, cycle: int) -> str:
    return f"{pid}-v{cycle}-closed"


def file_repo_path(pid: str, cycle: int, entry: dict) -> str:
    """A manifest entry may pin its repo path (files published in an earlier cycle)."""
    return entry.get("repo_path") or repo_path(pid, cycle, entry["path"])


def derived_files(pid: str, cycle: int, rel: str, content: str) -> dict[str, str]:
    """Human-readable companions required by WORKFLOW.md (VERIFICATION.md, FINDINGS.md)."""
    base = f"deliveries/{pid}/v{cycle}/"
    try:
        obj = json.loads(content)
    except ValueError:
        return {}
    if rel == "verification/verification-report.json":
        lines = [f"# Verification — {pid} v{cycle}", "",
                 f"Status: **{obj.get('status')}** · development complete: {obj.get('development_complete')}", "",
                 "| Check | Criterion | Result | Evidence |", "|---|---|---|---|"]
        lines += [f"| {c.get('name', '')} | {c.get('acceptance_criterion', '')} | {c.get('result', '')} | "
                  f"{str(c.get('evidence', '')).replace('|', '/')} |" for c in obj.get("checks", [])]
        lines += ["", "## Limitations"] + [f"- {x}" for x in obj.get("limitations", []) or ["none recorded"]]
        lines += ["", "## Unresolved issues"] + [f"- {x}" for x in obj.get("unresolved_issues", []) or ["none"]]
        return {base + "VERIFICATION.md": "\n".join(lines) + "\n"}
    if rel == "reviews/jarvis/kitt-findings-response.json":
        lines = [f"# Findings — {pid} v{cycle}", "", "JARVIS disposition of KITT's delivery review findings.", "",
                 "| Finding | Action | Details |", "|---|---|---|"]
        lines += [f"| {r.get('finding_id', '')} | {r.get('action', '')} | {str(r.get('details', '')).replace('|', '/')} |"
                  for r in obj.get("responses", [])]
        return {base + "FINDINGS.md": "\n".join(lines) + "\n"}
    return {}
