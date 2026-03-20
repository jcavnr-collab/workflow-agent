"""
miro_create_board.py

Creates a new Miro board for a workflow and saves the board ID/URL for
subsequent tool calls.

Usage:
    python tools/miro_create_board.py "CI/CD Pipeline"

Output:
    Writes .tmp/board_info.json with:
        {
          "board_id": "...",
          "board_url": "https://miro.com/app/board/...",
          "title": "..."
        }

Requirements:
    MIRO_ACCESS_TOKEN in .env
"""

import sys
import json
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

MIRO_API = "https://api.miro.com/v2"


def create_board(title: str) -> dict:
    headers = {
        "Authorization": f"Bearer {os.environ['MIRO_ACCESS_TOKEN']}",
        "Content-Type": "application/json",
    }

    payload = {
        "name": title,
        "description": f"Workflow diagram: {title}",
    }

    response = requests.post(f"{MIRO_API}/boards", headers=headers, json=payload)
    response.raise_for_status()

    data = response.json()
    board_info = {
        "board_id": data["id"],
        "board_url": data["viewLink"],
        "title": title,
    }
    return board_info


def main():
    title = sys.argv[1] if len(sys.argv) > 1 else "Workflow Diagram"

    print(f"Creating Miro board: {title}")
    board_info = create_board(title)

    output_path = Path(".tmp/board_info.json")
    output_path.parent.mkdir(exist_ok=True)
    output_path.write_text(json.dumps(board_info, indent=2))

    print(f"Board created: {board_info['board_url']}")
    print(f"Board ID: {board_info['board_id']}")
    print(f"Saved to {output_path}")
    return board_info


if __name__ == "__main__":
    main()
