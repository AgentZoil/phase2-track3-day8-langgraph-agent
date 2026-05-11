"""CLI for the lab."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Annotated
from uuid import uuid4

import typer
import yaml  # type: ignore[import-untyped]
from langgraph.types import Command

from .diagram import write_mermaid_diagram
from .graph import build_graph
from .history import write_state_history
from .metrics import MetricsReport, metric_from_state, summarize_metrics, write_metrics
from .persistence import build_checkpointer
from .report import write_report
from .scenarios import load_scenarios
from .state import initial_state

app = typer.Typer(no_args_is_help=True)


@app.command("run-scenarios")
def run_scenarios(
    config: Annotated[Path, typer.Option("--config")],
    output: Annotated[Path, typer.Option("--output")],
) -> None:
    """Run all grading scenarios and write metrics JSON."""
    cfg = yaml.safe_load(config.read_text(encoding="utf-8"))
    scenarios = load_scenarios(cfg["scenarios_path"])
    checkpointer = build_checkpointer(cfg.get("checkpointer", "memory"), cfg.get("database_url"))
    graph = build_graph(checkpointer=checkpointer)
    metrics = []
    run_id = uuid4().hex[:8]
    for scenario in scenarios:
        state = initial_state(scenario)
        run_config = {"configurable": {"thread_id": f"{state['thread_id']}:{run_id}"}}
        final_state = graph.invoke(state, config=run_config)
        metrics.append(
            metric_from_state(
                final_state, scenario.expected_route.value, scenario.requires_approval
            )
        )
    report = summarize_metrics(metrics)
    write_metrics(report, output)
    if cfg.get("report_path"):
        write_report(report, cfg["report_path"])
    typer.echo(f"Wrote metrics to {output}")


@app.command("validate-metrics")
def validate_metrics(metrics: Annotated[Path, typer.Option("--metrics")]) -> None:
    """Validate metrics JSON schema for grading."""
    payload = json.loads(metrics.read_text(encoding="utf-8"))
    report = MetricsReport.model_validate(payload)
    if report.total_scenarios < 6:
        raise typer.BadParameter("Expected at least 6 scenarios")
    typer.echo(f"Metrics valid. success_rate={report.success_rate:.2%}")


@app.command("export-diagram")
def export_diagram(
    config: Annotated[Path, typer.Option("--config")],
    output: Annotated[Path, typer.Option("--output")],
) -> None:
    """Export Mermaid diagram for the compiled graph."""
    cfg = yaml.safe_load(config.read_text(encoding="utf-8"))
    checkpointer = build_checkpointer(cfg.get("checkpointer", "memory"), cfg.get("database_url"))
    write_mermaid_diagram(output, checkpointer=checkpointer)
    typer.echo(f"Wrote graph diagram to {output}")


@app.command("time-travel-demo")
def time_travel_demo(
    config: Annotated[Path, typer.Option("--config")],
    output: Annotated[Path, typer.Option("--output")],
) -> None:
    """Run one demo thread and export checkpoint history."""
    cfg = yaml.safe_load(config.read_text(encoding="utf-8"))
    scenarios = load_scenarios(cfg["scenarios_path"])
    scenario = scenarios[0]
    checkpointer = build_checkpointer(cfg.get("checkpointer", "memory"), cfg.get("database_url"))
    graph = build_graph(checkpointer=checkpointer)
    state = initial_state(scenario)
    thread_id = "time-travel-demo"
    run_config: dict[str, object] = {"configurable": {"thread_id": thread_id}}
    graph.invoke(state, config=run_config)
    payload = write_state_history(graph, run_config, output)
    typer.echo(
        f"Wrote history for {payload['thread_id']} with "
        f"{payload['history_len']} snapshots to {output}"
    )


@app.command("hitl-demo")
def hitl_demo(
    config: Annotated[Path, typer.Option("--config")],
    output: Annotated[Path, typer.Option("--output")],
) -> None:
    """Run an interrupt/resume approval round trip and export evidence."""
    previous = os.environ.get("LANGGRAPH_INTERRUPT")
    os.environ["LANGGRAPH_INTERRUPT"] = "true"
    cfg = yaml.safe_load(config.read_text(encoding="utf-8"))
    scenarios = load_scenarios(cfg["scenarios_path"])
    scenario = next(item for item in scenarios if item.requires_approval)
    checkpointer = build_checkpointer(cfg.get("checkpointer", "memory"), cfg.get("database_url"))
    graph = build_graph(checkpointer=checkpointer)
    state = initial_state(scenario)
    config_run = {"configurable": {"thread_id": f"hitl-demo:{uuid4().hex[:8]}"}}

    initial = graph.invoke(state, config=config_run)
    interrupt_info = initial.get("__interrupt__", [])
    if not interrupt_info:
        raise RuntimeError("Expected interrupt from approval flow")
    interrupt_id = interrupt_info[0].id
    resume_value = {
        interrupt_id: {
            "approved": True,
            "reviewer": "demo-reviewer",
            "comment": "approved in demo",
        }
    }
    final = graph.invoke(Command(resume=resume_value), config=config_run)
    payload = {
        "thread_id": config_run["configurable"]["thread_id"],
        "interrupt_id": interrupt_id,
        "approved": final.get("approval", {}).get("approved"),
        "final_answer": final.get("final_answer"),
        "approval": final.get("approval"),
    }
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    if previous is None:
        del os.environ["LANGGRAPH_INTERRUPT"]
    else:
        os.environ["LANGGRAPH_INTERRUPT"] = previous
    typer.echo(f"Wrote HITL evidence to {output}")


@app.command("fanout-demo")
def fanout_demo(
    config: Annotated[Path, typer.Option("--config")],
    output: Annotated[Path, typer.Option("--output")],
) -> None:
    """Run a tool scenario with parallel fan-out and export evidence."""
    cfg = yaml.safe_load(config.read_text(encoding="utf-8"))
    scenarios = load_scenarios(cfg["scenarios_path"])
    scenario = next(item for item in scenarios if item.expected_route.value == "tool")
    checkpointer = build_checkpointer(cfg.get("checkpointer", "memory"), cfg.get("database_url"))
    graph = build_graph(checkpointer=checkpointer)
    state = initial_state(scenario)
    config_run = {"configurable": {"thread_id": f"fanout-demo:{uuid4().hex[:8]}"}}
    final = graph.invoke(state, config=config_run)
    payload = {
        "thread_id": config_run["configurable"]["thread_id"],
        "route": final.get("route"),
        "tool_outputs": final.get("tool_outputs", []),
        "tool_results": final.get("tool_results", []),
        "final_answer": final.get("final_answer"),
    }
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    typer.echo(f"Wrote fan-out evidence to {output}")


if __name__ == "__main__":
    app()
