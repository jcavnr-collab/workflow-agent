"""
miro_add_swimlane.py

Renders a swim lane workflow onto a Miro board. Reads .tmp/workflow.json
(extended format with "lanes" array) and .tmp/board_info.json.

Extended workflow.json format:
{
  "title": "...",
  "lanes": [
    {"id": "pm", "label": "Product Manager", "x": 0, "width": 380, "fill": "#dbedf9", "border": "#7ab8d9"}
  ],
  "nodes": [
    {"id": "1", "label": "...", "type": "start|process|decision|end|end_error", "x": 190, "y": 120}
  ],
  "edges": [...]
}

Nodes use absolute x/y coordinates instead of BFS layout.
Lanes are rendered as semi-transparent background rectangles with header labels.

Usage:
    python tools/miro_add_swimlane.py
"""

import json
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

MIRO_API = "https://api.miro.com/v2"

# LEANCYCL brand colours
BRAND_NAVY  = "#1b3d4a"
BRAND_TEAL  = "#4e8fa2"
BRAND_BTN   = "#3a7a8e"
BRAND_ICE   = "#e6f4f7"
BRAND_WHITE = "#ffffff"

NODE_STYLES = {
    "start":     {"shape": "round_rectangle", "fill": BRAND_TEAL,  "color": BRAND_WHITE},
    "process":   {"shape": "rectangle",        "fill": BRAND_BTN,   "color": BRAND_WHITE},
    "decision":  {"shape": "rhombus",          "fill": "#f5a623",   "color": "#000000"},
    "end":       {"shape": "round_rectangle",  "fill": BRAND_NAVY,  "color": BRAND_WHITE},
    "end_error": {"shape": "round_rectangle",  "fill": "#c0392b",   "color": BRAND_WHITE},
}

NODE_W = 220
NODE_H = 72
LANE_HEADER_H = 60
BRAND_HEADER_H = 80      # height of the branded title bar above the diagram
RATE_LIMIT_PAUSE = 0.12  # seconds between API calls to avoid 429s

LOGO_PATH = Path("brand/whitelogo.png")


def post(board_id, path, headers, body):
    time.sleep(RATE_LIMIT_PAUSE)
    resp = requests.post(f"{MIRO_API}/boards/{board_id}/{path}", headers=headers, json=body)
    resp.raise_for_status()
    return resp.json()


LABEL_W = 220   # width of the left-side label column in horizontal mode


def add_brand_header(board_id, headers, title, total_width, y_top):
    """
    Adds a branded title bar above the diagram.
    - Deep Navy background spanning the full diagram width
    - Teal accent stripe on the left
    - Workflow title as white text
    """
    center_x = total_width / 2
    center_y = y_top - BRAND_HEADER_H / 2

    # Navy background
    post(board_id, "shapes", headers, {
        "data": {"content": "", "shape": "rectangle"},
        "style": {
            "fillColor": BRAND_NAVY,
            "fillOpacity": "1.0",
            "borderColor": BRAND_NAVY,
            "borderWidth": "1.0",
        },
        "position": {"x": center_x, "y": center_y},
        "geometry": {"width": total_width, "height": BRAND_HEADER_H},
    })

    # Teal accent stripe (left edge)
    post(board_id, "shapes", headers, {
        "data": {"content": "", "shape": "rectangle"},
        "style": {
            "fillColor": BRAND_TEAL,
            "fillOpacity": "1.0",
            "borderColor": BRAND_TEAL,
            "borderWidth": "1.0",
        },
        "position": {"x": 6, "y": center_y},
        "geometry": {"width": 12, "height": BRAND_HEADER_H},
    })

    # Title text
    post(board_id, "shapes", headers, {
        "data": {"content": title, "shape": "rectangle"},
        "style": {
            "fillColor": BRAND_NAVY,
            "fillOpacity": "1.0",
            "borderColor": BRAND_NAVY,
            "borderWidth": "1.0",
            "fontSize": "22",
            "color": BRAND_WHITE,
            "textAlign": "left",
            "textAlignVertical": "middle",
        },
        "position": {"x": center_x + 40, "y": center_y},
        "geometry": {"width": total_width - 160, "height": BRAND_HEADER_H},
    })

    print("  Brand header added.")


