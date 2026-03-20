"""
slack_listener.py

Always-on Socket Mode listener. When a team member @mentions the bot with a
process description, it immediately acknowledges, then runs the full pipeline
in a background thread and posts the result back to the same Slack thread.

Usage:
    python tools/slack_listener.py

Requirements in .env:
    SLACK_BOT_TOKEN=xoxb-...
    SLACK_APP_TOKEN=xapp-...
    SLACK_BOT_USER_ID=U0XXXXXXXXX   # bot's own user ID (to strip from mention)

Trigger format (in Slack):
    @Miro Workflow Agent describe your business process in plain English

Stop with Ctrl+C.
"""

import json
import os
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def strip_mention(text: str) -> str:
    """Remove the leading <@BOTID> mention from the message text."""
    bot_id = os.environ.get("SLACK_BOT_USER_ID", "")
    cleaned = re.sub(r"<@[A-Z0-9]+>", "", text).strip()
    return cleaned


UPDATE_KEYWORDS = (
    "add", "remove", "delete", "rename", "change", "update", "insert",
    "move", "replace", "modify", "edit", "fix", "adjust",
)

DIRECTION_KEYWORDS = {"vertical", "horizontal"}


def is_update_request(text: str) -> bool:
    """Return True if the message looks like a change request on an existing board."""
    if not Path(".tmp/board_info.json").exists():
        return False
    words = {w.lower().strip(".,?!") for w in text.split()}
    return bool(words & set(UPDATE_KEYWORDS))


def detect_preferred_direction(text: str) -> str:
    """Return 'vertical' or 'horizontal' if mentioned in text, else 'horizontal' (default)."""
    words = {w.lower().strip(".,?!") for w in text.split()}
    if "vertical" in words:
        return "vertical"
    if "horizontal" in words:
        return "horizontal"
    return "horizontal"


def detect_direction_change(text: str):
    """
    Return 'vertical' or 'horizontal' if the message is asking to change the
    layout direction of an EXISTING board, else None.
    """
    if not Path(".tmp/workflow.json").exists():
        return None
    words = {w.lower().strip(".,?!") for w in text.split()}
    matched = words & DIRECTION_KEYWORDS
    if not matched:
        return None
    change_words = {"change", "make", "switch", "convert", "turn", "switch"}
    if words & change_words:
        return matched.pop()
    return None


