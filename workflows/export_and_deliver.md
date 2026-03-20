# Workflow: Export and Deliver Workflow

## Objective
Export the finalized Miro workflow as a PNG and deliver it to the user via email
along with the live Miro board link.

## Prerequisites
- User has approved the workflow ("looks good", "that's it", "send it")
- `.tmp/board_info.json` and `.tmp/workflow.json` are current
- `.env` has `DELIVERY_EMAIL` set

## Steps

### 1. Attempt PNG Export
```
python tools/miro_export_png.py
```
Output: `.tmp/export_info.json`

**If export succeeds**: `.tmp/workflow.png` is created (Miro paid plan).
**If export fails (402/403)**: The script logs a manual export instruction.
Inform the user: "Your Miro plan doesn't support API export. I'll send you
the board link. You can export the PNG manually: open the board → Export →
Export to PNG."

### 2. Prepare the Delivery Payload
```
python tools/deliver_workflow.py
```
This prints the email subject, body, and attachment info as JSON to stdout.

### 3. Send the Email via Gmail MCP
Use the Gmail MCP tool (`gmail_create_draft` or send directly) with:
- **To**: value from `DELIVERY_EMAIL` in `.env`
- **Subject**: from the payload
- **Body**: from the payload (includes board URL)
- **Attachment**: `.tmp/workflow.png` if `png_available` is true

### 4. Confirm Delivery
Tell the user: "Done! I've sent the workflow to [email]. The Miro board is
live at [board_url] — you can continue editing it anytime."

## Edge Cases
- **No DELIVERY_EMAIL set**: Ask the user for their email before proceeding.
- **Gmail MCP unavailable**: Share the board URL and PNG path directly in chat
  so the user can access them manually.
- **PNG export not available**: Deliver board URL only and note the manual
  export option. Do not block delivery on the PNG.

## Notes
- The Miro board remains live and editable after delivery.
- `.tmp/` files can be deleted after delivery — they're regeneratable.
- If the user wants a second iteration after delivery, start from
  `workflows/update_workflow.md` (the board still exists).
