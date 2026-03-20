"""
send_email.py

Sends an email via the Resend API. Used as the final delivery step in
export_and_deliver.md.

Usage:
    python tools/send_email.py                          # reads .tmp/deliver_payload.json
    python tools/send_email.py --test                   # sends a test email to DELIVERY_EMAIL

Reads .tmp/deliver_payload.json (written by deliver_workflow.py) for:
    - to, subject, body, board_url

Requirements:
    RESEND_API_KEY in .env
    DELIVERY_EMAIL in .env
"""

import sys
import json
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

RESEND_API = "https://api.resend.com/emails"

# On Resend free plan, use onboarding@resend.dev as sender until you verify a domain.
# To use your own address, verify it at resend.com/domains or resend.com/emails.
SENDER = os.environ.get("RESEND_SENDER", "WAT Workflow Agent <onboarding@resend.dev>")


def send(to: str, subject: str, body: str, attachment_path: str = None) -> dict:
    headers = {
        "Authorization": f"Bearer {os.environ['RESEND_API_KEY']}",
        "Content-Type": "application/json",
    }
    payload = {
        "from": SENDER,
        "to": [to],
        "subject": subject,
        "text": body,
    }

    if attachment_path and Path(attachment_path).exists():
        import base64
        data = Path(attachment_path).read_bytes()
        filename = Path(attachment_path).name
        payload["attachments"] = [{
            "filename": filename,
            "content": base64.b64encode(data).decode(),
        }]
        print(f"  Attaching {filename} ({len(data) // 1024}KB)")

    resp = requests.post(RESEND_API, headers=headers, json=payload)
    resp.raise_for_status()
    return resp.json()


def main():
    test_mode = "--test" in sys.argv

    if test_mode:
        to = os.environ["DELIVERY_EMAIL"]
        subject = "Test Email — WAT Workflow Agent"
        body = "This is a test email from your WAT Workflow Agent using Resend. If you received this, email delivery is working correctly."
    else:
        payload = json.loads(Path(".tmp/deliver_payload.json").read_text())
        to = payload["to"]
        subject = payload["subject"]
        body = payload["body"]
        attachment_path = payload.get("png_path") if payload.get("png_available") else None

    print(f"Sending email to {to}...")
    result = send(to, subject, body, attachment_path=attachment_path if not test_mode else None)
    print(f"Sent. Message ID: {result.get('id')}")
    return result


if __name__ == "__main__":
    main()
