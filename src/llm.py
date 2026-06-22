"""Provider-agnostic LLM client — set ONE API key and it just works.

Supported providers (set whichever key you have):
  ANTHROPIC_API_KEY  -> Claude   (Anthropic)
  OPENAI_API_KEY     -> GPT      (OpenAI)
  GEMINI_API_KEY     -> Gemini   (Google, via its OpenAI-compatible endpoint)
  QWEN_API_KEY       -> Qwen     (Alibaba DashScope, OpenAI-compatible endpoint)

If several keys are set, the first one in settings.PROVIDER_PRIORITY wins —
override with LLM_PROVIDER=openai|anthropic|gemini|qwen.

The provider registry and token budgets live in src/settings.py.
"""

from __future__ import annotations

import os

from .settings import (
    PROVIDER_PRIORITY,
    PROVIDERS,
    Provider,
    provider_for_model,
)


def _key_for(provider: Provider) -> str:
    for name in provider.keys:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return ""


def _detect_provider(model: str | None = None) -> str:
    """Decide which provider to use.

    Order of decision:
      1. LLM_PROVIDER, if set (explicit override).
      2. The provider the requested model belongs to (e.g. "qwen-plus" -> qwen),
         so setting MODEL alone is enough — no separate provider selection.
      3. The first available key in PROVIDER_PRIORITY.
    """
    available = [name for name in PROVIDER_PRIORITY if _key_for(PROVIDERS[name])]

    forced = os.environ.get("LLM_PROVIDER", "").strip().lower()
    if forced:
        if forced not in PROVIDERS:
            raise SystemExit(
                f"Unknown LLM_PROVIDER='{forced}'. "
                f"Choose one of: {', '.join(PROVIDERS)}"
            )
        if not _key_for(PROVIDERS[forced]):
            keys = " or ".join(PROVIDERS[forced].keys)
            raise SystemExit(f"LLM_PROVIDER='{forced}' but no key set ({keys}).")
        return forced

    if not available:
        first_keys = ", ".join(p.keys[0] for p in PROVIDERS.values())
        raise SystemExit(
            "No LLM API key found. Set exactly ONE of these in your environment "
            f"(or .env / repo secrets): {first_keys}"
        )

    # If a specific model was requested, use the provider it belongs to.
    if model:
        owner = provider_for_model(model)
        if owner:
            if not _key_for(PROVIDERS[owner]):
                keys = " or ".join(PROVIDERS[owner].keys)
                raise SystemExit(
                    f"MODEL='{model}' looks like a {PROVIDERS[owner].label} model, "
                    f"but its API key isn't set ({keys})."
                )
            return owner

    if len(available) > 1:
        print(
            f"⚠️  Multiple LLM keys set ({', '.join(available)}); using '{available[0]}'. "
            "Set LLM_PROVIDER (or a provider-specific MODEL) to pick explicitly."
        )
    return available[0]


class LLM:
    """A tiny uniform wrapper: build once, call .chat(system, user)."""

    def __init__(self, name: str, model: str | None = None):
        self.name = name
        self.provider = PROVIDERS[name]
        self.model = model or self.provider.default_model
        self.api_key = _key_for(self.provider)

    @property
    def label(self) -> str:
        return self.provider.label

    def chat(self, system: str, user: str, max_tokens: int) -> str:
        if self.provider.kind == "anthropic":
            return self._anthropic(system, user, max_tokens)
        return self._openai_compatible(system, user, max_tokens)

    def _anthropic(self, system: str, user: str, max_tokens: int) -> str:
        from anthropic import Anthropic

        client = Anthropic(api_key=self.api_key)
        resp = client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            # Anthropic supports caching the (repeated) system prompt — real
            # savings in detail mode where it's identical across calls.
            system=[{"type": "text", "text": system,
                     "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": user}],
        )
        return "".join(b.text for b in resp.content if b.type == "text")

    def _openai_compatible(self, system: str, user: str, max_tokens: int) -> str:
        from openai import OpenAI

        client = OpenAI(api_key=self.api_key, base_url=self.provider.base_url)
        resp = client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return resp.choices[0].message.content or ""


def get_client(model_override: str | None = None) -> LLM:
    """Detect the provider (from LLM_PROVIDER, the model name, or available keys)
    and return a ready-to-use client."""
    return LLM(_detect_provider(model_override), model_override)
