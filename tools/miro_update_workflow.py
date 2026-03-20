"""
miro_update_workflow.py

Applies change requests to an existing Miro board workflow.
Reads the current state from .tmp/board_info.json and .tmp/workflow.json,
uses Claude to interpret the change request, then applies targeted updates.

Usage:
    python tools/miro_update_workflow.py "Add a 'Code Review' step between 'Code Push' and 'Run Tests'"

Supported change types:
    - Add a new node (inserts between two existing nodes)
    - Rename a node label
    - Change a node type (e.g., process -> decision)
    - Remove a node and reconnect its neighbors
    - Add or change an edge label
"""

import sys
import json
import os
from pathlib import Path

import requests
import anthropic
from dotenv import load_dotenv

load_dotenv()

MIRO_API = "https://api.miro.com/v2"

SYSTEM_PROMPT = """You are a workflow editor. Given the current workflow JSON and a change request,
output ONLY a JSON object describing the minimal set of changes to apply.

Output format:
{
  "changes": [
    {
      "action": "add_node",
      "node": {"id": "NEW_1", "label": "string", "type": "process|decision|start|end|end_error"},
      "insert_between": {"from": "existing_id", "to": "existing_id"},
      "connect_from": "existing_id",
      "connect_to": "existing_id"
    },
    {
      "action": "rename_node",
      "node_id": "existing_id",
      "new_label": "string"
    },
    {
      "action": "remove_node",
      "node_id": "existing_id"
    },
    {
      "action": "change_edge_label",
      "from": "existing_id",
      "to": "existing_id",
      "new_label": "string"
    }
  ]
}

Rules:
- Use only node IDs that exist in the current workflow (or NEW_1, NEW_2... for new nodes)
- For add_node: use "insert_between" when inserting between two existing nodes; use "connect_from"/"connect_to" when appending or prepending
- Output ONLY the JSON, no explanation or markdown fences
"""


def get_changes(workflow: dict, change_request: str) -> list:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": f"Current workflow:\n{json.dumps(workflow, indent=2)}\n\nChange request: {change_request}"
        }],
    )
    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    result = json.loads(raw)
    return result["changes"]


def update_shape_label(board_id: str, headers: dict, miro_id: str, new_label: str):
    resp = requests.patch(
        f"{MIRO_API}/boards/{board_id}/shapes/{miro_id}",
        headers=headers,
        json={"data": {"content": new_label}},
    )
    resp.raise_for_status()


def delete_item(board_id: str, headers: dict, miro_id: str, item_type: str = "shapes"):
    resp = requests.delete(f"{MIRO_API}/boards/{board_id}/{item_type}/{miro_id}", headers=headers)
    resp.raise_for_status()


def create_shape(board_id: str, headers: dict, label: str, shape: str = "rectangle",
                 fill: str = "#4a90d9", x: float = 0, y: float = 0) -> str:
    payload = {
        "data": {"content": label, "shape": shape},
        "style": {"fillColor": fill, "fontColor": "#ffffff", "fontSize": "14", "borderColor": "#333333"},
        "position": {"x": x, "y": y},
        "geometry": {"width": 200, "height": 80},
    }
    resp = requests.post(f"{MIRO_API}/boards/{board_id}/shapes", headers=headers, json=payload)
    resp.raise_for_status()
    return resp.json()["id"]


def create_connector(board_id: str, headers: dict, from_id: str, to_id: str, label: str = "") -> str:
    payload = {
        "startItem": {"id": from_id},
        "endItem": {"id": to_id},
        "style": {"strokeColor": "#333333", "strokeWidth": "2"},
    }
    if label:
        payload["captions"] = [{"content": label, "position": "50%"}]
    resp = requests.post(f"{MIRO_API}/boards/{board_id}/connectors", headers=headers, json=payload)
    resp.raise_for_status()
    return resp.json()["id"]


def get_connector_id(board_id: str, headers: dict, from_miro: str, to_miro: str) -> str | None:
    resp = requests.get(f"{MIRO_API}/boards/{board_id}/connectors", headers=headers)
    resp.raise_for_status()
    for connector in resp.json().get("data", []):
        start = connector.get("startItem", {}).get("id")
        end = connector.get("endItem", {}).get("id")
        if start == from_miro and end == to_miro:
            return connector["id"]
    return None


