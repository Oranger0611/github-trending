# 🔥 GitHub Trending — Daily Email Digest

Every morning, this project scrapes the [GitHub Trending](https://github.com/trending)
page, asks **Claude** to turn it into a readable digest, and emails it to you via
**Gmail**. It runs automatically on **GitHub Actions** — no server needed.

The best part: you control *how* repos are explained by editing a single prompt
file. Want AI/agent repos explained in depth but crypto kept to one line? Just
say so in [`prompts/instructions.md`](prompts/instructions.md).

## How it works

```
GitHub Actions (daily cron)
  └─ src/fetch_trending.py   scrape github.com/trending
      └─ src/summarize.py     Claude writes the digest using prompts/instructions.md
          └─ src/render_email.py   Markdown → styled HTML
              └─ src/send_email.py  Gmail SMTP → your inbox
```

## Just want it locally? (no GitHub Actions, no email)

If you don't want to set up Actions or Gmail at all, run it on your machine and
read the result as an HTML file in your browser. **Only `ANTHROPIC_API_KEY` is
needed** — no Gmail keys.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # fill in ANTHROPIC_API_KEY only

python -m src.main --html              # writes output/trending-<date>.html and opens it
python -m src.main --html --mode detail  # deeper, per-repo version
python -m src.main --html --out ~/Desktop/trending.html --no-open  # custom path, don't auto-open
```

`--html` skips email entirely: it fetches trending, summarizes, and saves a
styled HTML file you can open anytime. Use `--dry-run` instead if you just want
the raw Markdown printed to the terminal.

### Prefer to set it once in `.env`?

Instead of typing flags every time, put your choices in `.env` and just run
`python -m src.main`:

```dotenv
OUTPUT=html      # html = local file (no email) | email = send via Gmail
MODE=detail      # digest = one call for all repos | detail = per-repo deep dive
# OUTPUT_PATH=/Users/you/Desktop/trending.html   # optional custom path
# OPEN_BROWSER=false                             # optional, don't auto-open
```

Precedence everywhere is: **CLI flag → `.env`/env var → `config.yaml` → built-in default.**
So flags still win for one-off overrides. (The GitHub Actions cron ignores `.env`
and always emails.)

## Two ways it runs (automated)

**Default mode — automatic, every day.**
You do nothing. The daily cron runs on `main` and uses the prompt committed there.

**Special mode — on demand with a custom prompt.**
When you want a one-off digest with different instructions, push a branch whose
name starts with `run/`:

```bash
git checkout -b run/deep-dive-rust
# edit prompts/instructions.md however you like
git commit -am "explain rust repos in depth today"
git push -u origin run/deep-dive-rust   # ← this push triggers a run immediately
```

The run uses **that branch's** `prompts/instructions.md`, so your changes apply
right away without touching the daily default. The email subject is tagged with
the branch name (e.g. `[run/deep-dive-rust] 🔥 GitHub Trending — …`) so you can
tell special runs apart in your inbox.

If you decide you want those instructions to become the new daily default, just
merge the branch into `main`.

> You can also hit **Actions → Run workflow** for a manual run on any branch.

## Digest vs. detail mode

| | `digest` (default) | `detail` |
|---|---|---|
| LLM calls | 1 for all repos | 1 **per repo** (+ 1 synthesis) |
| Depth | good overview | reads each README deeply, extracts more |
| Cost/time | cheapest, fastest | ~N× more (N = repo count) |
| Subject tag | none | ` · detail` |

Pick a mode any of these ways (highest priority first):
```bash
python -m src.main --mode detail      # per-run flag
MODE=detail python -m src.main        # env var
# config.yaml:  mode: detail          # persistent default
# GitHub:       Settings → Variables → MODE = detail
```
In `detail` mode each repo + its README is sent to the model on its own, then
once the day's repos are all done the assembled digest is emailed to you.

## ✏️ Customizing the digest (the "fix the prompt" part)

Open **[`prompts/instructions.md`](prompts/instructions.md)** and edit in plain English:

- **More / less detail** — change `concise` to `detailed`.
- **Go deep on topics you care about** — add lines under *"Topics I want explained in DETAIL"* (e.g. `Rust async`, `databases`, `LLM agents`).
- **Keep boring topics short** — add lines under *"Topics to keep SHORT or skip"*.
- **Change the tone, structure, sections** — it's just instructions to the editor.

Non-prompt settings (languages, how many repos, which model) live in
[`config.yaml`](config.yaml).

## Setup

### 1. Get the two credentials

| Credential | Where |
|---|---|
| `ANTHROPIC_API_KEY` | https://console.anthropic.com/settings/keys |
| Gmail **App Password** | https://myaccount.google.com/apppasswords (needs 2-Step Verification on) |

### 2. Run it locally first

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then fill in your keys (the app loads .env automatically)

python -m src.fetch_trending  # scraper only — no keys needed
python -m src.main --dry-run  # prints the digest, sends nothing
python -m src.main            # actually emails it
```

### 3. Automate it on GitHub Actions

1. Create a GitHub repo and push this code.
2. In the repo: **Settings → Secrets and variables → Actions → New repository secret**, add:
   - `ANTHROPIC_API_KEY`
   - `GMAIL_USER` (your Gmail address)
   - `GMAIL_APP_PASSWORD`
   - `MAIL_TO` *(optional — defaults to sending to yourself)*
3. The workflow in [`.github/workflows/daily-trending.yml`](.github/workflows/daily-trending.yml)
   runs daily at **00:00 UTC** (07:00 Vietnam time). Change the `cron` to retime it
   (use [crontab.guru](https://crontab.guru)).
4. Test it now: **Actions → Daily GitHub Trending Digest → Run workflow**.

## Cost

One Claude call per day summarizing ~12 repos — typically a fraction of a cent
per day with `claude-sonnet-4-6`. Gmail and GitHub Actions are free at this volume.

## Notes

- GitHub has no official trending API, so we parse the public HTML. If GitHub
  changes their markup, update the CSS selectors in
  [`src/fetch_trending.py`](src/fetch_trending.py).
- Switch to `claude-opus-4-8` in `config.yaml` for the highest-quality write-ups.
