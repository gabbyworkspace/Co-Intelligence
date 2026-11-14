"""Issue-comment command parser.

Only a top-level command is recognised: the FIRST non-blank line of the comment
must be the command. Text in block quotes, code fences, later lines, or inside
documents is never parsed as a command. The structured payload, when needed,
is the first top-level ```json fenced block that follows the command line.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from .config import ROLES

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
PROJECT_ID_RE = re.compile(r"^[A-Z][A-Z0-9-]{2,31}$")

COMMAND_PREFIXES = ("/project", "/initial", "/handoff", "/delivery")

BRIEF_REQUIRED = ("title", "objective", "scope", "deliverables", "acceptance_criteria", "constraints")
HANDOFF_REQUIRED = ("project_id", "task_id", "revision", "source_role", "files",
                    "expected_outputs", "next_action")


class ParseError(Exception):
    """Command is recognisable but incomplete/invalid; message is user-facing."""


@dataclass
class Command:
    name: str                      # e.g. "project start", "handoff"
    args: dict = field(default_factory=dict)
    payload: dict = field(default_factory=dict)


def _first_line(body: str) -> tuple[str | None, int]:
    lines = body.replace("\r\n", "\n").split("\n")
    for i, line in enumerate(lines):
        if line.strip():
            return line, i
    return None, -1


def _payload(body: str, start: int) -> dict | None:
    lines = body.replace("\r\n", "\n").split("\n")[start + 1:]
    i = 0
    while i < len(lines):
        if re.match(r"^```\s*json\s*$", lines[i]):  # must be top-level (column 0, not quoted)
            j = i + 1
            buf = []
            while j < len(lines) and not re.match(r"^```\s*$", lines[j]):
                buf.append(lines[j])
                j += 1
            if j >= len(lines):
                raise ParseError("Unterminated ```json block.")
            try:
                data = json.loads("\n".join(buf))
            except ValueError as e:
                raise ParseError(f"The ```json block is not valid JSON: {e}")
            if not isinstance(data, dict):
                raise ParseError("The ```json block must be a JSON object.")
            return data
        i += 1
    return None


def _cycle(tok: str) -> int:
    if not tok.isdigit() or int(tok) < 1:
        raise ParseError(f"Cycle must be a positive integer, got {tok!r}.")
    return int(tok)


def _sha(tok: str) -> str:
    if not SHA_RE.match(tok):
        raise ParseError(f"SHA must be the full 40-character lowercase commit SHA, got {tok!r}.")
    return tok


def _nonempty_list(payload: dict, key: str) -> list:
    v = payload.get(key)
    if not isinstance(v, list) or not v or not all(isinstance(x, str) and x.strip() for x in v):
        raise ParseError(f"Field `{key}` must be a non-empty list of strings.")
    return v


def validate_brief(p) -> dict:
    """Confirmed initial brief (shared by the KITT session channel and parser)."""
    if not isinstance(p, dict):
        raise ParseError("A confirmed brief object is required with fields: " + ", ".join(BRIEF_REQUIRED)
                         + ", confirmed.")
    missing = [k for k in BRIEF_REQUIRED if not p.get(k)]
    if missing:
        raise ParseError("Brief is incomplete. Missing: " + ", ".join(missing) + ".")
    if p.get("confirmed") is not True:
        raise ParseError("The brief must include `\"confirmed\": true` (G explicitly confirmed it).")
    if "project_id" in p and not PROJECT_ID_RE.match(str(p["project_id"])):
        raise ParseError("project_id must match ^[A-Z][A-Z0-9-]{2,31}$.")
    for k in ("deliverables", "acceptance_criteria"):
        _nonempty_list(p, k)
    return dict(p)


def validate_brief_ref(req: dict) -> dict:
    """Adopt a brief KITT already published on GitHub at an exact commit."""
    ref = req.get("brief_ref")
    if not isinstance(ref, dict) or not isinstance(ref.get("path"), str) or ".." in ref.get("path", ""):
        raise ParseError("brief_ref must be {\"path\": \"<repo path>\", \"sha\": \"<40-char sha>\"}.")
    _sha(str(ref.get("sha", "")))
    if req.get("confirmed") is not True:
        raise ParseError("`confirmed: true` is required: G must explicitly confirm the published brief.")
    if not req.get("title") or not req.get("project_id"):
        raise ParseError("title and project_id are required when adopting a published brief.")
    if not PROJECT_ID_RE.match(str(req["project_id"])):
        raise ParseError("project_id must match ^[A-Z][A-Z0-9-]{2,31}$.")
    return {"title": req["title"], "project_id": req["project_id"], "confirmed": True,
            "brief_ref": {"path": ref["path"], "sha": ref["sha"]}}


def validate_changes(p: dict, need_route: bool) -> None:
    _nonempty_list(p, "changes")
    if need_route and p.get("route") not in ("documents", "development"):
        raise ParseError("Delivery changes require `route`: \"documents\" or \"development\".")


def parse_command(body: str) -> Command | None:
    """Return a Command, None if the comment is not a command, or raise ParseError."""
    if not body:
        return None
    line, idx = _first_line(body)
    if line is None or not line.startswith("/"):
        return None  # leading whitespace, quotes ('>') and fences are not top-level commands
    toks = line.strip().split()
    head = toks[0]
    if head not in COMMAND_PREFIXES:
        return None
    sub = toks[1] if len(toks) > 1 else ""
    rest = toks[2:]

    if head == "/project":
        if sub == "start":
            if rest:
                raise ParseError("Usage: /project start  (followed by a ```json brief block)")
            return Command("project start", {}, validate_brief(_payload(body, idx)))
        if sub in ("status", "pause", "resume"):
            if rest:
                raise ParseError(f"Usage: /project {sub}")
            return Command(f"project {sub}", {}, _payload(body, idx) or {})
        raise ParseError("Unknown /project subcommand. Use start, status, pause or resume.")

    if head == "/initial":
        if sub not in ("approve", "changes") or len(rest) != 2:
            raise ParseError("Usage: /initial approve|changes <cycle> <document_sha>")
        args = {"cycle": _cycle(rest[0]), "sha": _sha(rest[1])}
        p = _payload(body, idx) or {}
        if sub == "changes":
            validate_changes(p, need_route=False)
        return Command(f"initial {sub}", args, p)

    if head == "/delivery":
        if sub not in ("changes", "approve-close") or len(rest) != 2:
            raise ParseError("Usage: /delivery changes|approve-close <cycle> <delivery_sha>")
        args = {"cycle": _cycle(rest[0]), "sha": _sha(rest[1])}
        p = _payload(body, idx) or {}
        if sub == "changes":
            validate_changes(p, need_route=True)
        return Command(f"delivery {sub}", args, p)

    # /handoff <role> <task_type> <cycle> <input_sha>
    if len(toks) != 5:
        raise ParseError("Usage: /handoff <role> <task_type> <cycle> <input_sha>  (+ ```json manifest)")
    role = toks[1].upper()
    if role not in ROLES and role != "FOUNDER":
        raise ParseError(f"Unknown destination role {toks[1]!r}.")
    args = {"role": role, "task_type": toks[2], "cycle": _cycle(toks[3]), "sha": _sha(toks[4])}
    p = _payload(body, idx)
    if p is None:
        raise ParseError("`/handoff` requires a ```json manifest with: " + ", ".join(HANDOFF_REQUIRED) + ".")
    missing = [k for k in HANDOFF_REQUIRED if p.get(k) is None or (k != "expected_outputs" and p.get(k) in ("", []))]
    if missing:
        raise ParseError("Handoff manifest is incomplete. Missing: " + ", ".join(missing) + ".")
    _nonempty_list(p, "files")
    if not isinstance(p.get("expected_outputs"), list):
        raise ParseError("`expected_outputs` must be a list.")
    if not isinstance(p.get("revision"), int):
        raise ParseError("`revision` must be an integer.")
    return Command("handoff", args, p)
