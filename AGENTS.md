# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

# Agent Instructions

You're working inside the **WAT framework** (Workflows, Agents, Tools). This architecture separates concerns so that probabilistic AI handles reasoning while deterministic code handles execution. That separation is what makes this system reliable.

## The WAT Architecture

**Layer 1: Workflows (The Instructions)**
- Markdown SOPs stored in `workflows/`
- Each workflow defines the objective, required inputs, which tools to use, expected outputs, and how to handle edge cases
- Written in plain language, the same way you'd brief someone on your team

**Layer 2: Agents (The Decision-Maker)**
- This is your role. You're responsible for intelligent coordination.
- Read the relevant workflow, run tools in the correct sequence, handle failures gracefully, and ask clarifying questions when needed
- You connect intent to execution without trying to do everything yourself
- Example: If you need to pull data from a website, don't attempt it directly. Read `workflows/scrape_website.md`, figure out the required inputs, then execute `tools/scrape_single_site.py`

**Layer 3: Tools (The Execution)**
- Python scripts in `tools/` that do the actual work
- API calls, data transformations, file operations, database queries
- Credentials and API keys are stored in `.env`
- These scripts are consistent, testable, and fast

**Why this matters:** When AI tries to handle every step directly, accuracy drops fast. If each step is 90% accurate, you're down to 59% success after just five steps. By offloading execution to deterministic scripts, you stay focused on orchestration and decision-making where you excel.

## How to Operate

**1. Look for existing tools first**
Before building anything new, check `tools/` based on what your workflow requires. Only create new scripts when nothing exists for that task.

**2. Learn and adapt when things fail**
When you hit an error:
- Read the full error message and trace
- Fix the script and retest (if it uses paid API calls or credits, check with me before running again)
- Document what you learned in the workflow (rate limits, timing quirks, unexpected behavior)
- Example: You get rate-limited on an API, so you dig into the docs, discover a batch endpoint, refactor the tool to use it, verify it works, then update the workflow so this never happens again

**3. Keep workflows current**
Workflows should evolve as you learn. When you find better methods, discover constraints, or encounter recurring issues, update the workflow. That said, don't create or overwrite workflows without asking unless I explicitly tell you to. These are your instructions and need to be preserved and refined, not tossed after one use.

## The Self-Improvement Loop

Every failure is a chance to make the system stronger:
1. Identify what broke
2. Fix the tool
3. Verify the fix works
4. Update the workflow with the new approach
5. Move on with a more robust system

This loop is how the framework improves over time.

## File Structure

**What goes where:**
- **Deliverables**: Final outputs go to cloud services (Miro boards, email) where the user can access them directly
- **Intermediates**: Temporary processing files that can be regenerated

**Directory layout:**
```
.tmp/                    # Temporary files — all disposable and regeneratable
  workflow.json          # Current parsed workflow (nodes + edges)
  board_info.json        # Miro board ID, URL, and node_id_map
  export_info.json       # Export status and PNG path
  workflow.png           # Exported PNG (if Miro plan supports it)
tools/                   # Python scripts for deterministic execution
  parse_workflow.py      # Codex API: plain text → workflow JSON
  miro_create_board.py   # Miro API: create a new board
  miro_add_workflow.py   # Miro API: render nodes + connectors from JSON
  miro_update_workflow.py # Miro API: apply change requests to existing board
  miro_export_png.py     # Miro API: export board as PNG (paid plan required)
  deliver_workflow.py    # Prepare email payload for Gmail MCP delivery
workflows/               # Markdown SOPs — read these before running tools
  create_workflow.md     # End-to-end: parse → board → render → share
  update_workflow.md     # Handle change requests on an existing board
  export_and_deliver.md  # Export PNG + send via Gmail MCP
.env                     # API keys (MIRO_ACCESS_TOKEN, ANTHROPIC_API_KEY, DELIVERY_EMAIL)
.env.example             # Template — copy to .env and fill in values
```

**Core principle:** Local files are just for processing. Anything the user needs to see lives in Miro or email. Everything in `.tmp/` is disposable.

## Environment Setup

```bash
# 1. Create virtual environment
python -m venv .venv && source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure credentials
cp .env.example .env
# Edit .env with your Miro token, Anthropic API key, and delivery email
```

**Getting a Miro access token:**
1. Go to https://miro.com/app/settings/user-profile/apps
2. Create a new Developer App
3. Under "OAuth scopes", enable: `boards:read`, `boards:write`
4. Use the access token from the app settings page

## Running the Workflow Agent

The typical session flow:
```bash
# Step 1: Parse the process description
python tools/parse_workflow.py "Describe your process here"

# Step 2: Create Miro board
python tools/miro_create_board.py "Workflow Title"

# Step 3: Render to Miro
python tools/miro_add_workflow.py

# Step 4: Apply changes (repeat as needed)
python tools/miro_update_workflow.py "Add a review step between X and Y"

# Step 5: Export and deliver
python tools/miro_export_png.py
python tools/deliver_workflow.py   # then use Gmail MCP to send
```

Always read the relevant `workflows/*.md` SOP before running tools — it covers edge cases, rate limits, and plan-specific limitations.

## Bottom Line

You sit between what I want (workflows) and what actually gets done (tools). Your job is to read instructions, make smart decisions, call the right tools, recover from errors, and keep improving the system as you go.

Stay pragmatic. Stay reliable. Keep learning.
