"""
miro_add_workflow.py

Reads .tmp/workflow.json and .tmp/board_info.json, then renders the workflow
onto the Miro board as shapes and connectors.

Usage:
    python tools/miro_add_workflow.py

Output:
    Updates .tmp/board_info.json with a node_id_map (logical ID -> Miro item ID)
    for use by miro_update_workflow.py.

Node type -> Miro shape mapping:
    start      -> round_rectangle (fill: #1fad5e, green)
    process    -> rectangle       (fill: #4a90d9, blue)
    decision   -> rhombus         (fill: #f5a623, yellow)
    end        -> round_rectangle (fill: #00bcd4, teal)
    end_error  -> round_rectangle (fill: #e74c3c, red)

Layout:
    Nodes are arranged in a vertical top-down flow with 200px spacing.
    Decision branches spread horizontally by 300px.
"""

import json
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

MIRO_API = "https://api.miro.com/v2"

NODE_STYLES = {
    "start":     {"shape": "round_rectangle", "fill": "#1fad5e", "text_color": "#ffffff"},
    "process":   {"shape": "rectangle",       "fill": "#4a90d9", "text_color": "#ffffff"},
    "decision":  {"shape": "rhombus",         "fill": "#f5a623", "text_color": "#000000"},
    "end":       {"shape": "round_rectangle", "fill": "#00bcd4", "text_color": "#ffffff"},
    "end_error": {"shape": "round_rectangle", "fill": "#e74c3c", "text_color": "#ffffff"},
}

NODE_WIDTH = 200
NODE_HEIGHT = 80
H_SPACING = 320
V_SPACING = 180


def compute_positions(nodes: list, edges: list) -> dict:
    """Assign (x, y) positions using a simple top-down BFS layout."""
    # Build adjacency
    children = {n["id"]: [] for n in nodes}
    parents = {n["id"]: [] for n in nodes}
    for e in edges:
        children[e["from"]].append(e["to"])
        parents[e["to"]].append(e["from"])

    # Find root
    root = next(n["id"] for n in nodes if n["type"] == "start")

    # BFS to assign levels
    levels = {}
    queue = [root]
    visited = set()
    level = 0
    while queue:
        next_queue = []
        for node_id in queue:
            if node_id not in visited:
                visited.add(node_id)
                levels[node_id] = level
                next_queue.extend(children[node_id])
        queue = next_queue
        level += 1

    # Group by level
    by_level = {}
    for node_id, lvl in levels.items():
        by_level.setdefault(lvl, []).append(node_id)

    # Assign x/y
    positions = {}
    for lvl, node_ids in by_level.items():
        count = len(node_ids)
        total_width = (count - 1) * H_SPACING
        for i, node_id in enumerate(node_ids):
            x = -total_width / 2 + i * H_SPACING
            y = lvl * V_SPACING
            positions[node_id] = (x, y)

    return positions


def create_shape(board_id: str, headers: dict, node: dict, x: float, y: float) -> str:
    style = NODE_STYLES.get(node["type"], NODE_STYLES["process"])

    payload = {
        "data": {"content": node["label"], "shape": style["shape"]},
        "style": {
            "fillColor": style["fill"],
            "color": style["text_color"],
            "fontSize": "14",
            "borderColor": "#333333",
        },
        "position": {"x": x, "y": y},
        "geometry": {"width": NODE_WIDTH, "height": NODE_HEIGHT},
    }

    resp = requests.post(
        f"{MIRO_API}/boards/{board_id}/shapes",
        headers=headers,
        json=payload,
    )
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

    resp = requests.post(
        f"{MIRO_API}/boards/{board_id}/connectors",
        headers=headers,
        json=payload,
    )
    resp.raise_for_status()
    return resp.json()["id"]


def main():
    workflow = json.loads(Path(".tmp/workflow.json").read_text())
    board_info = json.loads(Path(".tmp/board_info.json").read_text())

    board_id = board_info["board_id"]
    headers = {
        "Authorization": f"Bearer {os.environ['MIRO_ACCESS_TOKEN']}",
        "Content-Type": "application/json",
    }

    print(f"Adding {len(workflow['nodes'])} nodes to board {board_id}...")

    positions = compute_positions(workflow["nodes"], workflow["edges"])

    # Create shapes
    node_id_map = {}  # logical id -> miro item id
    for node in workflow["nodes"]:
        x, y = positions.get(node["id"], (0, 0))
        miro_id = create_shape(board_id, headers, node, x, y)
        node_id_map[node["id"]] = miro_id
        print(f"  Created [{node['type']}] {node['label']} -> {miro_id}")

    # Create connectors
    print(f"Adding {len(workflow['edges'])} connectors...")
    for edge in workflow["edges"]:
        from_miro = node_id_map[edge["from"]]
        to_miro = node_id_map[edge["to"]]
        label = edge.get("label", "")
        create_connector(board_id, headers, from_miro, to_miro, label)
        print(f"  Connected {edge['from']} -> {edge['to']}" + (f" [{label}]" if label else ""))

    # Save node map for future updates
    board_info["node_id_map"] = node_id_map
    Path(".tmp/board_info.json").write_text(json.dumps(board_info, indent=2))

    print(f"\nWorkflow rendered. View at: {board_info['board_url']}")


if __name__ == "__main__":
    main()
