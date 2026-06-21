"""Turn the trending list into an email digest using the Claude API.

The "voice" and rules of the digest come entirely from prompts/instructions.md,
so you can change the output by editing that file — no code changes required.

Two modes:
  • digest  -> ONE call summarizes all repos together (fast, cheap).
  • detail  -> ONE call PER repo (deeper extraction from each README), then a
               final synthesis call adds the opening line + closing pick.
"""

from __future__ import annotations

import os

from anthropic import Anthropic

from .fetch_trending import Repo


def _client() -> Anthropic:
    return Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


def _cached_system(instructions: str) -> list[dict]:
    # Editable instructions as a cached system prompt. In detail mode this is
    # identical across every per-repo call, so caching gives real savings.
    return [{"type": "text", "text": instructions, "cache_control": {"type": "ephemeral"}}]


def _text(resp) -> str:
    return "".join(block.text for block in resp.content if block.type == "text")


def _format_one(r: Repo, idx: int) -> str:
    block = (
        f"## {idx}. {r.full_name}\n"
        f"url: {r.url}\n"
        f"language: {r.language or 'n/a'}\n"
        f"total stars: {r.stars_total or 'n/a'}\n"
        f"trending: {r.stars_period or 'trending today'}\n"
        f"description: {r.description or '(no description)'}"
    )
    if r.readme:
        block += (
            "\nREADME excerpt (use this to explain the repo in depth; "
            "summarize, don't copy):\n"
            '"""\n'
            f"{r.readme}\n"
            '"""'
        )
    return block


def _format_repos(repos: list[Repo]) -> str:
    return "\n\n".join(_format_one(r, i) for i, r in enumerate(repos, 1))


# ── digest mode ──────────────────────────────────────────────────────────────
def summarize(repos: list[Repo], instructions: str, model: str) -> str:
    """One call for the whole list. Returns the digest as Markdown."""
    client = _client()
    user_msg = (
        "Here are today's trending GitHub repositories. Write the digest in "
        "Markdown, following your instructions.\n\n"
        f"{_format_repos(repos)}"
    )
    resp = client.messages.create(
        model=model,
        max_tokens=4096,
        system=_cached_system(instructions),
        messages=[{"role": "user", "content": user_msg}],
    )
    return _text(resp)


# ── detail mode ──────────────────────────────────────────────────────────────
def summarize_detailed(
    repos: list[Repo], instructions: str, model: str, log=print
) -> str:
    """One LLM call per repo for a deep section, then assemble + synthesize.

    Returns the full digest as Markdown.
    """
    client = _client()
    system = _cached_system(instructions)
    sections: list[str] = []

    for i, r in enumerate(repos, 1):
        log(f"  [{i}/{len(repos)}] summarizing {r.full_name} ...")
        user_msg = (
            "Write the digest section for THIS ONE repository, following the "
            "per-repo format in your instructions. Pull the substance from its "
            "README excerpt. Return ONLY that repo's Markdown section, starting "
            "with the `### [owner/repo](url)` heading.\n\n"
            f"{_format_one(r, i)}"
        )
        resp = client.messages.create(
            model=model,
            max_tokens=1500,
            system=system,
            messages=[{"role": "user", "content": user_msg}],
        )
        sections.append(_text(resp).strip())

    body = "\n\n".join(sections)

    # Final synthesis: an opening vibe line + a closing "worth a closer look"
    # pick, derived from the sections we just wrote.
    log("  synthesizing opening + pick ...")
    overview = (
        "Here are the per-repo sections of today's GitHub Trending digest.\n"
        "Write exactly two things, in Markdown:\n"
        "1) A single opening line capturing the overall vibe of today's trends.\n"
        "2) A final pick titled '**Worth a closer look:**' naming the one repo "
        "I should open first and why (one or two sentences).\n"
        "Separate the two with a line containing only `---PICK---`.\n\n"
        f"{body}"
    )
    resp = client.messages.create(
        model=model,
        max_tokens=600,
        system=system,
        messages=[{"role": "user", "content": overview}],
    )
    intro, _, pick = _text(resp).partition("---PICK---")

    parts = [intro.strip(), body, pick.strip()]
    return "\n\n".join(p for p in parts if p)
