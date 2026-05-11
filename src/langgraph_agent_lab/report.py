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
        "- Name: not set",
        f"- Repo/commit: {_git_commit()}",
        f"- Date: {date.today().isoformat()}",
        "",
        "## 2. Architecture",
        "",
        (
            "Graph flow: `START -> intake -> classify -> route`. "
            "Simple tickets go `answer -> finalize -> END`. "
            "Tool tickets go `tool -> evaluate -> answer -> finalize -> END`. "
            "Missing-info tickets go `clarify -> finalize -> END`. "
            "Risky tickets go `risky_action -> approval -> tool -> evaluate -> "
            "answer -> finalize -> END`. "
            "Error tickets go `retry -> tool -> evaluate -> ...` until success or `dead_letter`."
        ),
        "",
        (
            "State stays lean and serializable. Scalars overwrite current values; audit lists "
            "use append reducers so events, tool evidence, and errors stay history-safe."
        ),
        "",
        "## 3. State schema",
        "",
        _render_state_table(),
        "",
        "## 4. Scenario results",
        "",
        (
            f"Metrics summary: {successful}/{metrics.total_scenarios} scenarios succeeded, "
            f"{approval_hits} approval hits observed, {retrying} scenarios retried."
        ),
        "",
        _render_scenario_table(metrics.scenario_metrics),
        "",
        "## 5. Failure analysis",
        "",
        (
            "1. Retry or tool failure: transient tool output is marked `status=error`, "
            "then `evaluate_node` routes to `retry` until `max_attempts` is reached. "
            "This prevents infinite loops and gives a clean dead-letter path."
        ),
        (
            "2. Risky action without approval: high-risk requests pass through `risky_action` "
            "and `approval` before the tool executes. The approval node can reject, edit, "
            "or time out, which keeps side effects gated."
        ),
        "",
        "## 6. Persistence / recovery evidence",
        "",
        (
            "Persistence uses a checkpointer factory with `sqlite` enabled in `configs/lab.yaml`. "
            "Each scenario gets a stable `thread_id`, and "
            "`graph.get_state_history(config)` returns checkpoint snapshots after execution. "
            "SQLite survives process restart, while memory is only for in-process development."
        ),
        "",
        "## 7. Extension work",
        "",
        (
            "Completed extension: SQLite persistence with WAL mode and history replay. "
            "The run also records structured tool outputs, PII detection metadata, and a "
            "dead-letter ticket payload for exhausted retries. Mermaid graph diagram export "
            "is available via `python -m langgraph_agent_lab.cli export-diagram --output "
            "outputs/graph.mmd`. Time-travel evidence is available via "
            "`python -m langgraph_agent_lab.cli time-travel-demo --output "
            "outputs/time_travel.json`. Real HITL evidence is available via "
            "`python -m langgraph_agent_lab.cli hitl-demo --output outputs/hitl.json`. "
            "Parallel fan-out evidence is available via "
            "`python -m langgraph_agent_lab.cli fanout-demo --output outputs/fanout.json`."
        ),
        "",
        "## 8. Improvement plan",
        "",
        (
            "If I had one more day, I would add a real human approval UI, persist dead-letter "
            "items to an external queue, and export a Mermaid diagram plus trace logs for "
            "easier demoing."
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
