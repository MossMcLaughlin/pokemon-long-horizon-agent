from datetime import UTC, datetime

from pokemon_agent.environment.events import detect_events
from pokemon_agent.models import (
    AgentObservation,
    Button,
    ButtonAction,
    EventKind,
    GameMode,
    Position,
    Viewport,
)


def observation(
    *, x: int, mode: GameMode = GameMode.OVERWORLD, screen: str = "a"
) -> AgentObservation:
    return AgentObservation(
        observation_id=1,
        captured_at=datetime.now(UTC),
        frame_count=10,
        mode=mode,
        map_id=1,
        map_name="TEST_MAP",
        player_position=Position(x=x, y=2),
        viewport=Viewport(width=0, height=0),
        screen_hash=screen,
    )


def test_detects_position_change() -> None:
    events = detect_events(
        observation(x=1),
        observation(x=2, screen="b"),
        ButtonAction(button=Button.RIGHT),
        emulator_running=True,
    )
    kinds = {event.kind for event in events}
    assert EventKind.POSITION_CHANGED in kinds
    assert EventKind.MOVEMENT_BLOCKED not in kinds
    assert EventKind.SCREEN_CHANGED in kinds


def test_detects_blocked_movement() -> None:
    events = detect_events(
        observation(x=1),
        observation(x=1),
        ButtonAction(button=Button.RIGHT),
        emulator_running=True,
    )
    assert EventKind.MOVEMENT_BLOCKED in {event.kind for event in events}
