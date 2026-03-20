"""
miro_export_png.py

Exports the current Miro board as a PNG image.

Miro's image export requires a paid plan (Business or Enterprise). This tool
attempts the API export first. If it fails due to plan restrictions, it falls
back to saving the board URL and instructions for manual export.

Usage:
    python tools/miro_export_png.py

Output:
    .tmp/workflow.png    (if export succeeds)
    .tmp/export_info.json with board_url and export status

API reference:
    POST /v2/boards/{board_id}/export/jobs  -> create job
    GET  /v2/boards/{board_id}/export/jobs/{job_id} -> poll until "finished"
    Then download the result URL
"""

import json
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

MIRO_API = "https://api.miro.com/v2"
POLL_INTERVAL = 3   # seconds between status checks
MAX_POLLS = 20      # give up after ~60 seconds


def export_board_png(board_id: str, headers: dict) -> str | None:
    """Attempts API export. Returns local file path or None if unavailable."""

    # Create export job
    resp = requests.post(
        f"{MIRO_API}/boards/{board_id}/export/jobs",
        headers=headers,
        json={"format": "png", "outputFileId": "workflow_export"},
    )

    if resp.status_code in (402, 403, 404):
        print("  Export API not available on current Miro plan.")
        print("  Manual export: open the board -> Export -> Export to PNG")
        return None

    resp.raise_for_status()
    job_id = resp.json()["id"]
    print(f"  Export job created: {job_id}")

    # Poll for completion
    for attempt in range(MAX_POLLS):
        time.sleep(POLL_INTERVAL)
        status_resp = requests.get(
            f"{MIRO_API}/boards/{board_id}/export/jobs/{job_id}",
            headers=headers,
        )
        status_resp.raise_for_status()
        status_data = status_resp.json()
        status = status_data.get("status")
        print(f"  Export status: {status} (attempt {attempt + 1}/{MAX_POLLS})")

        if status == "finished":
            download_url = status_data["result"]["url"]
            img_resp = requests.get(download_url)
            img_resp.raise_for_status()

            output_path = Path(".tmp/workflow.png")
            output_path.write_bytes(img_resp.content)
            print(f"  PNG saved to {output_path} ({len(img_resp.content) // 1024} KB)")
            return str(output_path)

        elif status == "failed":
            print(f"  Export job failed: {status_data}")
            return None

    print("  Export timed out.")
    return None


def main():
    board_info = json.loads(Path(".tmp/board_info.json").read_text())
    board_id = board_info["board_id"]
    headers = {
        "Authorization": f"Bearer {os.environ['MIRO_ACCESS_TOKEN']}",
        "Content-Type": "application/json",
    }

    print(f"Exporting board {board_id} as PNG...")
    png_path = export_board_png(board_id, headers)

    export_info = {
        "board_url": board_info["board_url"],
        "board_id": board_id,
        "png_path": png_path,
        "export_available": png_path is not None,
    }

    Path(".tmp/export_info.json").write_text(json.dumps(export_info, indent=2))
    print(f"Export info saved to .tmp/export_info.json")
    print(f"Board URL: {board_info['board_url']}")
    return export_info


if __name__ == "__main__":
    main()
