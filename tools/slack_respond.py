"""
slack_respond.py

Posts the completed workflow to a Slack thread — board link + summary message,
plus the PNG screenshot as a file upload if available.

Usage:
    python tools/slack_respond.py <channel_id> <thread_ts>

Reads:
    .tmp/board_info.json  — board_url, title
    .tmp/workflow.json    — node/edge counts
    .tmp/workflow.png     — uploaded if present

Requirements in .env:
    SLACK_BOT_TOKEN=xoxb-...
"""

import json
import sys
from pathlib import Path

from dotenv import load_dotenv
import os

load_dotenv()


def respond(channel: str, thread_ts: str):
    from slack_sdk import WebClient
    from slack_sdk.errors import SlackApiError

    client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])

    board_info = json.loads(Path(".tmp/board_info.json").read_text())
    workflow = json.loads(Path(".tmp/workflow.json").read_text())

    title = workflow.get("title", "Workflow Diagram")
    node_count = len(workflow.get("nodes", []))
    edge_count = len(workflow.get("edges", []))
    board_url = board_info["board_url"]

    text = (
        f"*{title}* is ready!\n"
        f"• {node_count} steps · {edge_count} connections\n"
        f"• <{board_url}|Open in Miro>"
    )

    client.chat_postMessage(
        channel=channel,
        thread_ts=thread_ts,
        text=text,
        unfurl_links=False,
        unfurl_media=False,
    )
    print(f"Posted message to {channel} (thread {thread_ts})")

    # Upload PNG
    png_path = Path(".tmp/workflow.png")
    if png_path.exists():
        try:
            client.files_upload_v2(
                file=str(png_path),
                filename="workflow.png",
                channel=channel,
                thread_ts=thread_ts,
                initial_comment="",
            )
            print(f"Uploaded {png_path} ({png_path.stat().st_size // 1024}KB)")
        except SlackApiError as e:
            print(f"Warning: PNG upload failed — {e.response['error']}")
    else:
        print("No PNG found at .tmp/workflow.png — skipping PNG upload")

    # Generate and upload Mermaid file
    try:
        import subprocess
        subprocess.run(["python", "tools/generate_mermaid.py"], check=True, capture_output=True)
        mmd_path = Path(".tmp/workflow.mmd")
        if mmd_path.exists():
            client.files_upload_v2(
                file=str(mmd_path),
                filename="workflow.mmd",
                channel=channel,
                thread_ts=thread_ts,
                initial_comment="",
            )
            print(f"Uploaded {mmd_path}")
    except SlackApiError as e:
        print(f"Warning: Mermaid upload failed — {e.response['error']}")
    except Exception as e:
        print(f"Warning: Mermaid generation failed — {e}")


def main():
    if len(sys.argv) != 3:
        print("Usage: python tools/slack_respond.py <channel_id> <thread_ts>")
        sys.exit(1)

    channel = sys.argv[1]
    thread_ts = sys.argv[2]
    respond(channel, thread_ts)


if __name__ == "__main__":
    main()