def upload_logo(board_id, auth_headers, y_top, total_width):
    """
    Uploads whitelogo.png as a small icon in the right end of the brand header.
    Resizes to 50x50px before uploading (Miro ignores geometry in multipart),
    then PATCHes position and size after upload.
    """
    if not LOGO_PATH.exists():
        print(f"  Warning: logo not found at {LOGO_PATH} — skipping.")
        return

    import io
    from PIL import Image

    logo_size = 50   # canvas units — matches the 50px resized image
    header_center_y = int(y_top - BRAND_HEADER_H / 2)
    logo_x = int(total_width - logo_size / 2 - 30)
    logo_y = header_center_y

    # Resize to 50×50 so native upload size matches desired canvas size
    img = Image.open(LOGO_PATH).convert("RGBA")
    img = img.resize((logo_size, logo_size), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    time.sleep(RATE_LIMIT_PAUSE)
    resp = requests.post(
        f"{MIRO_API}/boards/{board_id}/images",
        headers={"Authorization": auth_headers["Authorization"]},
        files={"resource": ("whitelogo.png", buf, "image/png")},
    )
    if resp.status_code not in (200, 201):
        print(f"  Warning: logo upload failed ({resp.status_code}) — {resp.text[:120]}")
        return

    image_id = resp.json().get("id")
    if not image_id:
        print("  Warning: no image ID returned — skipping position patch.")
        return

    # PATCH position and geometry — this is reliable unlike multipart data fields
    time.sleep(RATE_LIMIT_PAUSE)
    patch = requests.patch(
        f"{MIRO_API}/boards/{board_id}/images/{image_id}",
        headers=auth_headers,
        json={
            "position": {"x": logo_x, "y": logo_y, "origin": "center"},
            "geometry": {"width": logo_size, "height": logo_size},
        },
    )
    if patch.status_code in (200, 201):
        print(f"  Logo uploaded and positioned (size={logo_size}, x={logo_x}, y={logo_y}).")
    else:
        print(f"  Warning: logo position patch failed ({patch.status_code}) — {patch.text[:120]}")


def create_lane_vertical(board_id, headers, lane, total_height):
    """Vertical mode: lane is a column. Creates background + header label at top."""
    lane_x = lane["x"]
    lane_w = lane["width"]
    center_x = lane_x + lane_w / 2
    center_y = total_height / 2

    body = {
        "data": {"content": lane["label"], "shape": "rectangle"},
        "style": {
            "fillColor": lane["fill"],
            "fillOpacity": "0.4",
            "borderColor": lane["border"],
            "borderWidth": "2.0",
            "fontSize": "22",
            "color": "#333333",
            "textAlign": "center",
            "textAlignVertical": "top",
        },
        "position": {"x": center_x, "y": center_y},
        "geometry": {"width": lane_w, "height": total_height},
    }
    resp = post(board_id, "shapes", headers, body)
    return resp["id"]


def create_lane_horizontal(board_id, headers, lane, total_width):
    """
    Horizontal mode: lane is a row.
    Creates:
      - A dark label box on the left (LABEL_W wide, white text)
      - A light content background to the right
    """
    y_start = lane["y_start"]
    h = lane["height"]
    center_y = y_start + h / 2

    # Label box (left column)
    label_body = {
        "data": {"content": lane["label"], "shape": "rectangle"},
        "style": {
            "fillColor": lane.get("label_fill", "#555555"),
            "fillOpacity": "1.0",
            "borderColor": lane["border"],
            "borderWidth": "1.0",
            "fontSize": "16",
            "color": "#ffffff",
            "textAlign": "center",
            "textAlignVertical": "middle",
        },
        "position": {"x": LABEL_W / 2, "y": center_y},
        "geometry": {"width": LABEL_W, "height": h},
    }
    post(board_id, "shapes", headers, label_body)

    # Content background (right of label column)
    content_w = total_width - LABEL_W
    content_body = {
        "data": {"content": "", "shape": "rectangle"},
        "style": {
            "fillColor": lane["fill"],
            "fillOpacity": "0.45",
            "borderColor": lane["border"],
            "borderWidth": "1.0",
        },
        "position": {"x": LABEL_W + content_w / 2, "y": center_y},
        "geometry": {"width": content_w, "height": h},
    }
    post(board_id, "shapes", headers, content_body)


def create_shape(board_id, headers, node):
    style = NODE_STYLES.get(node["type"], NODE_STYLES["process"])
    body = {
        "data": {"content": node["label"], "shape": style["shape"]},
        "style": {
            "fillColor": style["fill"],
            "color": style["color"],
            "fontSize": "13",
            "borderColor": "#333333",
            "textAlign": "center",
        },
        "position": {"x": node["x"], "y": node["y"]},
        "geometry": {"width": NODE_W, "height": NODE_H},
    }
    resp = post(board_id, "shapes", headers, body)
    return resp["id"]


def create_connector(board_id, headers, from_id, to_id, label=""):
    body = {
        "startItem": {"id": from_id},
        "endItem": {"id": to_id},
        "style": {"strokeColor": "#444444", "strokeWidth": "2"},
    }
    if label:
        body["captions"] = [{"content": label, "position": "50%"}]
    resp = post(board_id, "connectors", headers, body)
    return resp["id"]


def main():
    workflow = json.loads(Path(".tmp/workflow.json").read_text())
    board_info = json.loads(Path(".tmp/board_info.json").read_text())
    board_id = board_info["board_id"]

    headers = {
        "Authorization": f"Bearer {os.environ['MIRO_ACCESS_TOKEN']}",
        "Content-Type": "application/json",
    }

    direction = workflow.get("direction", "vertical")
    lanes = workflow.get("lanes", [])
    nodes = workflow["nodes"]
    edges = workflow["edges"]

    title = workflow.get("title", "Workflow Diagram")

    # Step 1: Create lane backgrounds (rendered first so they sit behind nodes)
    if lanes:
        print(f"Creating {len(lanes)} swim lane backgrounds ({direction})...")
        if direction == "horizontal":
            max_x = max(n["x"] for n in nodes) + NODE_W + 80
            total_width = max_x
            for lane in lanes:
                create_lane_horizontal(board_id, headers, lane, total_width)
                print(f"  Lane: {lane['label']}")
            # Brand header sits above the lanes (y=0 is top of first lane)
            print("\nAdding brand elements...")
            add_brand_header(board_id, headers, title, total_width, y_top=0)
            upload_logo(board_id, headers, y_top=0, total_width=total_width)
        else:
            max_y = max(n["y"] for n in nodes) + NODE_H + 80
            total_height = max_y
            max_x = max(n["x"] for n in nodes) + NODE_W + 80
            total_width = max_x
            for lane in lanes:
                create_lane_vertical(board_id, headers, lane, total_height)
                print(f"  Lane: {lane['label']}")
            print("\nAdding brand elements...")
            add_brand_header(board_id, headers, title, total_width, y_top=0)
            upload_logo(board_id, headers, y_top=0, total_width=total_width)

    # Step 2: Create node shapes
    print(f"\nCreating {len(nodes)} nodes...")
    node_id_map = {}
    for node in nodes:
        miro_id = create_shape(board_id, headers, node)
        node_id_map[node["id"]] = miro_id
        label_short = node["label"].replace("\n", " ")
        print(f"  [{node['type']}] {label_short}")

    # Step 3: Create connectors
    print(f"\nCreating {len(edges)} connectors...")
    for edge in edges:
        from_miro = node_id_map[edge["from"]]
        to_miro = node_id_map[edge["to"]]
        label = edge.get("label", "")
        create_connector(board_id, headers, from_miro, to_miro, label)
        print(f"  {edge['from']} → {edge['to']}" + (f" [{label}]" if label else ""))

    # Save node map
    board_info["node_id_map"] = node_id_map
    Path(".tmp/board_info.json").write_text(json.dumps(board_info, indent=2))

    print(f"\nSwim lane workflow rendered.")
    print(f"View at: {board_info['board_url']}")


if __name__ == "__main__":
    main()
