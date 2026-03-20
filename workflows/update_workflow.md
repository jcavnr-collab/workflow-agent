# Workflow: Update Workflow (Change Requests)

## Objective
Apply user-requested changes to an existing Miro board workflow without
rebuilding from scratch.

## Prerequisites
- `.tmp/workflow.json` — current workflow state
- `.tmp/board_info.json` — current board ID and node ID map
- The Miro board must already exist and have been rendered

## Steps

### 1. Understand the Change Request
Parse what the user wants. Common change types:
- **Add a step**: "Add an approval step between X and Y"
- **Remove a step**: "Remove the staging deploy step"
- **Rename a step**: "Rename 'Run Tests' to 'Unit + Integration Tests'"
- **Change a decision label**: "Label the Yes branch 'Tests Pass' and No as 'Tests Fail'"
- **Change node type**: "Make the 'Review?' step a decision node"

If the request is ambiguous (e.g., "add error handling"), ask: "Where in the
flow should the error step be added, and what should it connect to?"

### 2. Apply the Changes
```
python tools/miro_update_workflow.py "<change request in plain English>"
```

Claude will interpret the request and output a structured change list, then
apply it to both the Miro board and the local `.tmp/workflow.json`.

### 3. Confirm with the User
After applying changes, share the board URL again and ask:
"I've updated the workflow — take a look and let me know if it looks right or
if you'd like any more changes."

Repeat this loop until the user approves.

### 4. When Done
Proceed to `workflows/export_and_deliver.md`.

## Edge Cases
- **Node not found**: If `miro_update_workflow.py` can't find a referenced node,
  check `.tmp/workflow.json` for the correct node IDs and re-phrase the request.
- **Complex restructure**: If the user wants to reorder more than 3-4 steps,
  it may be faster to rebuild: run `miro_add_workflow.py` on an updated
  `workflow.json` on a new board rather than patching the existing one.
- **Rate limits**: Miro limits to 100 requests/10s. If you hit a 429 error,
  wait 10 seconds and retry. For large changes, add a 0.1s sleep between API calls.

## Notes
- `.tmp/workflow.json` is the source of truth. After each update it reflects
  the current state. If it gets out of sync with the board, re-render from scratch.
- The `node_id_map` in `.tmp/board_info.json` maps logical IDs to Miro item IDs.
  Never edit this manually.
