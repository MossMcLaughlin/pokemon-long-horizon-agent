from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pokemon_agent.models import AgentObservation, DebugSnapshot, StepResult


class JsonlTraceWriter:
    """Append-only structured trace writer."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record_reset(
        self,
        observation: AgentObservation,
        debug: DebugSnapshot | None = None,
    ) -> None:
        record: dict[str, Any] = {
            "schema_version": 1,
            "kind": "reset",
            "recorded_at": datetime.now(UTC).isoformat(),
            "observation": observation.model_dump(mode="json"),
        }
        if debug is not None:
            record["debug"] = debug.model_dump(mode="json")
        self._append(record)

    def record_step(self, result: StepResult) -> None:
        self._append(
            {
                "schema_version": 1,
                "kind": "step",
                "recorded_at": datetime.now(UTC).isoformat(),
                "result": result.model_dump(mode="json"),
            }
        )

    def record_observation(self, observation: AgentObservation) -> None:
        self._append(
            {
                "schema_version": 1,
                "kind": "observation",
                "recorded_at": datetime.now(UTC).isoformat(),
                "observation": observation.model_dump(mode="json"),
            }
        )

    def _append(self, record: dict[str, Any]) -> None:
        with self.path.open("a", encoding="utf-8") as file:
            json.dump(record, file, separators=(",", ":"), ensure_ascii=False)
            file.write("\n")
