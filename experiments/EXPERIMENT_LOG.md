# Gemma 4 Developer Agent: Experiment Tracking & Ablation Log

This log tracks all experimental iterations across both the **Leaderboard Track** and the **Paper Track** (Table 1: Architecture & Budget Ablation, Table 2: Multi-LoRA vs. Monolithic LoRA).

---

## 1. Submissions & Leaderboard Progress

| Exp ID | Date / Time (UTC) | Ref ID | Architecture / Configuration | Budget Configuration | Public Score | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **exp00** | — | — | Baseline Starter Kit (1-layer dummy LoRA, single agent) | `10 calls, 1 min, 60s timeout` | ~`0.18` (estimated) | Reference benchmark |
| **exp01** | `2026-10-30 23:23` | `57819201` | Clean Base 31B (`gemma-4-31b-it-qat-w4a16-ct`), context-isolated `agent_tool` analyzer (`skip_summarization: true`), prompt guardrails (/tmp/ repro, no tests edit) | `30 calls, 6 min, 180s timeout` | *Pending* | First calibrated submission |
| **exp02** | *Planned* | — | Deterministic `SequentialAgent` pipeline (LocalizationAgent -> PatchAgent) | `35 calls, 6 min, 180s timeout` | — | Eliminates coder agent wander |
| **exp03** | *Planned* | — | ADK Skills Playbook (`skills/swe_playbooks`) | `35 calls, 6 min, 180s timeout` | — | Reusable diagnostic skills |
| **exp04** | *Planned* | — | Role-Specialized Multi-LoRA (`localization_lora` + `coder_lora`) | `35 calls, 6 min, 180s timeout` | — | Multi-LoRA on 4x L4 GPUs |

---

## 2. Key Metrics & Observations to Log
- Total wall-clock time per task
- Tool calls utilized before `submit_patch()`
- Truncation frequency (`<|tool_call>` cutoffs)
- Error rates by repo (`fastapi`, `rich`, `requests`, `httpx`)

