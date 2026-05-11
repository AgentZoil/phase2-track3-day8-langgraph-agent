# Day 08 Lab Report

## 1. Team / student

- Name: Nhữ Gia Bách
- MSSV: 2A202600248
- Date: 2026-05-11

## 2. Deliverables

- `outputs/metrics.json`: grading summary with `success_rate=100%`.
- `reports/lab_report.md`: narrative summary, architecture, metrics, and evidence.
- `outputs/graph.mmd`: Mermaid diagram of the full workflow.
- `outputs/time_travel.json`: checkpoint history proof.
- `outputs/hitl.json`: human-in-the-loop resume proof.
- `outputs/crash_recovery.json`: SQLite restart recovery proof.
- `outputs/fanout.json`: parallel fan-out proof.

## 3. Architecture

Graph flow: `START -> intake -> classify -> route`. The classifier routes into six behaviors: `simple`, `tool`, `missing_info`, `risky`, `error`, and parallel `tool` fan-out. Simple tickets end at `answer -> finalize -> END`. Tool tickets fan out into `tool_primary` and `tool_secondary`, then merge at `evaluate -> answer -> finalize -> END`. Missing-info tickets go `clarify -> finalize -> END`. Risky tickets go `risky_action -> approval -> tool -> evaluate -> answer -> finalize -> END`. Error tickets go `retry -> tool -> evaluate -> ...` until success or `dead_letter` when the retry budget is exhausted.

State stays lean and serializable. Scalars overwrite current values; audit lists use append reducers so events, tool evidence, errors, and PII findings stay history-safe.

## 4. State schema

| Field | Reducer | Why |
|---|---|---|
| messages | append | audit conversation/events |
| tool_outputs | append | preserve structured tool evidence |
| tool_results | append | preserve tool output text |
| errors | append | keep retry and failure history |
| events | append | keep node-by-node audit trail |
| pii_findings | append | keep normalized PII detection results |
| route | overwrite | current route only |
| final_answer | overwrite | final response only |
| attempt | overwrite | current retry attempt only |

## 5. Scenario results

Metrics summary: 15/15 scenarios succeeded, 5 approval hits observed, 3 scenarios retried, and `success_rate=100.00%`.

| Scenario | Expected route | Actual route | Success | Retries | Interrupts |
|---|---|---|---:|---:|---:|
| G01_simple | simple | simple | yes | 0 | 0 |
| G02_simple2 | simple | simple | yes | 0 | 0 |
| G03_tool | tool | tool | yes | 0 | 0 |
| G04_tool2 | tool | tool | yes | 0 | 0 |
| G05_tool3 | tool | tool | yes | 0 | 0 |
| G06_missing | missing_info | missing_info | yes | 0 | 0 |
| G07_missing2 | missing_info | missing_info | yes | 0 | 0 |
| G08_risky | risky | risky | yes | 0 | 1 |
| G09_risky2 | risky | risky | yes | 0 | 1 |
| G10_risky3 | risky | risky | yes | 0 | 1 |
| G11_risky4 | risky | risky | yes | 0 | 1 |
| G12_error | error | error | yes | 1 | 0 |
| G13_error2 | error | error | yes | 1 | 0 |
| G14_dead | error | error | yes | 1 | 0 |
| G15_mixed | risky | risky | yes | 0 | 1 |

## 6. Failure analysis

1. Retry or tool failure: transient tool output is marked `status=error`, then `evaluate_node` routes to `retry` until `max_attempts` is reached. This prevents infinite loops and gives a clean dead-letter path.
2. Risky action without approval: high-risk requests pass through `risky_action` and `approval` before the tool executes. The approval node can reject, edit, or time out, which keeps side effects gated.
3. Fan-out merge correctness: the parallel branch writes two tool outputs with distinct variants, and `answer_node` deduplicates the result strings before the final answer is generated.

## 7. Persistence / recovery evidence

Persistence uses a checkpointer factory with `sqlite` enabled in `configs/lab.yaml`. Each scenario gets a stable `thread_id` prefix, and the CLI appends a per-run suffix so checkpoint histories do not collide across repeated runs. `graph.get_state_history(config)` returns checkpoint snapshots after execution. SQLite survives process restart, while memory is only for in-process development. The `outputs/time_travel.json` file captures both the latest snapshot and a rewind snapshot from the same thread. The `outputs/crash_recovery.json` file shows a checkpoint written before a simulated restart and the recovered run after reload.

## 8. Extension work

Completed extension: SQLite persistence with WAL mode and history replay. The run also records structured tool outputs, PII detection metadata, a dead-letter ticket payload for exhausted retries, real HITL resume evidence, crash-recovery evidence, and parallel fan-out evidence. The Mermaid diagram export is available via `python -m langgraph_agent_lab.cli export-diagram --config configs/lab.yaml --output outputs/graph.mmd`. Time-travel evidence is available via `python -m langgraph_agent_lab.cli time-travel-demo --config configs/lab.yaml --output outputs/time_travel.json`. Real HITL evidence is available via `python -m langgraph_agent_lab.cli hitl-demo --config configs/lab.yaml --output outputs/hitl.json`. Crash recovery evidence is available via `python -m langgraph_agent_lab.cli crash-recovery-demo --config configs/lab.yaml --output outputs/crash_recovery.json`. Parallel fan-out evidence is available via `python -m langgraph_agent_lab.cli fanout-demo --config configs/lab.yaml --output outputs/fanout.json`.

## 9. Improvement plan

If I had one more day, I would add a real human approval UI, persist dead-letter items to an external queue, and attach trace logs to each output artifact so the demo can be replayed faster.
