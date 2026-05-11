# Checklist

## Phase 0: Setup
- [x] Install deps with `make install`
- [x] Run `make test` once
- [x] Read `README.md`, `docs/LAB_GUIDE.md`, `docs/RUBRIC.md`
- [x] Inspect `data/sample/scenarios.jsonl`

## Phase 1: Core graph
- [x] Update `src/langgraph_agent_lab/state.py`
- [x] Keep lean serializable state
- [x] Use append-only reducers only for audit lists
- [x] Add `evaluation_result` for retry gate
- [x] Carry `requires_approval` and `should_retry` into initial state
- [x] Implement `src/langgraph_agent_lab/nodes.py`
- [x] `classify_node` uses keyword + word-boundary heuristics
- [x] Risky keywords win first
- [x] Tool keywords win second
- [x] Missing-info only for short vague queries
- [x] Error keywords catch failure/timeout/crash cases
- [x] `evaluate_node` sets `needs_retry` or `success`
- [x] `retry_or_fallback_node` increments attempt
- [x] `dead_letter_node` handles max retry exhaustion
- [x] `approval_node` defaults approved for CI
- [x] `answer_node` grounds output in tool results when present
- [x] Implement `src/langgraph_agent_lab/routing.py`
- [x] Classify routes map cleanly to next node
- [x] Evaluate routes map to retry or answer
- [x] Retry routes stop at `max_attempts`
- [x] Approval routes continue only when approved
- [x] Wire `src/langgraph_agent_lab/graph.py`
- [x] Every path ends at `finalize -> END`
- [x] Run `.venv/bin/pytest`
- [x] Run `make run-scenarios`
- [x] Confirm `outputs/metrics.json` hits `100%` success

## Phase 2: Persistence
- [x] Implement `src/langgraph_agent_lab/persistence.py`
- [x] Support `memory` checkpointer
- [x] Support `sqlite` checkpointer
- [x] Use `sqlite3.connect(..., check_same_thread=False)`
- [x] Enable WAL mode
- [x] Accept plain path and `sqlite:///...`
- [x] Keep `thread_id` unique per scenario
- [x] Prove state history survives restart with SQLite
- [x] Show memory loses history after restart

## Phase 3: Metrics and report
- [x] Run `make grade-local`
- [x] Verify metrics schema is valid
- [x] Check retry and interrupt counts
- [x] Fill `reports/lab_report.md`
- [x] Describe architecture and state schema
- [x] Paste scenario table from metrics
- [x] Explain one failure mode and one retry path
- [x] Add persistence / recovery evidence
- [x] Add improvement plan

## Phase 4: Bonus points
- [x] Pick at least one bonus extension
- [x] Add real HITL with interrupt/resume
- [x] Add crash recovery demo with SQLite restart
- [x] Add time travel with `get_state_history()`
- [x] Add parallel fan-out with `Send()`
- [x] Add graph diagram export
- [x] Add bonus evidence to report

## Final checks
- [x] `make test` passes
- [x] `make lint` passes
- [x] `make typecheck` passes
- [x] `make grade-local` passes
- [x] `outputs/metrics.json` valid
- [x] `reports/lab_report.md` complete
- [x] Can explain one route, one retry, one persistence demo
- [x] Can explain crash recovery from a persisted checkpoint
