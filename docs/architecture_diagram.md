# WAT Workflow Agent — Architecture Diagram

```mermaid
%%{init: {
  "theme": "base",
  "themeVariables": {
    "background":         "#ffffff",
    "primaryColor":       "#1b3d4a",
    "primaryTextColor":   "#ffffff",
    "primaryBorderColor": "#4e8fa2",
    "lineColor":          "#4e8fa2",
    "fontSize":           "14px"
  }
}}%%
flowchart TD

    %% ── Styles ──────────────────────────────────────────────
    classDef input      fill:#1b3d4a,color:#ffffff,stroke:#4e8fa2,stroke-width:2px
    classDef workflow   fill:#2a6478,color:#ffffff,stroke:#4e8fa2,stroke-width:2px
    classDef agent      fill:#3a7a8e,color:#ffffff,stroke:#1b3d4a,stroke-width:3px,font-weight:bold
    classDef tool       fill:#4e8fa2,color:#ffffff,stroke:#1b3d4a,stroke-width:1px
    classDef external   fill:#e6f4f7,color:#1b3d4a,stroke:#4e8fa2,stroke-width:1px
    classDef output     fill:#1b3d4a,color:#ffffff,stroke:#4e8fa2,stroke-width:2px
    classDef section    fill:#ffffff,color:#1b3d4a,stroke:#4e8fa2,stroke-width:2px,stroke-dasharray:6 3

    %% ── Inputs ──────────────────────────────────────────────
    subgraph INPUTS["  Inputs  "]
        direction LR
        SLACK_IN["💬 Slack @mention"]
        CHAT_IN["🖥️ Claude Code Chat"]
    end

    %% ── Layer 1: Workflows ───────────────────────────────────
    subgraph WORKFLOWS["  Layer 1 — Workflows  "]
        direction LR
        WF1["📄 create_workflow.md"]
        WF2["📄 update_workflow.md"]
        WF3["📄 slack_trigger.md"]
        WF4["📄 export_and_deliver.md"]
    end

    %% ── Layer 2: Agent ───────────────────────────────────────
    AGENT["🤖 Claude Agent\n(Orchestration & Decisions)"]

    %% ── Layer 3: Tools ───────────────────────────────────────
    subgraph TOOLS["  Layer 3 — Tools  "]
        direction LR
        subgraph PARSE["Parse"]
            T1["parse_swimlane\n_workflow.py"]
        end
        subgraph MIRO_TOOLS["Miro"]
            T2["miro_create\n_board.py"]
            T3["miro_add\n_swimlane.py"]
            T4["miro_update\n_workflow.py"]
        end
        subgraph CAPTURE["Capture"]
            T5["screenshot\n_board.py"]
            T6["generate\n_mermaid.py"]
        end
        subgraph DELIVER["Deliver"]
            T7["slack_listener.py"]
            T8["slack_respond.py"]
            T9["send_email.py"]
        end
    end

    %% ── External Services ────────────────────────────────────
    subgraph EXTERNAL["  External Services  "]
        direction LR
        E1["🧠 Anthropic API\nclaude-opus-4-6"]
        E2["🟦 Miro API v2"]
        E3["💬 Slack API\nSocket Mode"]
        E4["📧 Resend API"]
    end

    %% ── Outputs ─────────────────────────────────────────────
    subgraph OUTPUTS["  Outputs  "]
        direction LR
        O1["🟦 Miro Board\n(live diagram)"]
        O2["💬 Slack Thread\nboard link · PNG · .mmd"]
        O3["📧 Email\nboard link · PNG"]
    end

    %% ── Temp Storage ─────────────────────────────────────────
    subgraph TMP["  .tmp/ (intermediate files)  "]
        direction LR
        F1["workflow.json"]
        F2["board_info.json"]
        F3["workflow.png"]
        F4["workflow.mmd"]
    end

    %% ── Connections ─────────────────────────────────────────
    SLACK_IN --> WORKFLOWS
    CHAT_IN  --> WORKFLOWS
    WORKFLOWS --> AGENT

    AGENT --> T1
    AGENT --> T2
    AGENT --> T3
    AGENT --> T4
    AGENT --> T5
    AGENT --> T6
    AGENT --> T7
    AGENT --> T8
    AGENT --> T9

    T1 -->|"workflow JSON"| F1
    T2 -->|"board_id · URL"| F2
    T3 --> E2
    T4 --> E2
    T5 -->|"PNG"| F3
    T6 -->|".mmd"| F4

    T1 --> E1
    T4 --> E1
    T7 --> E3
    T8 --> E3
    T9 --> E4

    E2 --> O1
    T8 --> O2
    T9 --> O3

    F1 -.-> T2
    F1 -.-> T3
    F1 -.-> T4
    F1 -.-> T6
    F2 -.-> T3
    F2 -.-> T4
    F2 -.-> T5
    F3 -.-> T8
    F3 -.-> T9
    F4 -.-> T8

    %% ── Apply styles ─────────────────────────────────────────
    class SLACK_IN,CHAT_IN input
    class WF1,WF2,WF3,WF4 workflow
    class AGENT agent
    class T1,T2,T3,T4,T5,T6,T7,T8,T9 tool
    class E1,E2,E3,E4 external
    class O1,O2,O3 output
    class F1,F2,F3,F4 external
```

## Legend

| Colour | Layer |
|--------|-------|
| Deep Navy `#1b3d4a` | Inputs & Outputs |
| Dark Teal `#2a6478` | Workflows (SOPs) |
| Button Blue `#3a7a8e` | Agent (Claude) |
| Medium Teal `#4e8fa2` | Tools (Python scripts) |
| Ice Blue `#e6f4f7` | External Services & Temp Files |
