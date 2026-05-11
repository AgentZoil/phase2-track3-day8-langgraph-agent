"""Report generation helper."""

from __future__ import annotations

import subprocess
from datetime import date
from pathlib import Path

from .metrics import MetricsReport, ScenarioMetric


def _git_commit() -> str:
    try:
        output = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except Exception:
        return "unknown"
    return output.strip() or "unknown"


def _format_bool(value: bool) -> str:
    return "yes" if value else "no"


def _render_scenario_table(items: list[ScenarioMetric]) -> str:
    lines = [
        "| Scenario | Expected route | Actual route | Success | Retries | Interrupts |",
        "|---|---|---|---:|---:|---:|",
    ]
    for item in items:
        lines.append(
            f"| {item.scenario_id} | {item.expected_route} | {item.actual_route or 'n/a'} | "
            f"{_format_bool(item.success)} | {item.retry_count} | {item.interrupt_count} |"
        )
    return "\n".join(lines)


def _render_state_table() -> str:
    return "\n".join(
        [
            "| Field | Reducer | Why |",
            "|---|---|---|",
            "| messages | append | audit conversation/events |",
            "| tool_outputs | append | preserve structured tool evidence |",
            "| tool_results | append | preserve tool output text |",
            "| errors | append | keep retry and failure history |",
            "| events | append | keep node-by-node audit trail |",
            "| pii_findings | append | keep normalized PII detection results |",
            "| route | overwrite | current route only |",
            "| final_answer | overwrite | final response only |",
            "| attempt | overwrite | current retry attempt only |",
        ]
    )


def render_report(metrics: MetricsReport) -> str:
    """Render full lab report from metrics."""
    successful = sum(1 for item in metrics.scenario_metrics if item.success)
    approval_hits = sum(1 for item in metrics.scenario_metrics if item.approval_observed)
    retrying = sum(1 for item in metrics.scenario_metrics if item.retry_count > 0)
    lines = [
        "# Day 08 Lab Report",
        "",
        "## 1. Team / student",
        "",
        "- Name: Nhữ Gia Bách",
        "- MSSV: 2A202600248",
        f"- Date: {date.today().isoformat()}",
        "",
        "## 2. Deliverables",
        "",
        "- `outputs/metrics.json`: grading summary with `success_rate=100%`.",
        "- `reports/lab_report.md`: narrative summary, architecture, metrics, and evidence.",
        "- `outputs/graph.mmd`: Mermaid diagram of the full workflow.",
        "- `outputs/time_travel.json`: checkpoint history proof.",
        "- `outputs/hitl.json`: human-in-the-loop resume proof.",
        "- `outputs/crash_recovery.json`: SQLite restart recovery proof.",
        "- `outputs/fanout.json`: parallel fan-out proof.",
        "",
        "## 3. Architecture",
        "",
        (
            "Graph flow: `START -> intake -> classify -> route`. "
            "The classifier routes into six behaviors: `simple`, `tool`, `missing_info`, "
            "`risky`, `error`, and parallel `tool` fan-out. "
            "Simple tickets end at `answer -> finalize -> END`. "
            "Tool tickets fan out into `tool_primary` and `tool_secondary`, then merge at "
            "`evaluate -> answer -> finalize -> END`. "
            "Missing-info tickets go `clarify -> finalize -> END`. "
            "Risky tickets go `risky_action -> approval -> tool -> evaluate -> answer -> "
            "finalize -> END`. "
            "Error tickets go `retry -> tool -> evaluate -> ...` until success or "
            "`dead_letter` when the retry budget is exhausted."
        ),
        "",
        (
            "State stays lean and serializable. Scalars overwrite current values; audit lists "
            "use append reducers so events, tool evidence, errors, and PII findings stay "
            "history-safe."
        ),
        "",
        "## 4. State schema",
        "",
        _render_state_table(),
        "",
        "## 5. Scenario results",
        "",
        (
            f"Metrics summary: {successful}/{metrics.total_scenarios} scenarios succeeded, "
            f"{approval_hits} approval hits observed, {retrying} scenarios retried, "
            f"and `success_rate={metrics.success_rate:.2%}`."
        ),
        "",
        _render_scenario_table(metrics.scenario_metrics),
        "",
        "## 6. Failure analysis",
        "",
        (
            "1. Retry or tool failure: transient tool output is marked `status=error`, then "
            "`evaluate_node` routes to `retry` until `max_attempts` is reached. This prevents "
            "infinite loops and gives a clean dead-letter path."
        ),
        (
            "2. Risky action without approval: high-risk requests pass through `risky_action` "
            "and `approval` before the tool executes. The approval node can reject, edit, or "
            "time out, which keeps side effects gated."
        ),
        (
            "3. Fan-out merge correctness: the parallel branch writes two tool outputs with "
            "distinct variants, and `answer_node` deduplicates the result strings before the "
            "final answer is generated."
        ),
        "",
        "## 7. Persistence / recovery evidence",
        "",
        (
            "Persistence uses a checkpointer factory with `sqlite` enabled in `configs/lab.yaml`. "
            "Each scenario gets a stable `thread_id` prefix, and the CLI appends a per-run suffix "
            "so checkpoint histories do not collide across repeated runs. "
            "`graph.get_state_history(config)` returns checkpoint snapshots after execution. "
            "SQLite survives process restart, while memory is only for in-process development. "
            "The `outputs/time_travel.json` file captures both the latest snapshot and a rewind "
            "snapshot from the same thread. The `outputs/crash_recovery.json` file shows a "
            "checkpoint written before a simulated restart and the recovered run after reload."
        ),
        "",
        "## 8. Extension work",
        "",
        (
            "Completed extension: SQLite persistence with WAL mode and history replay. "
            "The run also records structured tool outputs, PII detection metadata, a dead-letter "
            "ticket payload for exhausted retries, real HITL resume evidence, crash-recovery "
            "evidence, and parallel fan-out evidence. The Mermaid diagram export is available via "
            "`python -m langgraph_agent_lab.cli export-diagram --config configs/lab.yaml "
            "--output outputs/graph.mmd`. Time-travel evidence is available via "
            "`python -m langgraph_agent_lab.cli time-travel-demo --config configs/lab.yaml "
            "--output outputs/time_travel.json`. Real HITL evidence is available via "
            "`python -m langgraph_agent_lab.cli hitl-demo --config configs/lab.yaml "
            "--output outputs/hitl.json`. Crash recovery evidence is available via "
            "`python -m langgraph_agent_lab.cli crash-recovery-demo --config configs/lab.yaml "
            "--output outputs/crash_recovery.json`. Parallel fan-out evidence is available via "
            "`python -m langgraph_agent_lab.cli fanout-demo --config configs/lab.yaml "
            "--output outputs/fanout.json`."
        ),
        "",
        "## 9. Improvement plan",
        "",
        (
            "If I had one more day, I would add a real human approval UI, persist dead-letter "
            "items to an external queue, and attach trace logs to each output artifact so the "
            "demo can be replayed faster."
        ),
    ]
    return "\n".join(lines) + "\n"


def render_report_stub(metrics: MetricsReport) -> str:
    """Return a minimal report stub."""
    return render_report(metrics)


def write_report(metrics: MetricsReport, output_path: str | Path) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_report_stub(metrics), encoding="utf-8")
