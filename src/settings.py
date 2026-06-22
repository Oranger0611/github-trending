"""Central place for tunable parameters and the LLM provider registry.

Everything here is "knobs you might turn" — token budgets, which providers exist,
their endpoints and default models. The rest of the code imports from this module
instead of hard-coding values, so there's exactly one place to edit.
"""

from __future__ import annotations

from dataclasses import dataclass

# ── LLM call sizing (max output tokens per call) ──────────────────────────────
MAX_TOKENS_DIGEST = 4096          # digest mode: one call for the whole list
MAX_TOKENS_DETAIL_SECTION = 1500  # detail mode: one section per repo
MAX_TOKENS_SYNTHESIS = 600        # detail mode: opening line + closing pick


# ── LLM providers ─────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class Provider:
    """Describes one LLM provider. Add a new one by adding an entry below."""

    label: str                       # human-readable name (used in logs)
    keys: tuple[str, ...]            # env vars to look for; first non-empty wins
    kind: str                        # wire protocol: "anthropic" | "openai"
    default_model: str               # used when no model is configured
    base_url: str | None = None      # OpenAI-compatible endpoint (None = SDK default)
    model_prefixes: tuple[str, ...] = ()  # model-name prefixes that imply this provider

    def owns_model(self, model: str) -> bool:
        m = model.lower()
        return any(m.startswith(prefix) for prefix in self.model_prefixes)


PROVIDERS: dict[str, Provider] = {
    "anthropic": Provider(
        label="Claude (Anthropic)",
        keys=("ANTHROPIC_API_KEY",),
        kind="anthropic",
        default_model="claude-sonnet-4-6",
        model_prefixes=("claude",),
    ),
    "openai": Provider(
        label="OpenAI",
        keys=("OPENAI_API_KEY", "OPENAI_KEY"),
        kind="openai",
        default_model="gpt-4o-mini",
        model_prefixes=("gpt", "o1", "o3", "o4", "chatgpt"),
    ),
    "gemini": Provider(
        label="Gemini (Google)",
        keys=("GEMINI_API_KEY", "GOOGLE_API_KEY"),
        kind="openai",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        default_model="gemini-2.0-flash",
        model_prefixes=("gemini",),
    ),
    "qwen": Provider(
        label="Qwen (Alibaba)",
        keys=("QWEN_API_KEY", "DASHSCOPE_API_KEY"),
        kind="openai",
        base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
        default_model="qwen-plus",
        model_prefixes=("qwen", "qwq"),
    ),
}


def provider_for_model(model: str) -> str | None:
    """Return the provider name a model belongs to, or None if unrecognized."""
    for name, provider in PROVIDERS.items():
        if provider.owns_model(model):
            return name
    return None

# Order used to pick a provider when more than one key is present.
PROVIDER_PRIORITY: tuple[str, ...] = ("anthropic", "openai", "gemini", "qwen")