def run_pipeline(description: str, channel: str, thread_ts: str):
    """
    Execute the full workflow pipeline in a background thread.
    Each step is a subprocess call to keep tool contracts unchanged.
    """
    from slack_sdk import WebClient
    from slack_sdk.errors import SlackApiError

    client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])

    def post(msg: str):
        try:
            client.chat_postMessage(
                channel=channel,
                thread_ts=thread_ts,
                text=msg,
            )
        except SlackApiError as e:
            print(f"[slack] post failed: {e.response['error']}")

    try:
        new_direction = detect_direction_change(description)
        if new_direction:
            # --- Direction change: re-layout existing workflow and recreate board ---
            print(f"[pipeline] Direction change requested: {new_direction}")
            steps = [
                (["python", "tools/parse_swimlane_workflow.py", "--convert-direction", new_direction], "Converting layout..."),
                (["python", "tools/miro_create_board.py"], "Creating Miro board..."),
                (["python", "tools/miro_add_swimlane.py"], "Rendering diagram..."),
                (["python", "tools/screenshot_board.py"], "Taking screenshot..."),
            ]
            for cmd, label in steps:
                print(f"[pipeline] {label}")
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    stderr = result.stderr.strip() or result.stdout.strip()
                    raise RuntimeError(f"{label} failed:\n{stderr[-500:]}")

        elif is_update_request(description):
            # --- Update existing board ---
            print(f"[pipeline] Detected update request: {description[:60]}")
            steps = [
                (["python", "tools/miro_update_workflow.py", description], "Applying changes..."),
                (["python", "tools/screenshot_board.py"], "Taking screenshot..."),
            ]
            for cmd, label in steps:
                print(f"[pipeline] {label}")
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    stderr = result.stderr.strip() or result.stdout.strip()
                    raise RuntimeError(f"{label} failed:\n{stderr[-500:]}")
        else:
            # --- Create new board ---
            direction = detect_preferred_direction(description)
            print(f"[pipeline] Parsing swim lane workflow (direction={direction})...")
            result = subprocess.run(
                ["python", "tools/parse_swimlane_workflow.py", description, "--direction", direction],
                capture_output=True, text=True,
            )
            if result.returncode != 0:
                raise RuntimeError(f"Parsing failed:\n{(result.stderr or result.stdout)[-500:]}")

            workflow_title = "Workflow Diagram"
            try:
                workflow_title = json.loads(Path(".tmp/workflow.json").read_text()).get("title", workflow_title)
            except Exception:
                pass

            steps = [
                (["python", "tools/miro_create_board.py", workflow_title], "Creating Miro board..."),
                (["python", "tools/miro_add_swimlane.py"], "Rendering diagram..."),
                (["python", "tools/screenshot_board.py"], "Taking screenshot..."),
            ]
            for cmd, label in steps:
                print(f"[pipeline] {label}")
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    stderr = result.stderr.strip() or result.stdout.strip()
                    raise RuntimeError(f"{label} failed:\n{stderr[-500:]}")

        subprocess.run(
            ["python", "tools/slack_respond.py", channel, thread_ts],
            check=True,
        )

    except Exception as exc:
        print(f"[pipeline] ERROR: {exc}")
        post(f":x: Something went wrong building your workflow:\n```{exc}```")


def handle_event(client, req):
    """Socket Mode event handler — called for every incoming event."""
    from slack_sdk.socket_mode.response import SocketModeResponse

    # Always acknowledge within 3 seconds
    client.send_socket_mode_response(SocketModeResponse(envelope_id=req.envelope_id))

    payload = req.payload
    event = payload.get("event", {})

    if event.get("type") != "app_mention":
        return

    # Ignore bot's own messages
    bot_id = os.environ.get("SLACK_BOT_USER_ID", "")
    if event.get("bot_id") or event.get("user") == bot_id:
        return

    text = event.get("text", "")
    channel = event.get("channel", "")
    thread_ts = event.get("thread_ts") or event.get("ts", "")

    description = strip_mention(text)
    if not description:
        client.web_client.chat_postMessage(
            channel=channel,
            thread_ts=thread_ts,
            text="Hi! Mention me with a process description and I'll build the Miro board. Example:\n> @Miro Workflow Agent describe your process here",
        )
        return

    # Post acknowledgment to thread
    client.web_client.chat_postMessage(
        channel=channel,
        thread_ts=thread_ts,
        text=f":gear: Building your workflow board... I'll reply here when it's ready (usually ~60s).",
    )

    # Run pipeline in background so we don't block the event loop
    t = threading.Thread(
        target=run_pipeline,
        args=(description, channel, thread_ts),
        daemon=True,
    )
    t.start()


def main():
    from slack_sdk.socket_mode import SocketModeClient
    from slack_sdk.web import WebClient

    bot_token = os.environ.get("SLACK_BOT_TOKEN")
    app_token = os.environ.get("SLACK_APP_TOKEN")

    if not bot_token or not app_token:
        print("ERROR: SLACK_BOT_TOKEN and SLACK_APP_TOKEN must be set in .env")
        sys.exit(1)

    web_client = WebClient(token=bot_token)
    socket_client = SocketModeClient(
        app_token=app_token,
        web_client=web_client,
    )

    socket_client.socket_mode_request_listeners.append(handle_event)
    socket_client.connect()

    print("Slack listener connected. Waiting for @mentions...")
    print("Stop with Ctrl+C.\n")

    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        print("\nShutting down.")
        socket_client.close()


if __name__ == "__main__":
    main()
