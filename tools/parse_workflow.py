"""
parse_workflow.py

Takes a plain-language description of a technical/business process and uses
Claude to convert it into a structured workflow JSON file.

Usage:
    python tools/parse_workflow.py "Describe the CI/CD pipeline from code push to production"

Output:
    Writes .tmp/workflow.json with nodes and edges ready for Miro.

Node types:
    start        - Entry point (rounded rectangle, green)
    process      - A step or action (rectangle, blue)
    decision     - A yes/no branch (rhombus, yellow)
    end          - Success terminal (rounded rectangle, teal)
    end_error    - Failure terminal (rounded rectangle, red)
"""

import sys
import json
import os
from pathlib import Path

import anthropic
from dotenv import load_dotenv

load_dotenv()

SYSTEM_PROMPT = """You are a technical workflow architect. Convert process descriptions into structured JSON.

Output ONLY valid JSON with this exact shape:
{
  "title": "string",
  "nodes": [
    {"id": "1", "label": "string", "type": "start|process|decision|end|end_error"}
  ],
  "edges": [
    {"from": "1", "to": "2", "label": "optional string"}
  ]
}

Rules:
- Every workflow must have exactly one "start" node
- Decision nodes must have exactly two outgoing edges, labeled (e.g. "Yes"/"No", "Pass"/"Fail")
- Keep labels short (3-6 words max)
- Use "end_error" for failure/error terminal states
- Number node IDs sequentially starting from "1"
- Do not include markdown fences or explanation, only the JSON object
"""


def parse(description: str) -> dict:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": description}],
    )

    raw = message.content[0].text.strip()
    # Strip markdown code fences if the model wraps the JSON
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    workflow = json.loads(raw)
    return workflow


def main():
    if len(sys.argv) < 2:
        print("Usage: python tools/parse_workflow.py \"<process description>\"")
        sys.exit(1)

    description = sys.argv[1]
    print(f"Parsing workflow: {description[:80]}...")

    workflow = parse(description)

    output_path = Path(".tmp/workflow.json")
    output_path.parent.mkdir(exist_ok=True)
    output_path.write_text(json.dumps(workflow, indent=2))

    print(f"Parsed {len(workflow['nodes'])} nodes, {len(workflow['edges'])} edges")
    print(f"Saved to {output_path}")
    return workflow


if __name__ == "__main__":
    main()
