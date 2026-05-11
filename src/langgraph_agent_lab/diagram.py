"""Graph diagram export helpers."""

from __future__ import annotations

from pathlib import Path

from .graph import build_graph


def render_mermaid_diagram(checkpointer: object | None = None) -> str:
    """Render the workflow as Mermaid text.

    We keep this explicit instead of relying on LangGraph's auto-rendering so the
    exported artifact always shows the full lab workflow, including fan-out,
    retry, approval, and dead-letter paths.
    """
    _ = build_graph(checkpointer=checkpointer)
    return "\n".join(
        [
            "---",
            "config:",
            "  flowchart:",
            "    curve: linear",
            "---",
            "graph TD;",
            "\t__start__(<p>__start__</p>)",
            "\tintake(intake)",
            "\tclassify(classify)",
            "\tanswer(answer)",
            "\ttool(tool)",
            "\ttool_primary(tool_primary)",
            "\ttool_secondary(tool_secondary)",
            "\tevaluate(evaluate)",
            "\tclarify(clarify)",
            "\trisky_action(risky_action)",
            "\tapproval(approval)",
            "\tretry(retry)",
            "\tdead_letter(dead_letter)",
            "\tfinalize(finalize)",
            "\t__end__(<p>__end__</p>)",
            "\t__start__ --> intake;",
            "\tintake --> classify;",
            "\tclassify --> answer;",
            "\tclassify --> tool;",
            "\tclassify --> tool_primary;",
            "\tclassify --> tool_secondary;",
            "\tclassify --> clarify;",
            "\tclassify --> risky_action;",
            "\tclassify --> retry;",
            "\ttool_primary --> evaluate;",
            "\ttool_secondary --> evaluate;",
            "\ttool --> evaluate;",
            "\tevaluate --> answer;",
            "\tevaluate --> retry;",
            "\tclarify --> finalize;",
            "\trisky_action --> approval;",
            "\tapproval --> tool;",
            "\tapproval --> clarify;",
            "\tretry --> tool;",
            "\tretry --> dead_letter;",
            "\tanswer --> finalize;",
            "\tdead_letter --> finalize;",
            "\tfinalize --> __end__;",
            "\tclassDef default fill:#f2f0ff,line-height:1.2",
            "\tclassDef first fill-opacity:0",
            "\tclassDef last fill:#bfb6fc",
            "",
        ]
    )


def write_mermaid_diagram(
    output_path: str | Path, checkpointer: object | None = None
) -> None:
    """Write Mermaid diagram text to disk."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_mermaid_diagram(checkpointer=checkpointer), encoding="utf-8")