def apply_changes(changes: list, workflow: dict, board_info: dict) -> tuple[dict, dict]:
    board_id = board_info["board_id"]
    node_id_map = board_info.get("node_id_map", {})
    headers = {
        "Authorization": f"Bearer {os.environ['MIRO_ACCESS_TOKEN']}",
        "Content-Type": "application/json",
    }

    nodes_by_id = {n["id"]: n for n in workflow["nodes"]}
    # Also index nodes by lowercased label words for fuzzy fallback
    nodes_by_label = {n["label"].lower().replace("\n", " "): n["id"] for n in workflow["nodes"]}

    def resolve_id(raw_id: str) -> str:
        """Return the canonical node ID, falling back to label-based lookup."""
        if raw_id in node_id_map:
            return raw_id
        # Try matching against label (case-insensitive substring)
        raw_lower = raw_id.lower()
        for label, nid in nodes_by_label.items():
            if raw_lower in label or label in raw_lower:
                print(f"  Warning: resolved '{raw_id}' → node {nid} ('{label}') by label match")
                return nid
        raise KeyError(f"Cannot resolve node ID '{raw_id}' — not in node_id_map or labels")

    for change in changes:
        action = change["action"]

        if action == "rename_node":
            node_id = resolve_id(change["node_id"])
            miro_id = node_id_map[node_id]
            update_shape_label(board_id, headers, miro_id, change["new_label"])
            if node_id in nodes_by_id:
                nodes_by_id[node_id]["label"] = change["new_label"]
            print(f"  Renamed node {node_id} -> '{change['new_label']}'")

        elif action == "add_node":
            new_node = change["node"]
            insert = change.get("insert_between")
            connect_from = change.get("connect_from")
            connect_to = change.get("connect_to")

            if insert:
                from_id = resolve_id(insert["from"])
                to_id = resolve_id(insert["to"])
                from_pos = _get_item_position(board_id, headers, node_id_map[from_id])
                to_pos = _get_item_position(board_id, headers, node_id_map[to_id])
                mid_x = (from_pos["x"] + to_pos["x"]) / 2
                mid_y = (from_pos["y"] + to_pos["y"]) / 2

                old_connector_id = get_connector_id(board_id, headers, node_id_map[from_id], node_id_map[to_id])
                if old_connector_id:
                    delete_item(board_id, headers, old_connector_id, "connectors")

                new_miro_id = create_shape(board_id, headers, new_node["label"], x=mid_x, y=mid_y)
                node_id_map[new_node["id"]] = new_miro_id

                create_connector(board_id, headers, node_id_map[from_id], new_miro_id)
                create_connector(board_id, headers, new_miro_id, node_id_map[to_id])

                workflow["nodes"].append(new_node)
                workflow["edges"] = [
                    e for e in workflow["edges"]
                    if not (e["from"] == from_id and e["to"] == to_id)
                ]
                workflow["edges"].append({"from": from_id, "to": new_node["id"]})
                workflow["edges"].append({"from": new_node["id"], "to": to_id})
                print(f"  Added node '{new_node['label']}' between {from_id} and {to_id}")
            else:
                last_node = workflow["nodes"][-1] if workflow["nodes"] else None
                ref_x, ref_y = 0, 0
                if last_node and last_node["id"] in node_id_map:
                    pos = _get_item_position(board_id, headers, node_id_map[last_node["id"]])
                    ref_x, ref_y = pos["x"] + 250, pos["y"]

                new_miro_id = create_shape(board_id, headers, new_node["label"], x=ref_x, y=ref_y)
                node_id_map[new_node["id"]] = new_miro_id
                workflow["nodes"].append(new_node)

                if connect_from:
                    cf_id = resolve_id(connect_from)
                    create_connector(board_id, headers, node_id_map[cf_id], new_miro_id)
                    workflow["edges"].append({"from": cf_id, "to": new_node["id"]})
                if connect_to:
                    ct_id = resolve_id(connect_to)
                    create_connector(board_id, headers, new_miro_id, node_id_map[ct_id])
                    workflow["edges"].append({"from": new_node["id"], "to": ct_id})

                print(f"  Added node '{new_node['label']}'")

        elif action == "remove_node":
            node_id = resolve_id(change["node_id"])
            miro_id = node_id_map[node_id]

            # Find predecessor and successor
            preds = [e["from"] for e in workflow["edges"] if e["to"] == node_id]
            succs = [e["to"] for e in workflow["edges"] if e["from"] == node_id]

            # Remove connectors and shape
            delete_item(board_id, headers, miro_id, "shapes")

            # Reconnect predecessor to successor if simple chain
            if len(preds) == 1 and len(succs) == 1:
                create_connector(board_id, headers, node_id_map[preds[0]], node_id_map[succs[0]])

            # Update workflow data
            workflow["nodes"] = [n for n in workflow["nodes"] if n["id"] != node_id]
            workflow["edges"] = [
                e for e in workflow["edges"]
                if e["from"] != node_id and e["to"] != node_id
            ]
            if len(preds) == 1 and len(succs) == 1:
                workflow["edges"].append({"from": preds[0], "to": succs[0]})
            del node_id_map[node_id]
            print(f"  Removed node {node_id}")

        elif action == "change_edge_label":
            connector_id = get_connector_id(
                board_id, headers,
                node_id_map[resolve_id(change["from"])], node_id_map[resolve_id(change["to"])]
            )
            if connector_id:
                resp = requests.patch(
                    f"{MIRO_API}/boards/{board_id}/connectors/{connector_id}",
                    headers=headers,
                    json={"captions": [{"content": change["new_label"], "position": "50"}]},
                )
                resp.raise_for_status()
                print(f"  Updated edge {change['from']}->{change['to']} label to '{change['new_label']}'")

    board_info["node_id_map"] = node_id_map
    workflow["nodes"] = list({n["id"]: n for n in workflow["nodes"]}.values())
    return workflow, board_info


def _get_item_position(board_id: str, headers: dict, miro_id: str) -> dict:
    resp = requests.get(f"{MIRO_API}/boards/{board_id}/shapes/{miro_id}", headers=headers)
    resp.raise_for_status()
    return resp.json().get("position", {"x": 0, "y": 0})


def main():
    if len(sys.argv) < 2:
        print("Usage: python tools/miro_update_workflow.py \"<change request>\"")
        sys.exit(1)

    change_request = sys.argv[1]
    workflow = json.loads(Path(".tmp/workflow.json").read_text())
    board_info = json.loads(Path(".tmp/board_info.json").read_text())

    print(f"Interpreting change: {change_request}")
    changes = get_changes(workflow, change_request)
    print(f"Applying {len(changes)} change(s)...")

    updated_workflow, updated_board_info = apply_changes(changes, workflow, board_info)

    Path(".tmp/workflow.json").write_text(json.dumps(updated_workflow, indent=2))
    Path(".tmp/board_info.json").write_text(json.dumps(updated_board_info, indent=2))

    print(f"\nDone. View at: {board_info['board_url']}")


if __name__ == "__main__":
    main()
