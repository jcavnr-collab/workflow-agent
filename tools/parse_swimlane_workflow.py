"""
parse_swimlane_workflow.py

Converts a plain-language process description into swim lane workflow JSON,
ready for miro_add_swimlane.py.

Claude assigns each node to a lane (actor/role) and a column index. This script
then calculates pixel x/y coordinates so the caller never deals with layout math.

Usage:
    python tools/parse_swimlane_workflow.py "Describe your process here"

Output:
    Writes .tmp/workflow.json in the extended swim lane format expected by
    miro_add_swimlane.py (direction, lanes with y_start/height, nodes with x/y).
"""

import sys
import json
import os
from pathlib import Path

import anthropic
from dotenv import load_dotenv

load_dotenv()

# Layout constants (must match miro_add_swimlane.py)
LABEL_W = 220       # width of the dark label column on the left (horizontal mode)
LANE_H = 220        # height of each horizontal lane in pixels
COL_W = 260         # horizontal spacing between node columns
NODE_START_X = 380  # x-center of the first column (LABEL_W + some padding)
NODE_OFFSET_Y = 110 # y-center of a node within its lane (lane_y_start + offset)

# Vertical mode constants
LANE_HEADER_H = 60  # header height at top of vertical lane column
LANE_W = 300        # width of each vertical lane column
ROW_H = 160         # vertical spacing between node rows
NODE_START_Y = 160  # y-center of the first row (below header)

# LEANCYCL brand colours — progressively lighter Ice Blue fill, consistent Navy/Teal headers
LANE_COLORS = [
    {"fill": "#e6f4f7", "border": "#4e8fa2", "label_fill": "#1b3d4a"},
    {"fill": "#cce9f0", "border": "#3a7a8e", "label_fill": "#2a6478"},
    {"fill": "#b5dce8", "border": "#4e8fa2", "label_fill": "#1b3d4a"},
    {"fill": "#9fd0e1", "border": "#3a7a8e", "label_fill": "#2a6478"},
    {"fill": "#88c3d9", "border": "#4e8fa2", "label_fill": "#1b3d4a"},
    {"fill": "#d4edf3", "border": "#3a7a8e", "label_fill": "#2a6478"},
]

SYSTEM_PROMPT = """You are a workflow architect. Convert a process description into structured JSON for a horizontal swim lane diagram.

Identify the distinct actors or roles involved (2–5 lanes). Assign each step to the actor who performs it.

Output ONLY valid JSON — no markdown fences, no explanation:

{
  "title": "Short Descriptive Title",
  "lanes": [
    {"id": "lane_id", "label": "Actor Name"}
  ],
  "nodes": [
    {"id": "1", "label": "Short Label", "type": "start|process|decision|end|end_error", "lane": "lane_id", "col": 0}
  ],
  "edges": [
    {"from": "1", "to": "2"},
    {"from": "3", "to": "4", "label": "Yes"}
  ]
}

Rules:
- "col" is a zero-based integer representing the step's horizontal position (left to right). Nodes in different lanes can share the same col if they happen at the same stage.
- Every workflow must start with exactly one "start" node and end with at least one "end" or "end_error" node.
- Decision nodes must have exactly two outgoing edges with labels (e.g. "Yes"/"No", "Pass"/"Fail", "Approved"/"Rejected").
- Keep labels short (3–6 words). Use \\n for a line break if needed.
- Number node IDs sequentially starting from "1".
- Use 2–5 lanes. If the process has no clear actor separation, use department/phase names.
"""


def parse(description: str, direction: str = "horizontal") -> dict:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": description}],
    )

    raw = message.content[0].text.strip()
    # Strip markdown fences if the model wraps the JSON
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    intermediate = json.loads(raw)
    return _layout(intermediate, direction=direction)


def _layout(data: dict, direction: str = "horizontal") -> dict:
    """
    Convert lane+col node positions into absolute x/y pixel coordinates and
    add lane geometry. Supports "horizontal" (lanes as rows) and "vertical"
    (lanes as columns).
    """
    lanes_raw = data["lanes"]
    nodes_raw = data["nodes"]

    lane_index = {lane["id"]: i for i, lane in enumerate(lanes_raw)}

    if direction == "vertical":
        lanes = []
        for i, lane in enumerate(lanes_raw):
            color = LANE_COLORS[i % len(LANE_COLORS)]
            lanes.append({
                "id": lane["id"],
                "label": lane["label"],
                "x": i * LANE_W,
                "width": LANE_W,
                **color,
            })

        nodes = []
        for node in nodes_raw:
            lane_idx = lane_index.get(node.get("lane", lanes_raw[0]["id"]), 0)
            col = node.get("col", 0)
            x = lane_idx * LANE_W + LANE_W / 2
            y = NODE_START_Y + col * ROW_H
            nodes.append({
                "id": node["id"],
                "label": node["label"],
                "type": node["type"],
                "x": x,
                "y": y,
            })
    else:
        lanes = []
        for i, lane in enumerate(lanes_raw):
            color = LANE_COLORS[i % len(LANE_COLORS)]
            lanes.append({
                "id": lane["id"],
                "label": lane["label"],
                "y_start": i * LANE_H,
                "height": LANE_H,
                **color,
            })

        nodes = []
        for node in nodes_raw:
            lane_idx = lane_index.get(node.get("lane", lanes_raw[0]["id"]), 0)
            col = node.get("col", 0)
            x = NODE_START_X + col * COL_W
            y = lane_idx * LANE_H + NODE_OFFSET_Y
            nodes.append({
                "id": node["id"],
                "label": node["label"],
                "type": node["type"],
                "x": x,
                "y": y,
            })

    return {
        "title": data.get("title", "Workflow Diagram"),
        "direction": direction,
        "lanes": lanes,
        "nodes": nodes,
        "edges": data.get("edges", []),
    }


