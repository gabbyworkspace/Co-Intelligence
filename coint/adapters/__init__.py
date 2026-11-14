"""Callable agent adapters.

An ordinary chat (claude.ai, ChatGPT, Grok web) cannot be invoked automatically.
Each role must be configured with an adapter that is genuinely callable:

  anthropic      Anthropic Messages API (Claude)
  openai_compat  Any OpenAI-compatible /chat/completions API (OpenAI, xAI Grok, ...)
  http           Your own agent service endpoint (JSON in / JSON out)
  manual         A human/agent posts the output and an explicit /handoff comment;
                 the automation only assigns and validates.
  unsupported    Default. Tasks for this role are BLOCKED and reported.
"""
from __future__ import annotations

from ..config import AdapterConfig
from .base import AgentAdapter, AgentRequest, ManualAdapter, UnsupportedAdapterImpl
from .anthropic import AnthropicAdapter
from .http import HttpAdapter
from .openai_compat import OpenAICompatAdapter

KINDS = {
    "anthropic": AnthropicAdapter,
    "openai_compat": OpenAICompatAdapter,
    "http": HttpAdapter,
    "manual": ManualAdapter,
    "unsupported": UnsupportedAdapterImpl,
}


def build_adapter(cfg: AdapterConfig) -> AgentAdapter:
    cls = KINDS.get(cfg.kind, UnsupportedAdapterImpl)
    return cls(cfg)


__all__ = ["AgentAdapter", "AgentRequest", "build_adapter", "KINDS"]
