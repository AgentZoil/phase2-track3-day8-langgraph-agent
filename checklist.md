# Checklist

## Phase 0: Setup
- [ ] Install deps with `make install`
- [ ] Run `make test` once
- [ ] Read `README.md`, `docs/LAB_GUIDE.md`, `docs/RUBRIC.md`
- [ ] Inspect `data/sample/scenarios.jsonl`

## Phase 1: Core graph
- [ ] Update `src/langgraph_agent_lab/state.py`
- [ ] Keep lean serializable state
- [ ] Use append-only reducers only for audit lists
- [ ] Add `evaluation_result` for retry gate
- [ ] Carry `requires_approval` and `should_retry` into initial state
- [ ] Implement `src/langgraph_agent_lab/nodes.py`
- [ ] `classify_node` uses keyword + word-boundary heuristics
- [ ] Risky keywords win first
- [ ] Tool keywords win second
- [ ] Missing-info only for short vague queries
- [ ] Error keywords catch failure/timeout/crash cases
- [ ] `evaluate_node` sets `needs_retry` or `success`
- [ ] `retry_or_fallback_node` increments attempt
- [ ] `dead_letter_node` handles max retry exhaustion
- [ ] `approval_node` defaults approved for CI
- [ ] `answer_node` grounds output in tool results when present
- [ ] Implement `src/langgraph_agent_lab/routing.py`
- [ ] Classify routes map cleanly to next node
- [ ] Evaluate routes map to retry or answer
- [ ] Retry routes stop at `max_attempts`
- [ ] Approval routes continue only when approved
- [ ] Wire `src/langgraph_agent_lab/graph.py`
- [ ] Every path ends at `finalize -> END`
- [ ] Run `.venv/bin/pytest`
- [ ] Run `make run-scenarios`
- [ ] Confirm `outputs/metrics.json` hits `100%` success

## Phase 2: Persistence
- [ ] Implement `src/langgraph_agent_lab/persistence.py`
- [ ] Support `memory` checkpointer
- [ ] Support `sqlite` checkpointer
- [ ] Use `sqlite3.connect(..., check_same_thread=False)`
- [ ] Enable WAL mode
- [ ] Accept plain path and `sqlite:///...`
- [ ] Keep `thread_id` unique per scenario
- [ ] Prove state history survives restart with SQLite
- [ ] Show memory loses history after restart

## Phase 3: Metrics and report
- [ ] Run `make grade-local`
- [ ] Verify metrics schema is valid
- [ ] Check retry and interrupt counts
- [ ] Fill `reports/lab_report.md`
- [ ] Describe architecture and state schema
- [ ] Paste scenario table from metrics
- [ ] Explain one failure mode and one retry path
- [ ] Add persistence / recovery evidence
- [ ] Add improvement plan

## Phase 4: Bonus points
- [ ] Pick at least one bonus extension
- [ ] Add real HITL with interrupt/resume
- [ ] Add time travel with `get_state_history()`
- [ ] Add parallel fan-out with `Send()`
- [ ] Add graph diagram export
- [ ] Add bonus evidence to report

## Final checks
- [ ] `make test` passes
- [ ] `make lint` passes
- [ ] `make typecheck` passes
- [ ] `make grade-local` passes
- [ ] `outputs/metrics.json` valid
- [ ] `reports/lab_report.md` complete
- [ ] Can explain one route, one retry, one persistence demo