def convert_direction(workflow: dict, new_direction: str) -> dict:
    """
    Re-layout an existing rendered workflow JSON into a different direction.
    Strips rendered x/y/geometry, rebuilds lane+col assignments from node order,
    then calls _layout() with the new direction.
    """
    lanes_rendered = workflow.get("lanes", [])
    nodes_rendered = workflow.get("nodes", [])
    edges = workflow.get("edges", [])

    # Rebuild lane lookup from rendered lanes (they have id + label)
    lane_ids = [l["id"] for l in lanes_rendered] if lanes_rendered else []

    # For vertical→horizontal or horizontal→vertical, we need lane+col per node.
    # We recover "col" by sorting nodes that share a lane by their current
    # dominant axis (x for horizontal, y for vertical).
    current_direction = workflow.get("direction", "horizontal")

    # Group nodes by lane
    lane_nodes: dict = {lid: [] for lid in lane_ids}
    unassigned = []
    for node in nodes_rendered:
        # Try to recover lane from original data; fall back to closest lane
        assigned = False
        if current_direction == "horizontal":
            # Lane is determined by y range: y_start <= y < y_start + height
            for lane in lanes_rendered:
                if lane.get("y_start", 0) <= node["y"] < lane.get("y_start", 0) + lane.get("height", LANE_H):
                    lane_nodes[lane["id"]].append(node)
                    assigned = True
                    break
        else:
            # Vertical: lane is determined by x range
            for lane in lanes_rendered:
                lx = lane.get("x", 0)
                if lx <= node["x"] < lx + lane.get("width", LANE_W):
                    lane_nodes[lane["id"]].append(node)
                    assigned = True
                    break
        if not assigned:
            unassigned.append(node)

    # Assign col = rank within the dominant sort axis
    sort_key = "x" if current_direction == "horizontal" else "y"
    rebuilt_nodes = []
    for lid in lane_ids:
        sorted_nodes = sorted(lane_nodes.get(lid, []), key=lambda n: n[sort_key])
        for col, node in enumerate(sorted_nodes):
            rebuilt_nodes.append({
                "id": node["id"],
                "label": node["label"],
                "type": node["type"],
                "lane": lid,
                "col": col,
            })
    for node in unassigned:
        rebuilt_nodes.append({
            "id": node["id"],
            "label": node["label"],
            "type": node["type"],
            "lane": lane_ids[0] if lane_ids else "lane0",
            "col": 0,
        })

    # Rebuild minimal lane list for _layout
    lanes_minimal = [{"id": l["id"], "label": l["label"]} for l in lanes_rendered]

    intermediate = {
        "title": workflow.get("title", "Workflow Diagram"),
        "lanes": lanes_minimal,
        "nodes": rebuilt_nodes,
        "edges": edges,
    }
    return _layout(intermediate, direction=new_direction)


def main():
    if len(sys.argv) < 2:
        print("Usage: python tools/parse_swimlane_workflow.py \"<process description>\"")
        print("       python tools/parse_swimlane_workflow.py --convert-direction vertical|horizontal")
        sys.exit(1)

    output_path = Path(".tmp/workflow.json")

    if sys.argv[1] == "--convert-direction":
        if len(sys.argv) < 3:
            print("Usage: --convert-direction vertical|horizontal")
            sys.exit(1)
        new_direction = sys.argv[2]
        existing = json.loads(output_path.read_text())
        workflow = convert_direction(existing, new_direction)
        print(f"Converted direction to: {new_direction}")
    else:
        description = sys.argv[1]
        direction = "horizontal"
        if "--direction" in sys.argv:
            idx = sys.argv.index("--direction")
            if idx + 1 < len(sys.argv):
                direction = sys.argv[idx + 1]
        print(f"Parsing swim lane workflow ({direction}): {description[:80]}...")
        workflow = parse(description, direction=direction)

    output_path.parent.mkdir(exist_ok=True)
    output_path.write_text(json.dumps(workflow, indent=2))

    lane_count = len(workflow["lanes"])
    node_count = len(workflow["nodes"])
    edge_count = len(workflow["edges"])
    print(f"Saved: {lane_count} lanes, {node_count} nodes, {edge_count} edges → {output_path}")
    return workflow


if __name__ == "__main__":
    main()
