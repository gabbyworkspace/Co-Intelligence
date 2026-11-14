"""Configuration.

Fixed values from the specification are constants and cannot be overridden by
environment variables, repository text, or model output. Secrets are read only
from the process environment (or files referenced by *_FILE variables) and are
never written to the repository, the database, or model prompts.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

# ---- Fixed configuration (spec: FIXED CONFIGURATION) -----------------------
GITHUB_OWNER = "gabbyworkspace"
GITHUB_REPO = "Co-Intelligence"
GITHUB_URL = "https://github.com/gabbyworkspace/Co-Intelligence"
FINAL_REPORT_FROM = "jarvis.resystem@gmail.com"
FINAL_REPORT_TO = "g@resystem.org"
TIMEZONE = "Asia/Dubai"

ROLES = ("KITT", "JARVIS", "GRONK", "COUNCIL_1", "COUNCIL_2", "COUNCIL_3", "COUNCIL_4")
COUNCIL_ROLES = ROLES[3:]

_LOGIN_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")


class ConfigError(Exception):
    pass


def _env(name: str, default: str | None = None) -> str | None:
    """Read NAME, or the file named by NAME_FILE (docker/k8s secrets)."""
    path = os.environ.get(f"{name}_FILE")
    if path:
        try:
            with open(path, encoding="utf-8") as fh:
                return fh.read().strip()
        except OSError as e:
            raise ConfigError(f"{name}_FILE={path} cannot be read: {e.strerror}")
    val = os.environ.get(name)
    return val if val not in (None, "") else default


def _int(name: str, default: int) -> int:
    v = _env(name)
    return int(v) if v is not None else default


def _float(name: str, default: float) -> float:
    v = _env(name)
    return float(v) if v is not None else default


@dataclass
class AdapterConfig:
    role: str
    kind: str  # anthropic | openai_compat | http | manual | unsupported
    model: str | None = None
    endpoint: str | None = None
    api_key_env: str | None = None  # NAME of the env var holding the key, never the key
    github_login: str | None = None  # identity used for manual /handoff authorization
    max_runtime_s: int = 900
    max_output_tokens: int = 16000
    max_cost_usd: float = 5.0
    price_in_per_mtok: float | None = None   # USD per 1M input tokens (for cost limit)
    price_out_per_mtok: float | None = None  # USD per 1M output tokens


@dataclass
class Settings:
    founder_login: str
    db_path: str
    webhook_secret: str | None
    github_app_id: str | None
    github_app_private_key: str | None
    github_installation_id: str | None
    github_repo_id: str | None
    app_bot_login: str | None
    gmail_client_id: str | None
    gmail_client_secret: str | None
    gmail_refresh_token: str | None
    adapters: dict[str, AdapterConfig] = field(default_factory=dict)
    kitt_oauth_client_id: str | None = None      # GitHub OAuth App used by KITT's GPT Action
    kitt_oauth_client_secret: str | None = None
    founder_user_id: str | None = None           # optional: pin G's numeric GitHub user id
    public_base_url: str | None = None           # e.g. https://coint.example.com (for OpenAPI)
    lease_seconds: int = 300
    heartbeat_seconds: int = 60
    lease_grace_seconds: int = 120
    council_timeout_minutes: int = 60
    stage_timeout_minutes: int = 240
    retry_delays_minutes: tuple[int, ...] = (1, 5, 15)
    max_revision_loops: int = 3
    email_reconcile_wait_minutes: int = 15
    require_checks_pass: bool = True
    max_webhook_bytes: int = 5 * 1024 * 1024
    project_branch_prefix: str = "co-intel/"
    owner: str = GITHUB_OWNER
    repo: str = GITHUB_REPO

    @property
    def repo_full_name(self) -> str:
        return f"{self.owner}/{self.repo}"


def _adapter(role: str) -> AdapterConfig:
    key = role.upper()
    kind = (_env(f"ADAPTER_{key}_KIND") or "unsupported").lower()
    return AdapterConfig(
        role=role,
        kind=kind,
        model=_env(f"ADAPTER_{key}_MODEL"),
        endpoint=_env(f"ADAPTER_{key}_ENDPOINT"),
        api_key_env=_env(f"ADAPTER_{key}_API_KEY_ENV"),
        github_login=_env(f"ADAPTER_{key}_GITHUB_LOGIN"),
        max_runtime_s=_int(f"ADAPTER_{key}_MAX_RUNTIME_S", 900),
        max_output_tokens=_int(f"ADAPTER_{key}_MAX_OUTPUT_TOKENS", 16000),
        max_cost_usd=_float(f"ADAPTER_{key}_MAX_COST_USD", 5.0),
        price_in_per_mtok=_float(f"ADAPTER_{key}_PRICE_IN_PER_MTOK", -1) if _env(f"ADAPTER_{key}_PRICE_IN_PER_MTOK") else None,
        price_out_per_mtok=_float(f"ADAPTER_{key}_PRICE_OUT_PER_MTOK", -1) if _env(f"ADAPTER_{key}_PRICE_OUT_PER_MTOK") else None,
    )


def load_settings() -> Settings:
    founder = _env("FOUNDER_GITHUB_USERNAME")
    if not founder:
        raise ConfigError(
            "FOUNDER_GITHUB_USERNAME is required. Set it to G's actual GitHub login; "
            "the repository owner is NOT assumed to be G."
        )
    if not _LOGIN_RE.match(founder):
        raise ConfigError(f"FOUNDER_GITHUB_USERNAME {founder!r} is not a valid GitHub login")
    # Recipient/sender overrides are refused, not silently ignored.
    for name, fixed in (("FINAL_REPORT_TO", FINAL_REPORT_TO), ("FINAL_REPORT_FROM", FINAL_REPORT_FROM)):
        v = _env(name)
        if v is not None and v.strip().lower() != fixed:
            raise ConfigError(f"{name} is fixed to {fixed} and cannot be changed")
    for name, fixed in (("GITHUB_OWNER", GITHUB_OWNER), ("GITHUB_REPO", GITHUB_REPO)):
        v = _env(name)
        if v is not None and v.lower() != fixed.lower():
            raise ConfigError(f"{name} is fixed to {fixed} and cannot be changed")

    delays = tuple(int(x) for x in (_env("RETRY_DELAYS_MINUTES") or "1,5,15").split(","))
    return Settings(
        founder_login=founder,
        db_path=_env("COINT_DB_PATH", "./data/coint.sqlite3"),
        webhook_secret=_env("GITHUB_WEBHOOK_SECRET"),
        github_app_id=_env("GITHUB_APP_ID"),
        github_app_private_key=_env("GITHUB_APP_PRIVATE_KEY"),
        github_installation_id=_env("GITHUB_APP_INSTALLATION_ID"),
        github_repo_id=_env("GITHUB_REPO_ID"),
        app_bot_login=_env("GITHUB_APP_BOT_LOGIN"),
        gmail_client_id=_env("GMAIL_CLIENT_ID"),
        gmail_client_secret=_env("GMAIL_CLIENT_SECRET"),
        gmail_refresh_token=_env("GMAIL_REFRESH_TOKEN"),
        adapters={r: _adapter(r) for r in ROLES},
        kitt_oauth_client_id=_env("KITT_OAUTH_CLIENT_ID"),
        kitt_oauth_client_secret=_env("KITT_OAUTH_CLIENT_SECRET"),
        founder_user_id=_env("FOUNDER_GITHUB_USER_ID"),
        public_base_url=_env("PUBLIC_BASE_URL"),
        lease_seconds=_int("LEASE_SECONDS", 300),
        heartbeat_seconds=_int("HEARTBEAT_SECONDS", 60),
        lease_grace_seconds=_int("LEASE_GRACE_SECONDS", 120),
        council_timeout_minutes=_int("COUNCIL_REVIEW_TIMEOUT_MINUTES", 60),
        stage_timeout_minutes=_int("STAGE_TIMEOUT_MINUTES", 240),
        retry_delays_minutes=delays,
        max_revision_loops=_int("MAX_REVISION_LOOPS", 3),
        email_reconcile_wait_minutes=_int("EMAIL_RECONCILE_WAIT_MINUTES", 15),
        require_checks_pass=(_env("REQUIRE_CHECKS_PASS", "true").lower() == "true"),
    )
