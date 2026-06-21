"""Send the digest via Gmail SMTP.

Requires a Gmail *App Password* (not your normal password):
  https://myaccount.google.com/apppasswords
Set GMAIL_USER and GMAIL_APP_PASSWORD in the environment.
"""

from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465  # SSL


def send_email(subject: str, html_body: str, text_fallback: str, recipients: list[str]) -> None:
    user = os.environ["GMAIL_USER"]
    password = os.environ["GMAIL_APP_PASSWORD"]

    if not recipients:
        recipients = [user]  # send to self by default

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = ", ".join(recipients)
    msg.set_content(text_fallback)              # plain-text fallback
    msg.add_alternative(html_body, subtype="html")

    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
        server.login(user, password)
        server.send_message(msg)

    print(f"Sent '{subject}' to {', '.join(recipients)}")
