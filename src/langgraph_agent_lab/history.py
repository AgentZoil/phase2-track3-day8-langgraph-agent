"""State history / time-travel helpers."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Protocol


class _SnapshotLike(Protocol):
    values: Mapping[str, object]


class _HistoryGraph(Protocol):
    def get_state_history(self, config: dict[str, object]) -> list[_SnapshotLike]: ...


def write_state_history(
    graph: _HistoryGraph,
    config: dict[str, object],
    output_path: str | Path,
    rewind_index: int = 1,
) -> dict[str, object]:
    """Export checkpoint snapshots and a rewind target."""
    history = list(graph.get_state_history(config))
    if not history:
        raise ValueError("No state history available")

    latest = history[0]
    rewind = history[rewind_index] if len(history) > rewind_index else latest
    configurable = config.get("configurable")
    if isinstance(configurable, dict):
        thread_id = str(configurable.get("thread_id", "unknown"))
    else:
        thread_id = "unknown"
    payload = {
        "thread_id": thread_id,
        "history_len": len(history),
        "latest_route": latest.values.get("route"),
        "rewind_route": rewind.values.get("route"),
        "latest_snapshot": latest.values,
        "rewind_snapshot": rewind.values,
    }

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return payload
