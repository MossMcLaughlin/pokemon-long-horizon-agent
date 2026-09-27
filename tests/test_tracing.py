import json
from datetime import UTC, datetime

from pokemon_agent.models import AgentObservation, GameMode, Viewport
from pokemon_agent.tracing import JsonlTraceWriter


def test_jsonl_trace_is_append_only(tmp_path) -> None:
    trace_path = tmp_path / "run.jsonl"
    writer = JsonlTraceWriter(trace_path)
    observation = AgentObservation(
        observation_id=0,
        captured_at=datetime.now(UTC),
        frame_count=0,
        mode=GameMode.BOOT,
        viewport=Viewport(width=0, height=0),
        screen_hash="abc",
    )
    writer.record_observation(observation)
    writer.record_observation(observation)

    records = [json.loads(line) for line in trace_path.read_text().splitlines()]
    assert len(records) == 2
    assert all(record["kind"] == "observation" for record in records)
