from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass

from ..config import AdapterConfig
from ..errors import AuthError, InvalidInput, PermanentError, PermissionDenied, TransientError, UnsupportedAdapter


@dataclass
class AgentRequest:
    role: str
    task_type: str
    system: str
    user: str


class AgentAdapter:
    external = False

    def __init__(self, cfg: AdapterConfig):
        self.cfg = cfg

    def problems(self) -> list[str]:
        """Configuration problems reported by `coint doctor` (no network calls)."""
        return []

    def run(self, req: AgentRequest) -> dict:
        raise NotImplementedError

    # -- helpers ------------------------------------------------------------
    def api_key(self, default_env: str) -> str:
        name = self.cfg.api_key_env or default_env
        key = os.environ.get(name)
        if not key:
            raise AuthError(f"{self.cfg.role}: API key env var {name} is not set")
        return key

    def check_cost(self, req: AgentRequest) -> None:
        """Worst-case cost guard: input estimate + max output tokens."""
        pin, pout = self.cfg.price_in_per_mtok, self.cfg.price_out_per_mtok
        if pin is None or pout is None:
            return  # reported by doctor as an unpriced adapter
        est_in = (len(req.system) + len(req.user)) / 3.5
        worst = (est_in * pin + self.cfg.max_output_tokens * pout) / 1_000_000
        if worst > self.cfg.max_cost_usd:
            raise PermanentError(f"{self.cfg.role}: worst-case cost ${worst:.2f} exceeds limit "
                                 f"${self.cfg.max_cost_usd:.2f}; reduce inputs or raise the limit")

    def post_json(self, url: str, body: dict, headers: dict) -> dict:
        req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST")
        req.add_header("Content-Type", "application/json")
        for k, v in headers.items():
            req.add_header(k, v)
        try:
            with urllib.request.urlopen(req, timeout=self.cfg.max_runtime_s) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            msg = e.read()[:500].decode(errors="replace")
            if e.code == 401:
                raise AuthError(f"{self.cfg.role} adapter 401: {msg}")
            if e.code == 403:
                raise PermissionDenied(f"{self.cfg.role} adapter 403: {msg}")
            if e.code in (400, 404, 413, 422):
                raise InvalidInput(f"{self.cfg.role} adapter {e.code}: {msg}")
            raise TransientError(f"{self.cfg.role} adapter {e.code}: {msg}")
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            raise TransientError(f"{self.cfg.role} adapter network/timeout: {e}")


def extract_json(text: str) -> dict:
    """Parse the single JSON object a model was asked to return."""
    t = text.strip()
    m = re.search(r"```(?:json)?\s*(\{.*\})\s*```", t, re.S)
    if m:
        t = m.group(1)
    else:
        i, j = t.find("{"), t.rfind("}")
        if i == -1 or j == -1:
            raise InvalidInput("agent output contains no JSON object")
        t = t[i:j + 1]
    try:
        obj = json.loads(t)
    except ValueError as e:
        raise InvalidInput(f"agent output is not valid JSON: {e}")
    if not isinstance(obj, dict):
        raise InvalidInput("agent output must be a JSON object")
    return obj


class ManualAdapter(AgentAdapter):
    """Not invoked. The task is assigned on the issue; the configured GitHub
    identity publishes files and posts an explicit /handoff."""
    external = True

    def problems(self):
        return [] if self.cfg.github_login else [
            f"{self.cfg.role}: manual adapter needs ADAPTER_{self.cfg.role}_GITHUB_LOGIN"]

    def run(self, req):
        raise UnsupportedAdapter(f"{self.cfg.role} is manual; it cannot be invoked automatically")


class UnsupportedAdapterImpl(AgentAdapter):
    def problems(self):
        return [f"{self.cfg.role}: no callable adapter configured (kind={self.cfg.kind!r})"]

    def run(self, req):
        raise UnsupportedAdapter(f"{self.cfg.role}: no callable adapter configured (kind={self.cfg.kind!r})")
