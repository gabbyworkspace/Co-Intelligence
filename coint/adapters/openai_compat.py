from __future__ import annotations

import os

from .base import AgentAdapter, AgentRequest, extract_json
from ..errors import InvalidInput


class OpenAICompatAdapter(AgentAdapter):
    """OpenAI-compatible chat completions (e.g. https://api.x.ai/v1 for Grok)."""

    def problems(self):
        p = []
        if not self.cfg.endpoint:
            p.append(f"{self.cfg.role}: ADAPTER_{self.cfg.role}_ENDPOINT (base URL) not set")
        if not self.cfg.model:
            p.append(f"{self.cfg.role}: ADAPTER_{self.cfg.role}_MODEL not set")
        if not self.cfg.api_key_env or not os.environ.get(self.cfg.api_key_env):
            p.append(f"{self.cfg.role}: ADAPTER_{self.cfg.role}_API_KEY_ENV not set or key missing")
        if self.cfg.price_in_per_mtok is None:
            p.append(f"{self.cfg.role}: prices not set; cost limit cannot be enforced")
        return p

    def run(self, req: AgentRequest) -> dict:
        self.check_cost(req)
        data = self.post_json(self.cfg.endpoint.rstrip("/") + "/chat/completions", {
            "model": self.cfg.model,
            "max_tokens": self.cfg.max_output_tokens,
            "response_format": {"type": "json_object"},
            "messages": [{"role": "system", "content": req.system},
                         {"role": "user", "content": req.user}],
        }, {"Authorization": f"Bearer {self.api_key(self.cfg.api_key_env or 'OPENAI_API_KEY')}"})
        choice = (data.get("choices") or [{}])[0]
        if choice.get("finish_reason") == "length":
            raise InvalidInput(f"{self.cfg.role}: output truncated at max_tokens")
        return extract_json((choice.get("message") or {}).get("content") or "")
