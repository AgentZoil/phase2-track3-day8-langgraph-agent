# Checklist

## Phase 0: Setup
- [ ] Install dependencies with `make install`
- [ ] Run `make test` once to confirm baseline
- [ ] Review `data/sample/scenarios.jsonl` and routing rules in README

## Phase 1: Core graph
- [ ] Update `src/langgraph_agent_lab/state.py`
- [ ] Add typed state fields and reducers
- [ ] Add `evaluation_result` for retry control
- [ ] Implement node logic in `src/langgraph_agent_lab/nodes.py`
- [ ] Build `classify_node` with keyword-based routing
- [ ] Build `evaluate_node` to detect tool success or retry need
- [ ] Build `dead_letter_node` for exhausted failures
- [ ] Build `approval_node` with default approved state
- [ ] Implement routing in `src/langgraph_agent_lab/routing.py`
- [ ] Map classify output to next node
- [ ] Map evaluate output to retry or answer
- [ ] Stop retry loop at `max_attempts`
- [ ] Wire graph in `src/langgraph_agent_lab/graph.py`
- [ ] Ensure every route ends at `finalize -> END`
- [ ] Run `make test`
- [ ] Run `make run-scenarios`

## Phase 2: Persistence
- [ ] Implement checkpoint factory in `src/langgraph_agent_lab/persistence.py`
- [ ] Support `memory` checkpointer
- [ ] Support `sqlite` checkpointer with WAL mode
- [ ] Confirm `thread_id` is set per run
- [ ] Capture recovery or state-history evidence

## Phase 3: Metrics and report
- [ ] Generate `outputs/metrics.json` with `make run-scenarios`
- [ ] Validate output with `make grade-local`
- [ ] Review `src/langgraph_agent_lab/metrics.py` behavior
- [ ] Fill `reports/lab_report.md`
- [ ] Explain architecture and node boundaries
- [ ] Summarize metrics and scenario coverage
- [ ] Describe failure mode and retry behavior
- [ ] Add improvement ideas

## Phase 4: Bonus points
- [ ] Add at least one bonus extension
- [ ] Try parallel fan-out with `Send()`
- [ ] Try real HITL with interrupt/resume
- [ ] Try crash recovery with SQLite checkpoint
- [ ] Try time travel with state history
- [ ] Export graph diagram if useful
- [ ] Add evidence of bonus feature to report

## Final checks
- [ ] `make test` passes
- [ ] `make lint` passes
- [ ] `make typecheck` passes
- [ ] `make grade-local` passes
- [ ] `outputs/metrics.json` is valid
- [ ] `reports/lab_report.md` is complete
- [ ] Can explain one route and one failure mode in demo
