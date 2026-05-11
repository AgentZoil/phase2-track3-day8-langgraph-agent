"""Graph diagram export helpers."""

from __future__ import annotations

from pathlib import Path

from .graph import build_graph


def render_mermaid_diagram(checkpointer: object | None = None) -> str:
    """Render the compiled graph as Mermaid text."""
    graph = build_graph(checkpointer=checkpointer)
    return graph.get_graph().draw_mermaid()


def write_mermaid_diagram(
    output_path: str | Path, checkpointer: object | None = None
) -> None:
    """Write Mermaid diagram text to disk."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_mermaid_diagram(checkpointer=checkpointer), encoding="utf-8")
