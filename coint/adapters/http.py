from __future__ import annotations

import os

from .base import AgentAdapter, AgentRequest


class HttpAdapter(AgentAdapter):
    """POSTs {role, task_type, system, user, limits} to your own agent service,
    which must return the output JSON object described in prompts/OUTPUT_SCHEMA.md."""

    def problems(self):
        p = []
        if not self.cfg.endpoint:
            p.append(f"{self.cfg.role}: ADAPTER_{self.cfg.role}_ENDPOINT not set")
        if self.cfg.api_key_env and not os.environ.get(self.cfg.api_key_env):
            p.append(f"{self.cfg.role}: key env {self.cfg.api_key_env} not set")
        return p

    def run(self, req: AgentRequest) -> dict:
        headers = {}
        if self.cfg.api_key_env:
            headers["Authorization"] = f"Bearer {self.api_key(self.cfg.api_key_env)}"
        return self.post_json(self.cfg.endpoint, {
            "role": req.role, "task_type": req.task_type, "system": req.system, "user": req.user,
            "limits": {"max_runtime_s": self.cfg.max_runtime_s, "max_output_tokens": self.cfg.max_output_tokens,
                       "max_cost_usd": self.cfg.max_cost_usd},
        }, headers)
