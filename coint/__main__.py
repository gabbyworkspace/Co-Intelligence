"""CLI: python -m coint {serve|scheduler|run-job|doctor|init-db|audit}"""
from __future__ import annotations

import argparse
import json
import logging
import sys

from .config import FINAL_REPORT_FROM, ConfigError, load_settings
from .db import DB


def build_engine(settings, *, need_github=True):
    from .github import GitHubAppClient
    from .gmail import GmailClient
    from .workflow import Engine
    db = DB(settings.db_path)
    gh = GitHubAppClient(settings) if need_github else None
    try:
        gmail = GmailClient(settings)
    except Exception:  # noqa: BLE001 - reported by doctor; email rows will BLOCK
        gmail = None
    return Engine(settings, db, gh, gmail=gmail)


def doctor(settings) -> int:
    """Validate connections without asking for passwords. Exit 1 if anything is missing."""
    from .adapters import build_adapter
    problems, ok = [], []
    if not settings.webhook_secret:
        problems.append("GITHUB_WEBHOOK_SECRET not set")
    try:
        from .github import GitHubAppClient
        info = GitHubAppClient(settings).validate_access()
        perms = info.get("permissions") or {}
        ok.append(f"GitHub App access to {info['full_name']} (id {info['id']})")
        if settings.github_repo_id and str(info["id"]) != str(settings.github_repo_id):
            problems.append("GITHUB_REPO_ID does not match repository")
        if perms and not (perms.get("push") or perms.get("admin")):
            problems.append("GitHub App lacks contents write permission")
    except Exception as e:  # noqa: BLE001
        problems.append(f"GitHub: {e}")
    try:
        from .gmail import GmailClient
        addr = GmailClient(settings).authorized_address()
        (ok if addr == FINAL_REPORT_FROM else problems).append(f"Gmail authorized as {addr}")
    except Exception as e:  # noqa: BLE001
        problems.append(f"Gmail: {e}")
    if settings.kitt_oauth_client_id and settings.kitt_oauth_client_secret:
        ok.append("KITT session channel configured (GitHub OAuth app "
                  f"{settings.kitt_oauth_client_id}); founder decisions accepted only from it")
    else:
        problems.append("BLOCKER: KITT session founder-decision channel not configured "
                        "(KITT_OAUTH_CLIENT_ID / KITT_OAUTH_CLIENT_SECRET). G's approvals cannot be "
                        "validated, so no founder decision will be accepted.")
    for role, cfg in settings.adapters.items():
        p = build_adapter(cfg).problems()
        if p:
            problems.extend(p)
        else:
            ok.append(f"{role}: {cfg.kind} adapter configured" + (" (manual: requires explicit /handoff)"
                                                                     if cfg.kind == "manual" else ""))
    print(json.dumps({"founder": settings.founder_login, "ok": ok, "problems": problems}, indent=2))
    return 1 if problems else 0


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    ap = argparse.ArgumentParser(prog="coint")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("serve")
    s.add_argument("--host", default="0.0.0.0")
    s.add_argument("--port", type=int, default=8080)
    s.add_argument("--concurrency", type=int, default=4)
    sub.add_parser("scheduler")
    j = sub.add_parser("run-job")
    j.add_argument("name")
    sub.add_parser("doctor")
    sub.add_parser("init-db")
    a = sub.add_parser("audit")
    a.add_argument("--project")
    a.add_argument("--limit", type=int, default=50)
    args = ap.parse_args(argv)
    try:
        settings = load_settings()
    except ConfigError as e:
        print(f"configuration error: {e}", file=sys.stderr)
        return 2
    if args.cmd == "doctor":
        return doctor(settings)
    if args.cmd == "init-db":
        DB(settings.db_path)
        print(f"database ready at {settings.db_path}")
        return 0
    if args.cmd == "audit":
        db = DB(settings.db_path)
        q = "SELECT * FROM audit_events" + (" WHERE project_id=?" if args.project else "") + " ORDER BY id DESC LIMIT ?"
        for r in db.all(q, *([args.project] if args.project else []), args.limit):
            print(json.dumps(dict(r)))
        return 0
    engine = build_engine(settings)
    if args.cmd == "serve":
        from .server import serve
        serve(engine, args.host, args.port, args.concurrency)
    elif args.cmd == "scheduler":
        from .scheduler import run_forever
        run_forever(engine)
    elif args.cmd == "run-job":
        from .scheduler import run_job
        print(json.dumps(run_job(engine, args.name), default=str, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
