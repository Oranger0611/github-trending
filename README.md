# 🔥 GitHub Trending Digest

**A hands-off daily email that explains what's trending on GitHub — in plain English, no jargon.**

![Python](https://img.shields.io/badge/python-3.12-blue)
![Runs on](https://img.shields.io/badge/runs%20on-GitHub%20Actions-black)
![LLM](https://img.shields.io/badge/summaries-Claude-orange)
![Cost](https://img.shields.io/badge/cost-~%240.03–0.10%2Fday-green)

Set it up once on **GitHub Actions** and forget it. Every morning it scrapes
[github.com/trending](https://github.com/trending), asks **Claude** to turn the raw
list into a readable digest, and **emails it to your inbox** — automatically, for
free, while you sleep. (You can also run it locally on demand.)

[**▶ Set up the daily email**](#-set-up-the-daily-email-the-main-feature) ·
[How it works](#-how-it-works) ·
[Automation modes](#-automation-modes) ·
[Customize the writing](#%EF%B8%8F-customize-the-writing) ·
[Configuration](#%EF%B8%8F-configuration) ·
[Cost](#-cost) ·
[Run locally](#-run-locally-optional)

---

## What it does

- **🤖 Fully automated** — a GitHub Actions cron runs every day and emails you the digest. Zero servers, zero maintenance, nothing to keep running on your machine.
- **Scrapes GitHub Trending** for the day (any language, or all languages).
- **Reads each repo's README** and summarizes the substance — not just the tagline.
- **Explains it for humans** — every acronym is translated into a concrete benefit; each repo gets a 3-second "hook" plus skimmable bullets.
- **Two depth modes** — a fast single-call `digest`, or a per-repo `detail` deep dive.
- **You own the voice** — a single plain-text prompt file controls tone, depth, and which topics get explained in detail.
- **On-demand reruns** — push a `run/*` branch to trigger an instant custom digest, or run it locally as an HTML file.

<img width="960" height="663" alt="Screenshot 2026-06-21 at 23 01 49" src="https://github.com/user-attachments/assets/080f9dce-eff0-46fc-94d1-93d59550e5c2" />

---

## 🤖 Set up the daily email (the main feature)

This is the whole point: **configure it once, get a digest every morning forever.**
Takes about 3 minutes.

### 1. Fork / push this repo to your GitHub

```bash
git remote add origin https://github.com/<you>/github-trending.git
git branch -M main && git push -u origin main
```

### 2. Add your secrets

Repo → **Settings → Secrets and variables → Actions → New repository secret**:

| Secret | Value |
|---|---|
| `ANTHROPIC_API_KEY` | <https://console.anthropic.com/settings/keys> |
| `GMAIL_USER` | your Gmail address (the sender) |
| `GMAIL_APP_PASSWORD` | a 16-char **App Password** — <https://myaccount.google.com/apppasswords> (needs 2-Step Verification on; **not** your login password) |
| `MAIL_TO` | *(optional)* who receives it; defaults to yourself |

Optional repo **Variables** (same screen, *Variables* tab): `MODEL`, `MODE`, `OUTPUT`.

### 3. Turn it on & test

- The workflow is already in [`.github/workflows/daily-trending.yml`](.github/workflows/daily-trending.yml).
- Test it immediately: **Actions → Daily GitHub Trending Digest → Run workflow**.
  You should get the email within a minute.
- After that, it runs on its own — **`00:00 UTC` daily** (`07:00` Vietnam time).

### 4. (Optional) Change the schedule

Edit the `cron` line in the workflow — use [crontab.guru](https://crontab.guru) to
pick your time:

```yaml
on:
  schedule:
    - cron: "0 0 * * *"   # 00:00 UTC every day
```

That's the entire setup. Everything below is optional tuning.

---

## 🏗 How it works

```
                  ┌──────────────────────┐
   GitHub Actions │   src/fetch_trending │  scrape github.com/trending
   (daily cron) ─►│                      │  + pull each repo's README
                  └──────────┬───────────┘
                             ▼
                  ┌──────────────────────┐
                  │    src/summarize     │  Claude writes the digest,
                  │  (prompts/*.md)      │  guided by your prompt file
                  └──────────┬───────────┘
                             ▼
                  ┌──────────────────────┐
                  │   src/render_email   │  Markdown → styled HTML
                  └──────────┬───────────┘
                             ▼
                  ┌──────────────────────┐
                  │    src/send_email    │  Gmail SMTP → your inbox 📬
                  └──────────────────────┘
```

---

## 🔁 Automation modes

**Default — automatic, every day.** The cron runs on `main` using the prompt
committed there and emails you. You do nothing.

**On-demand — push a `run/*` branch for an instant custom digest.** Want a one-off
run with different instructions, right now?

```bash
git checkout -b run/deep-dive-rust
# edit prompts/instructions.md however you like
git commit -am "explain rust repos in depth today"
git push -u origin run/deep-dive-rust   # ← this push triggers a run immediately
```

It runs using **that branch's** prompt, and the email subject is tagged with the
branch name (e.g. `[run/deep-dive-rust] 🔥 GitHub Trending — …`) so you can spot
special runs. Happy with the changes long-term? Merge the branch into `main` to
make them the new default.

> You can also trigger any run by hand: **Actions → Run workflow**.

---

## ✍️ Customize the writing

The entire voice of the digest lives in **[`prompts/instructions.md`](prompts/instructions.md)** —
plain English, no code. Commit a change and the next daily run uses it. Edit it to:

- **More / less detail** — adjust the length rules.
- **Explain certain topics deeply** — add lines under *"Topics I want explained in DETAIL"* (e.g. `Rust async`, `databases`, `LLM agents`).
- **Keep boring topics short** — add lines under *"Topics to keep SHORT or skip"*.

The prompt already enforces readability rules: **no naked jargon** (every acronym
is translated into a benefit), a **3-second hook** per repo, and **bullets instead
of walls of text**.

---

## ⚙️ Configuration

Defaults the cron uses live in **`config.yaml`** (committed). For local runs you can
also use a **`.env`** file or CLI flags.

> **Precedence:** CLI flag → `.env` / env var → `config.yaml` → built-in default.

### `config.yaml` (defaults the daily cron uses)

```yaml
languages: [""]        # "" = all; add "python", "rust", etc.
since: daily           # daily | weekly | monthly
max_repos: 12
include_readme: true   # pull READMEs for deeper summaries
mode: digest           # digest = one call for all | detail = per-repo deep dive
model: claude-sonnet-4-6
```

### Picking a model

| Model | Best for | Relative cost |
|---|---|---|
| `claude-opus-4-8` | Highest quality, follows formatting rules best | $$$ |
| `claude-sonnet-4-6` | Great daily default | $ |
| `claude-haiku-4-5-20251001` | Fastest & cheapest | ¢ |

Override per-run without editing the file: set a repo **Variable** `MODEL` (for the
cron), or use `--model` / `MODEL=` locally.

---

## 💰 Cost

This is cheap to run. The only paid piece is the Claude API call(s) that write the
digest — **roughly `$0.03–0.10` per day**, i.e. about **$1–3 for a whole month**.

| What | Cost |
|---|---|
| **Claude summarization** | **~$0.03–0.10 per day** (varies by model & mode) |
| GitHub Trending scrape | Free |
| Reading repo READMEs (GitHub API) | Free |
| **GitHub Actions (daily cron)** | **Free** (well within the free tier) |
| Gmail sending | Free |

- `digest` mode = one Claude call/day → the **low** end (~$0.03).
- `detail` mode = one call **per repo** → the **high** end (~$0.10), more on `claude-opus-4-8`.
- Cut it further: lower `max_repos`, trim `readme_chars`, or use `claude-haiku-4-5-20251001`.

---

## 💻 Run locally (optional)

Don't want to wait for the cron, or want to preview without email? Run it on your
machine. **Only `ANTHROPIC_API_KEY` is needed** — no Gmail required.

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # paste your ANTHROPIC_API_KEY

python -m src.main --html              # writes output/trending-<date>.html and opens it
python -m src.main --html --mode detail  # deeper per-repo version
python -m src.main --dry-run           # print Markdown only, no file/email
python -m src.main                     # email it (needs Gmail keys in .env)
```

Prefer to set it once? Put `OUTPUT=html`, `MODE=detail`, `MODEL=...` in `.env` and
just run `python -m src.main`.

---

## 🛠 Troubleshooting

- **No email arrived.** Almost always a wrong `GMAIL_APP_PASSWORD` — it must be a
  16-char **App Password** (not your login password), with 2-Step Verification on.
  Check the Actions run log; the error message names the cause.
- **`command not found` when loading `.env`.** Don't `source .env` — the app loads
  it automatically via `python-dotenv`. Just run the command directly.
- **Trending list is empty.** GitHub changed their HTML. Update the CSS selectors
  in [`src/fetch_trending.py`](src/fetch_trending.py).

---

## What's inside

```
src/
  fetch_trending.py   scrape trending + pull repo READMEs
  summarize.py        Claude turns the list into a digest (digest & detail modes)
  render_email.py     Markdown → styled, email-safe HTML
  send_email.py       Gmail SMTP delivery
  main.py             orchestrates: fetch → summarize → render → deliver
prompts/
  instructions.md     ← the editable "brain": tone, depth, topics, jargon rules
config.yaml           languages, count, defaults
.github/workflows/    daily cron + run/* trigger   ← the automation
```

## Notes

- GitHub has no official trending API, so we parse the public HTML page. If the
  markup changes, the only file to update is `src/fetch_trending.py`.
- `.env` and `output/` are git-ignored — your keys and generated files stay local.
