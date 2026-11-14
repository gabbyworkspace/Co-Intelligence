from __future__ import annotations

import os

from .base import AgentAdapter, AgentRequest, extract_json
from ..errors import InvalidInput


class AnthropicAdapter(AgentAdapter):
    URL = "https://api.anthropic.com/v1/messages"

    def problems(self):
        p = []
        if not self.cfg.model:
            p.append(f"{self.cfg.role}: ADAPTER_{self.cfg.role}_MODEL not set")
        if not os.environ.get(self.cfg.api_key_env or "ANTHROPIC_API_KEY"):
            p.append(f"{self.cfg.role}: API key env {self.cfg.api_key_env or 'ANTHROPIC_API_KEY'} not set")
        if self.cfg.price_in_per_mtok is None:
            p.append(f"{self.cfg.role}: prices not set; cost limit cannot be enforced")
        return p

    def run(self, req: AgentRequest) -> dict:
        self.check_cost(req)
        data = self.post_json(self.URL, {
            "model": self.cfg.model,
            "max_tokens": self.cfg.max_output_tokens,
            "system": req.system,
            "messages": [{"role": "user", "content": req.user}],
        }, {"x-api-key": self.api_key("ANTHROPIC_API_KEY"), "anthropic-version": "2023-06-01"})
        if data.get("stop_reason") == "max_tokens":
            raise InvalidInput(f"{self.cfg.role}: output truncated at max_tokens")
        text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
        return extract_json(text)
