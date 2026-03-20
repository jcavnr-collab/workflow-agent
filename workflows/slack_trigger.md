# Workflow: Slack Trigger for Workflow Creation

## Objective
Allow any team member to create a Miro workflow board by @mentioning the bot
in a Slack channel. The bot replies in the same thread with the board link and
a PNG screenshot.

## One-Time Slack App Setup

1. Go to https://api.slack.com/apps → **Create New App** → "From scratch"
2. **Socket Mode** → Enable → Generate App-Level Token (scope: `connections:write`) → save as `SLACK_APP_TOKEN`
3. **OAuth & Permissions → Bot Token Scopes**: add `app_mentions:read`, `chat:write`, `files:write`, `channels:history`
4. **Event Subscriptions** → Enable → Subscribe to bot event: `app_mention`
5. **Install App to Workspace** → copy Bot User OAuth Token → save as `SLACK_BOT_TOKEN`
6. Find your bot's User ID: open Slack → bot's profile → "Copy member ID" → save as `SLACK_BOT_USER_ID`

Add these three variables to `.env`:
```
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...
SLACK_BOT_USER_ID=U0XXXXXXXXX
```

## Starting the Listener

```
python tools/slack_listener.py
```

Keep this terminal open. The listener uses Socket Mode (WebSocket) — no public
URL, port forwarding, or ngrok required. Stop with `Ctrl+C`.

## Trigger Format

In any channel the bot has been invited to:

```
@Miro Workflow Agent describe your business process in plain English here
```

The bot name is set in the Slack app's Basic Information → Display Information.
No code change needed to rename it.

## Pipeline Sequence (automated)

When a mention is received:

1. Bot immediately replies: ":gear: Building your workflow board..."
2. `parse_workflow.py "<description>"` → `.tmp/workflow.json`
3. `miro_create_board.py` → `.tmp/board_info.json`
4. `miro_add_swimlane.py` → renders shapes/connectors on the board
5. `screenshot_board.py` → `.tmp/workflow.png`
6. `slack_respond.py <channel> <thread_ts>` → posts board link + uploads PNG

Total time: ~60 seconds depending on workflow complexity.

## Testing Without a Full Pipeline Run

After any completed pipeline (manual or Slack-triggered), test the respond step
independently:

```
python tools/slack_respond.py C1234567890 1234567890.123456
```

Replace `C1234567890` with a real channel ID and `1234567890.123456` with a
thread timestamp. This confirms Slack credentials and file upload work before
testing the full trigger flow.

## Edge Cases

- **Duplicate events**: Slack occasionally delivers the same event twice. The
  pipeline is idempotent (overwrites `.tmp/` files), so duplicates cause a
  second board to be created. Acceptable for now.

- **Concurrent requests**: Two simultaneous @mentions both write to `.tmp/` and
  will corrupt each other's output. Fix later: use `.tmp/{event_ts}/`
  subdirectories per request. For now, avoid concurrent use.

- **`parse_workflow.py` fails**: Requires `ANTHROPIC_API_KEY` with credit
  balance. If the Anthropic account runs out of credits, the bot will post an
  error message to the thread.

- **Bot not responding**: Confirm the bot is invited to the channel
  (`/invite @Miro Workflow Agent`). Check that `app_mention` event subscription
  is active in the Slack app settings.

- **PNG upload fails with `missing_scope`**: Add `files:write` scope in
  OAuth & Permissions, then reinstall the app to the workspace.

## Notes

- `miro_add_swimlane.py` is used (not `miro_add_workflow.py`) because
  `parse_workflow.py` produces swim lane JSON by default. If a non-swim-lane
  workflow is needed, update step 4 in the pipeline.
- The listener runs as a single process. Restart it after `.env` changes.
