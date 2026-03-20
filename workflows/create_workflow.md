# Workflow: Create Business Process Workflow

## Objective
Convert a plain-language description of a technical or business process into a
visual workflow diagram on a Miro board, ready for review and iteration.

## Required Inputs
- A clear process description from the user (one paragraph minimum)
- `.env` with `MIRO_ACCESS_TOKEN` and `ANTHROPIC_API_KEY`

## Steps

### 1. Gather the Process Description
Ask the user to describe the process. Prompt for:
- What triggers the process (start event)?
- What are the main steps in order?
- Where are the decision points (yes/no branches)?
- What are the success and failure outcomes?

If the description is vague, ask clarifying questions before proceeding.

### 2. Parse the Description into Structured JSON
```
python tools/parse_workflow.py "<process description>"
```
Output: `.tmp/workflow.json`

Review the JSON for accuracy — check node types, labels, and edge connections.
If something looks wrong, re-run with a more detailed description.

### 3. Create the Miro Board
```
python tools/miro_create_board.py "<workflow title>"
```
Output: `.tmp/board_info.json` with `board_id` and `board_url`

### 4. Render the Workflow onto the Board
```
python tools/miro_add_workflow.py
```
Reads `.tmp/workflow.json` and `.tmp/board_info.json`.
Adds all shapes and connectors to the Miro board.

### 5. Share the Board Link with the User
Share the `board_url` from `.tmp/board_info.json` so the user can view the board.
Tell them: "Open the link to review your workflow. Let me know what changes you'd like."

### 6. Handle Change Requests
See `workflows/update_workflow.md` for change request handling.

### 7. Export and Deliver
When the user approves the workflow, see `workflows/export_and_deliver.md`.

## Edge Cases
- **Miro auth failure (401)**: Token may be expired. Ask user to regenerate at
  https://miro.com/app/settings/user-profile/apps and update `.env`.
- **Parse produces wrong structure**: Re-run `parse_workflow.py` with more detail.
  If Claude misidentifies a step as a decision node, describe that step more explicitly.
- **Board creation fails**: Check that the Miro app has `boards:write` scope.
- **Nodes overlap on board**: The auto-layout is a simple BFS grid. For complex
  branching diagrams, manually rearrange in Miro after rendering.

## Notes
- The Miro free plan supports board creation and shape/connector API calls.
- PNG export via API requires a Business or Enterprise plan. See `workflows/export_and_deliver.md`.
- Keep workflow titles short (under 50 chars) — they appear in the Miro dashboard.
