"""Orchestrate the daily digest: fetch -> summarize -> render -> send.

Run locally and email it:        python -m src.main
Local, no email, open in browser: python -m src.main --html
Dry run (print Markdown only):    python -m src.main --dry-run
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import pathlib
import sys
import webbrowser

import yaml

try:
    # Load a local .env automatically so you don't have to `source` it.
    # (No-op in GitHub Actions, where secrets come from the environment.)
    from dotenv import load_dotenv

    load_dotenv()
except ModuleNotFoundError:
    pass

from .fetch_trending import fetch_many
from .render_email import render_html
from .send_email import send_email
from .summarize import summarize, summarize_detailed

ROOT = pathlib.Path(__file__).resolve().parent.parent


def load_config() -> dict:
    with open(ROOT / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_instructions() -> str:
    return (ROOT / "prompts" / "instructions.md").read_text(encoding="utf-8")


def normalize_output(value: str) -> str:
    """Map friendly aliases to 'html' (local file) or 'email' (send via Gmail)."""
    v = (value or "").strip().lower()
    if v in ("html", "local", "file"):
        return "html"
    if v in ("email", "mail", "git", "send"):
        return "email"
    return "email"  # safe default


def env_flag(name: str, default: bool) -> bool:
    """Read a truthy/falsy env var (1/true/yes/on vs 0/false/no/off)."""
    v = os.environ.get(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


def trigger_tag() -> str:
    """A short label for how this run was triggered, for the email subject.

    - scheduled daily run  -> ""           (default mode, no tag)
    - push to a run/* branch -> "[run/<name>]"  (special mode)
    - manual / other       -> "[<branch>]"
    """
    event = os.environ.get("GITHUB_EVENT_NAME", "").strip()
    ref = os.environ.get("GITHUB_REF_NAME", "").strip()
    if event == "schedule" or not ref or ref == "main":
        return ""
    return f"[{ref}] "


def resolve_recipients(config: dict) -> list[str]:
    recipients = [r for r in (config.get("recipients") or []) if r]
    if recipients:
        return recipients
    env_to = os.environ.get("MAIL_TO", "").strip()
    if env_to:
        return [addr.strip() for addr in env_to.split(",") if addr.strip()]
    return []  # send_email falls back to GMAIL_USER


def main() -> int:
    parser = argparse.ArgumentParser(description="Daily GitHub Trending email digest")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print the Markdown digest instead of emailing it")
    parser.add_argument("--html", action="store_true",
                        help="Local mode: write the digest to an HTML file and open "
                             "it in your browser. No email, no Gmail keys needed.")
    parser.add_argument("--out", default=None,
                        help="Path for the --html file (default: output/trending-<date>.html)")
    parser.add_argument("--no-open", action="store_true",
                        help="With --html, don't auto-open the file in a browser")
    parser.add_argument("--model", default=None,
                        help="Claude model to use (overrides MODEL env and config.yaml)")
    parser.add_argument("--mode", choices=["digest", "detail"], default=None,
                        help="digest = one call for all repos; "
                             "detail = one call per repo + README (deeper)")
    args = parser.parse_args()

    config = load_config()
    languages = config.get("languages") or [""]
    since = config.get("since", "daily")
    max_repos = int(config.get("max_repos", 12))
    # Model priority: --model flag > MODEL env var > config.yaml > default.
    model = args.model or os.environ.get("MODEL") or config.get("model", "claude-sonnet-4-6")
    # Mode priority: --mode flag > MODE env var > config.yaml > "digest".
    mode = args.mode or os.environ.get("MODE") or config.get("mode", "digest")
    # Output priority: --html flag > OUTPUT env var > config.yaml > "email".
    raw_output = ("html" if args.html else None) or os.environ.get("OUTPUT") \
        or config.get("output", "email")
    output = normalize_output(raw_output)
    subject_prefix = config.get("subject_prefix", "GitHub Trending")
    include_readme = bool(config.get("include_readme", True))
    readme_chars = int(config.get("readme_chars", 6000))

    print(f"Fetching {since} trending for languages={languages} "
          f"(readme={'on' if include_readme else 'off'}) ...")
    repos = fetch_many(
        languages,
        since=since,
        max_repos=max_repos,
        include_readme=include_readme,
        readme_chars=readme_chars,
    )
    if not repos:
        print("No trending repos found — aborting.", file=sys.stderr)
        return 1
    print(f"Got {len(repos)} repos. Mode={mode}, model={model}. Writing the digest ...")

    instructions = load_instructions()
    if mode == "detail":
        markdown_body = summarize_detailed(repos, instructions, model)
    else:
        markdown_body = summarize(repos, instructions, model)

    today = dt.date.today().strftime("%b %d, %Y")
    mode_tag = " · detail" if mode == "detail" else ""
    title = f"{trigger_tag()}{subject_prefix}{mode_tag} — {today}"

    if args.dry_run:
        print("\n" + "=" * 60 + f"\n{title}\n" + "=" * 60 + "\n")
        print(markdown_body)
        return 0

    html = render_html(markdown_body, title)

    # ── Local mode: write an HTML file and open it, no email ──────────────────
    if output == "html":
        out_setting = args.out or os.environ.get("OUTPUT_PATH")
        if out_setting:
            out_path = pathlib.Path(out_setting).expanduser().resolve()
        else:
            out_path = ROOT / "output" / f"trending-{dt.date.today().isoformat()}.html"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(html, encoding="utf-8")
        print(f"\n✅ Wrote digest to {out_path}")
        # Open unless --no-open, or OPEN_BROWSER=false in the env.
        if not args.no_open and env_flag("OPEN_BROWSER", default=True):
            webbrowser.open(out_path.as_uri())
            print("   Opened it in your browser.")
        return 0

    recipients = resolve_recipients(config)
    try:
        send_email(
            subject=title,
            html_body=html,
            text_fallback=markdown_body,
            recipients=recipients,
        )
    except Exception as exc:  # surface the real reason instead of failing silently
        print(f"\n❌ Email send FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        print(
            "Common causes:\n"
            "  • GMAIL_APP_PASSWORD is wrong or is your login password "
            "(it must be a 16-char App Password from "
            "https://myaccount.google.com/apppasswords)\n"
            "  • 2-Step Verification is not enabled on the Gmail account\n"
            "  • GMAIL_USER is missing/incorrect",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
