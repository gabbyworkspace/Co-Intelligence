"""Authorization by authenticated GitHub actor (webhook `sender.login`)."""
from __future__ import annotations

from .config import Settings
from .errors import CommandRejected
from .models import HANDOFF_ALLOWED

FOUNDER_ONLY = {
    "project start", "initial approve", "initial changes", "delivery changes",
    "delivery approve-close", "project pause", "project resume",
}


def actor_roles(settings: Settings, actor: str) -> set[str]:
    a = actor.lower()
    return {r for r, cfg in settings.adapters.items() if cfg.github_login and cfg.github_login.lower() == a}


def is_founder(settings: Settings, actor: str) -> bool:
    """G's verified identity: the GitHub login, or (email channel only) a founder decision address.
    GitHub logins cannot contain '@', so an email address never matches a GitHub-authenticated actor."""
    a = actor.lower()
    if "@" in a:
        return a in {e.lower() for e in getattr(settings, "founder_decision_emails", ())}
    return a == settings.founder_login.lower()


FOUNDER_CHANNEL_MSG = ("Founder decisions are accepted only through a validated founder session: "
                       "brief and initial document review via the KITT session, final delivery approval or "
                       "changes via the JARVIS session. A GitHub comment or agent statement is not approval "
                       "evidence.")

# Action -> sessions allowed to carry G's decision.
ACTION_CHANNELS = {
    "project start": {"kitt_session"},
    "initial approve": {"kitt_session"},
    "initial changes": {"kitt_session"},
    "delivery changes": {"jarvis_session", "email"},
    "delivery approve-close": {"jarvis_session", "email"},
    "project pause": {"kitt_session", "jarvis_session"},
    "project resume": {"kitt_session", "jarvis_session"},
}


def authorize_action(settings: Settings, actor: str, action: str, project=None, *,
                     task=None, dest_role: str | None = None, channel: str = "github_comment") -> str:
    """Return the role the actor acts as, or raise CommandRejected.

    Founder actions require channel == 'kitt_session', i.e. an identity already
    verified by KittSessionVerifier. GitHub comments can never satisfy this."""
    if action in FOUNDER_ONLY:
        if channel not in ACTION_CHANNELS[action]:
            raise CommandRejected(FOUNDER_CHANNEL_MSG)
        if not is_founder(settings, actor):
            raise CommandRejected(f"@{actor} is not authorized for `{action}`. Only the configured founder may do this.")
        return "FOUNDER"
    if action == "project status":
        if is_founder(settings, actor) or actor_roles(settings, actor):
            return "FOUNDER" if is_founder(settings, actor) else sorted(actor_roles(settings, actor))[0]
        raise CommandRejected(f"@{actor} is not a configured participant.")
    if action == "handoff":
        if task is None:
            raise CommandRejected("No assigned open task matches this handoff.")
        roles = actor_roles(settings, actor)
        if task["role"] not in roles:
            raise CommandRejected(f"@{actor} is not the identity configured for role {task['role']}; "
                                  "agents may hand off only their own assigned work.")
        allowed = HANDOFF_ALLOWED.get((task["role"], task["task_type"]), set())
        if dest_role not in allowed:
            raise CommandRejected(f"{task['role']} may not hand off `{task['task_type']}` to {dest_role}. "
                                  f"Allowed: {', '.join(sorted(allowed)) or 'none'}.")
        return task["role"]
    raise CommandRejected(f"Unknown action {action!r}.")
