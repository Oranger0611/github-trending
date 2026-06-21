"""Render the Markdown digest into a clean, email-friendly HTML document."""

from __future__ import annotations

import markdown

_CSS = """
  body { margin:0; padding:0; background:#f6f8fa; }
  .wrap { max-width:680px; margin:0 auto; padding:24px 16px;
          font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
          color:#1f2328; line-height:1.55; }
  .card { background:#ffffff; border:1px solid #d0d7de; border-radius:12px;
          padding:24px 28px; }
  h1 { font-size:20px; margin:0 0 4px; }
  h2 { font-size:18px; margin:28px 0 8px; border-bottom:1px solid #d8dee4; padding-bottom:6px; }
  h3 { font-size:16px; margin:22px 0 4px; }
  a { color:#0969da; text-decoration:none; }
  a:hover { text-decoration:underline; }
  p { margin:6px 0; }
  code { background:#eff1f3; padding:1px 5px; border-radius:5px; font-size:85%; }
  .meta { color:#636c76; font-size:13px; margin-top:24px; text-align:center; }
"""


def render_html(markdown_body: str, title: str) -> str:
    body_html = markdown.markdown(
        markdown_body, extensions=["extra", "sane_lists", "nl2br"]
    )
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>{_CSS}</style></head>
<body><div class="wrap">
  <div class="card">
    <h1>{title}</h1>
    {body_html}
  </div>
  <p class="meta">Sent automatically by your GitHub Trending digest ·
     edit <code>prompts/instructions.md</code> to change the style.</p>
</div></body></html>"""
