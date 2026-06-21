"""Scrape github.com/trending.

GitHub has no official trending API, so we parse the public HTML page.
The selectors below match the current markup; if GitHub changes their HTML,
this is the one place that needs updating.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup

TRENDING_URL = "https://github.com/trending"
README_API = "https://api.github.com/repos/{full_name}/readme"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36 github-trending-mailer"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


@dataclass
class Repo:
    full_name: str          # "owner/repo"
    url: str                # "https://github.com/owner/repo"
    description: str
    language: str
    stars_total: str        # e.g. "12,345"
    stars_period: str       # e.g. "1,234 stars today"
    readme: str = ""        # trimmed README text (filled in optionally)

    def __hash__(self) -> int:
        return hash(self.full_name)


def _clean(text: str | None) -> str:
    return " ".join(text.split()) if text else ""


def _strip_readme_noise(md: str) -> str:
    """Drop the visual clutter that wastes tokens but adds no meaning."""
    # markdown images / badges:  ![alt](url)
    md = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", md)
    # raw <img ...> and other html tags
    md = re.sub(r"<[^>]+>", "", md)
    # HTML comments
    md = re.sub(r"<!--.*?-->", "", md, flags=re.DOTALL)
    # collapse blank-line runs
    md = re.sub(r"\n{3,}", "\n\n", md)
    return md.strip()


def fetch_readme(full_name: str, max_chars: int = 6000) -> str:
    """Fetch a repo's README via the GitHub API and trim it.

    Uses GITHUB_TOKEN if present (higher rate limit; auto-provided in Actions).
    Returns "" on any failure — a missing README must never break the digest.
    """
    headers = dict(HEADERS)
    headers["Accept"] = "application/vnd.github.raw+json"
    token = (os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        resp = requests.get(
            README_API.format(full_name=full_name), headers=headers, timeout=20
        )
        if resp.status_code != 200:
            return ""
        return _strip_readme_noise(resp.text)[:max_chars]
    except requests.RequestException:
        return ""


def fetch_trending(language: str = "", since: str = "daily", limit: int = 25) -> list[Repo]:
    """Return trending repos for a language ("" == all) and window."""
    url = f"{TRENDING_URL}/{language}" if language else TRENDING_URL
    resp = requests.get(url, params={"since": since}, headers=HEADERS, timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    repos: list[Repo] = []

    for article in soup.select("article.Box-row")[:limit]:
        link = article.select_one("h2 a")
        if not link or not link.get("href"):
            continue
        href = link["href"].strip("/")

        desc_el = article.select_one("p")
        lang_el = article.select_one('[itemprop="programmingLanguage"]')
        stars_el = article.select_one('a[href$="/stargazers"]')
        period_el = article.select_one("span.d-inline-block.float-sm-right")

        repos.append(
            Repo(
                full_name=href,
                url=f"https://github.com/{href}",
                description=_clean(desc_el.get_text() if desc_el else ""),
                language=_clean(lang_el.get_text() if lang_el else ""),
                stars_total=_clean(stars_el.get_text() if stars_el else ""),
                stars_period=_clean(period_el.get_text() if period_el else ""),
            )
        )

    return repos


def fetch_many(
    languages: list[str],
    since: str,
    max_repos: int,
    include_readme: bool = True,
    readme_chars: int = 6000,
) -> list[Repo]:
    """Fetch across several languages, de-dupe by repo name, preserve order.

    If include_readme is set, each kept repo also gets a trimmed README so the
    summarizer can explain it in real depth instead of just echoing the tagline.
    """
    seen: set[str] = set()
    merged: list[Repo] = []
    for lang in languages:
        for repo in fetch_trending(lang, since=since):
            if repo.full_name not in seen:
                seen.add(repo.full_name)
                merged.append(repo)

    merged = merged[:max_repos]

    if include_readme:
        for repo in merged:
            repo.readme = fetch_readme(repo.full_name, max_chars=readme_chars)

    return merged


if __name__ == "__main__":  # quick manual check
    for r in fetch_trending(limit=5):
        print(f"{r.full_name:40} {r.language:12} {r.stars_period}")
