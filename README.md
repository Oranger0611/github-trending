# 🔥 GitHub Trending Digest

**A daily email that explains what's trending on GitHub — in plain English, no jargon.**

![Python](https://img.shields.io/badge/python-3.12-blue)
![Runs on](https://img.shields.io/badge/runs%20on-GitHub%20Actions-black)
![LLM](https://img.shields.io/badge/summaries-Claude-orange)
![Cost](https://img.shields.io/badge/cost-~%240.03–0.10%2Fday-green)

Every morning it scrapes [github.com/trending](https://github.com/trending), asks
**Claude** to turn the raw list into a readable digest, and either **emails it to
you** or **saves it as a local HTML file**. It runs free on **GitHub Actions** —
or entirely on your laptop with no email setup at all.

[Quickstart](#-get-started-60-seconds) ·
[How it works](#-how-it-works) ·
[Configuration](#%EF%B8%8F-configuration) ·
[Customize the writing](#%EF%B8%8F-customize-the-writing) ·
[Cost](#-cost) ·
[Deploy to GitHub Actions](#-deploy-to-github-actions)

---

## What it does

- **Scrapes GitHub Trending** for the day (any language, or all languages).
- **Reads each repo's README** and summarizes the substance — not just the tagline.
- **Explains it for humans** — every acronym is translated into a concrete benefit; each repo gets a 3-second "hook" plus skimmable bullets.
- **Two delivery options** — email via Gmail, or a local HTML file you open in your browser.
- **Two depth modes** — a fast single-call `digest`, or a per-repo `detail` deep dive.
- **You own the voice** — a single plain-text prompt file controls tone, depth, and which topics get explained in detail.
- **Three ways to trigger** — daily cron, a manual `run/*` branch push, or just running it locally.

---

## 🏗 How it works

```
                  ┌──────────────────────┐
   daily cron ──► │   src/fetch_trending │  scrape github.com/trending
   or `--html`    │                      │  + pull each repo's README
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
              ┌──────────────┴──────────────┐
              ▼                             ▼
     src/send_email (Gmail)        output/trending-<date>.html
        → your inbox                  → opens in your browser
```

---

## 🚀 Get started (60 seconds)

No GitHub account or email setup required for the local version — you only need an
[Anthropic API key](https://console.anthropic.com/settings/keys).

```bash
# 1. Install
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Configure — only the API key is required for local HTML mode
cp .env.example .env        # then paste your ANTHROPIC_API_KEY

# 3. Run — writes output/trending-<date>.html and opens it in your browser
python -m src.main --html
```

That's it. Want the deeper per-repo version?

```bash
python -m src.main --html --mode detail
```

---

## Three ways to run

| You want… | Command / setup | Needs |
|---|---|---|
| **See it now, locally** | `python -m src.main --html` | Anthropic key only |
| **Email it to yourself locally** | `python -m src.main` | Anthropic key + Gmail |
| **Fully automated daily email** | [GitHub Actions](#-deploy-to-github-actions) | repo secrets |

All three share the same fetch → summarize → render core.

---

## ⚙️ Configuration

Set behavior in **`.env`** (local) or **`config.yaml`** (committed defaults). CLI
flags win for one-off overrides.

> **Precedence:** CLI flag → `.env` / env var → `config.yaml` → built-in default.

### `.env` (local runs)

```dotenv
ANTHROPIC_API_KEY=sk-ant-...     # required

OUTPUT=html                      # html = local file | email = send via Gmail
MODE=digest                      # digest = one call for all | detail = per-repo deep dive
MODEL=claude-sonnet-4-6          # see "Picking a model" below

# Only when OUTPUT=html:
# OUTPUT_PATH=/Users/you/Desktop/trending.html
# OPEN_BROWSER=false

# Only when OUTPUT=email:
GMAIL_USER=you@gmail.com
GMAIL_APP_PASSWORD=abcd efgh ijkl mnop   # 16-char App Password, not your login password
MAIL_TO=you@gmail.com                    # optional; defaults to GMAIL_USER
```

### `config.yaml` (languages, count, defaults)

```yaml
languages: [""]        # "" = all; add "python", "rust", etc.
since: daily           # daily | weekly | monthly
max_repos: 12
include_readme: true   # pull READMEs for deeper summaries
output: email          # default delivery (the cron uses this)
mode: digest
model: claude-sonnet-4-6
```

### CLI flags

```bash
python -m src.main --html                  # force local HTML
python -m src.main --mode detail           # per-repo deep dive
python -m src.main --model claude-opus-4-8 # override the model
python -m src.main --out ~/x.html --no-open
python -m src.main --dry-run               # print Markdown, no file/email
```

### Picking a model

| Model | Best for | Relative cost |
|---|---|---|
| `claude-opus-4-8` | Highest quality, follows formatting rules best | $$$ |
| `claude-sonnet-4-6` | Great daily default | $ |
| `claude-haiku-4-5-20251001` | Fastest & cheapest | ¢ |

---

## ✍️ Customize the writing

The entire voice of the digest lives in **[`prompts/instructions.md`](prompts/instructions.md)** —
plain English, no code. Edit it to change anything:

- **More / less detail** — adjust the length rules.
- **Explain certain topics deeply** — add lines under *"Topics I want explained in DETAIL"* (e.g. `Rust async`, `databases`, `LLM agents`).
- **Keep boring topics short** — add lines under *"Topics to keep SHORT or skip"*.

The prompt already enforces readability rules: **no naked jargon** (every acronym
is translated into a benefit), a **3-second hook** per repo, and **bullets instead
of walls of text**.

> Like a one-off tweak? Push a `run/<name>` branch with your edited prompt and it
> runs immediately with that version — see [Special mode](#special-mode-on-demand).

---

## 💰 Cost

This is cheap to run. The only paid piece is the Claude API call(s) that write the
digest — **roughly `$0.03–0.10` per day**.

| What | Cost |
|---|---|
| **Claude summarization** | **~$0.03–0.10 per run/day** (varies by model & mode) |
| GitHub Trending scrape | Free |
| Reading repo READMEs (GitHub API) | Free |
| GitHub Actions (daily cron) | Free (well within the free tier) |
| Gmail sending | Free |

Notes:
- `digest` mode is one Claude call per day → toward the **low** end (~$0.03).
- `detail` mode is one call **per repo** → toward the **high** end (~$0.10), and more with `claude-opus-4-8`.
- Lower the cost further by reducing `max_repos`, trimming `readme_chars`, or using `claude-haiku-4-5-20251001`.

At ~$0.03–0.10/day, a full month of daily digests runs about **$1–3**.

---

## Two automated modes

**Default mode — automatic, every day.** The cron runs on `main` and uses the
prompt committed there. You do nothing.

### Special mode (on demand)

Push a branch whose name starts with `run/` to trigger a one-off digest *now*,
using **that branch's** prompt:

```bash
git checkout -b run/deep-dive-rust
# edit prompts/instructions.md however you like
git commit -am "explain rust repos in depth today"
git push -u origin run/deep-dive-rust   # ← this push triggers a run
```

The email subject is tagged with the branch name (e.g.
`[run/deep-dive-rust] 🔥 GitHub Trending — …`) so you can spot special runs. Happy
with the changes long-term? Merge the branch into `main` to make them the new default.

---

## 🤖 Deploy to GitHub Actions

1. **Create a repo** at <https://github.com/new> and push:
   ```bash
   git remote add origin https://github.com/<you>/github-trending.git
   git branch -M main && git push -u origin main
   ```
2. **Add secrets** — repo → *Settings → Secrets and variables → Actions*:

   | Secret | Value |
   |---|---|
   | `ANTHROPIC_API_KEY` | <https://console.anthropic.com/settings/keys> |
   | `GMAIL_USER` | your Gmail address |
   | `GMAIL_APP_PASSWORD` | App Password — <https://myaccount.google.com/apppasswords> (needs 2FA) |
   | `MAIL_TO` | *(optional)* recipient; defaults to yourself |

   Optional repo **Variables** (`vars`): `MODEL`, `MODE`, `OUTPUT`.
3. **Test it now** — *Actions → Daily GitHub Trending Digest → Run workflow*. You
   should get the email within a minute.

The schedule lives in
[`.github/workflows/daily-trending.yml`](.github/workflows/daily-trending.yml):
`00:00 UTC` daily (`07:00` Vietnam). Change the `cron` with
[crontab.guru](https://crontab.guru). The cron always emails, regardless of your
local `OUTPUT` setting.

---

## 🛠 Troubleshooting

- **No email arrived.** `--dry-run` and `--html` never send. To email, run
  `python -m src.main` with `OUTPUT=email`. If it still fails, the error message
  names the cause — almost always a wrong `GMAIL_APP_PASSWORD` (it must be a
  16-char **App Password**, not your login password, and 2FA must be on).
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
.github/workflows/    daily cron + run/* trigger
```

## Notes

- GitHub has no official trending API, so we parse the public HTML page. If the
  markup changes, the only file to update is `src/fetch_trending.py`.
- `.env` and `output/` are git-ignored — your keys and generated files stay local.
