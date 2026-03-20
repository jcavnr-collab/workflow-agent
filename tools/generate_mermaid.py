"""
generate_mermaid.py

Converts .tmp/workflow.json into a Mermaid flowchart and saves it to
.tmp/workflow.mmd. Works with both basic and swim lane workflow JSON.

Usage:
    python tools/generate_mermaid.py

Output:
    .tmp/workflow.mmd   — Mermaid flowchart file, ready to paste into any
                          Mermaid-compatible viewer (GitHub, VS Code, Notion, etc.)
"""

import json
from pathlib import Path


SHAPE = {
    "start":     ("([", "])"),
    "end":       ("([", "])"),
    "end_error": ("([", "])"),
    "decision":  ("{",  "}"),
    "process":   ("[",  "]"),
}


def _safe_label(label: str) -> str:
    """Escape double quotes and replace newlines for Mermaid node labels."""
    return label.replace('"', "#quot;").replace("\n", "<br/>")


def to_mermaid(workflow: dict) -> str:
    direction = workflow.get("direction", "horizontal")
    # Map swim lane direction to Mermaid flow direction
    flow_dir = "LR" if direction == "horizontal" else "TD"

    lines = [f"flowchart {flow_dir}"]

    # Subgraph per lane (if lanes exist)
    lanes = workflow.get("lanes", [])
    nodes = workflow.get("nodes", [])
    edges = workflow.get("edges", [])

    if lanes:
        # Build a node-id → lane-label lookup from x/y positions
        # For horizontal: lane determined by y range; for vertical: by x range
        lane_h = 220  # must match parse_swimlane_workflow.py LANE_H
        lane_w = 300  # must match LANE_W

        def lane_for_node(node):
            for lane in lanes:
                if direction == "horizontal":
                    y_start = lane.get("y_start", 0)
                    if y_start <= node["y"] < y_start + lane.get("height", lane_h):
                        return lane
                else:
                    x_start = lane.get("x", 0)
                    if x_start <= node["x"] < x_start + lane.get("width", lane_w):
                        return lane
            return lanes[0]

        # Group nodes by lane (preserve order)
        from collections import defaultdict
        lane_nodes = defaultdict(list)
        node_map = {n["id"]: n for n in nodes}
        for node in nodes:
            lane = lane_for_node(node)
            lane_nodes[lane["id"]].append(node)

        # Emit subgraphs
        for lane in lanes:
            safe_id = lane["id"].replace(" ", "_")
            lines.append(f'    subgraph {safe_id}["{lane["label"]}"]')
            for node in lane_nodes.get(lane["id"], []):
                open_b, close_b = SHAPE.get(node["type"], ("[", "]"))
                label = _safe_label(node["label"])
                lines.append(f'        {node["id"]}{open_b}"{label}"{close_b}')
            lines.append("    end")
    else:
        # No lanes — flat node list
        for node in nodes:
            open_b, close_b = SHAPE.get(node["type"], ("[", "]"))
            label = _safe_label(node["label"])
            lines.append(f'    {node["id"]}{open_b}"{label}"{close_b}')

    lines.append("")

    # Edges
    for edge in edges:
        label = edge.get("label", "")
        if label:
            lines.append(f'    {edge["from"]} -->|"{label}"| {edge["to"]}')
        else:
            lines.append(f'    {edge["from"]} --> {edge["to"]}')

    # Style end_error nodes red
    error_nodes = [n["id"] for n in nodes if n.get("type") == "end_error"]
    if error_nodes:
        lines.append("")
        for nid in error_nodes:
            lines.append(f"    style {nid} fill:#e74c3c,color:#fff")

    return "\n".join(lines) + "\n"


def main():
    workflow = json.loads(Path(".tmp/workflow.json").read_text())
    mermaid = to_mermaid(workflow)

    out = Path(".tmp/workflow.mmd")
    out.parent.mkdir(exist_ok=True)
    out.write_text(mermaid)

    print(f"Mermaid file saved to {out}")
    return str(out)


if __name__ == "__main__":
    main()
