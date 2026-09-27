from __future__ import annotations

from pokemon_agent.models import (
    AgentObservation,
    Button,
    ButtonAction,
    EventKind,
    GameAction,
    GameEvent,
)

MOVEMENT_BUTTONS = {Button.UP, Button.DOWN, Button.LEFT, Button.RIGHT}


def detect_events(
    before: AgentObservation,
    after: AgentObservation,
    action: GameAction,
    *,
    emulator_running: bool,
) -> tuple[GameEvent, ...]:
    """Describe meaningful changes produced by one primitive action."""

    events: list[GameEvent] = []
    if before.mode != after.mode:
        events.append(
            GameEvent(
                kind=EventKind.MODE_CHANGED,
                message=f"mode changed from {before.mode.value} to {after.mode.value}",
                data={"before": before.mode.value, "after": after.mode.value},
            )
        )
    if before.map_id != after.map_id:
        events.append(
            GameEvent(
                kind=EventKind.MAP_CHANGED,
                message=f"map changed from {before.map_name or before.map_id} "
                f"to {after.map_name or after.map_id}",
                data={"before": before.map_id, "after": after.map_id},
            )
        )
    if before.player_position != after.player_position:
        before_position = before.player_position.model_dump() if before.player_position else None
        after_position = after.player_position.model_dump() if after.player_position else None
        events.append(
            GameEvent(
                kind=EventKind.POSITION_CHANGED,
                message=(
                    f"position changed from {before.player_position} to {after.player_position}"
                ),
                data={
                    "before": before_position,
                    "after": after_position,
                },
            )
        )
    elif (
        isinstance(action, ButtonAction)
        and action.button in MOVEMENT_BUTTONS
        and before.player_position is not None
        and before.map_id == after.map_id
        and before.mode == after.mode
    ):
        events.append(
            GameEvent(
                kind=EventKind.MOVEMENT_BLOCKED,
                message=f"{action.button.value} did not change the player position",
                data={"button": action.button.value},
            )
        )
    if before.party != after.party:
        events.append(GameEvent(kind=EventKind.PARTY_CHANGED, message="party state changed"))
    if before.inventory != after.inventory:
        events.append(
            GameEvent(kind=EventKind.INVENTORY_CHANGED, message="inventory state changed")
        )
    if before.screen_hash != after.screen_hash:
        events.append(GameEvent(kind=EventKind.SCREEN_CHANGED, message="rendered screen changed"))
    if not emulator_running:
        events.append(GameEvent(kind=EventKind.EMULATOR_STOPPED, message="emulator stopped"))
    return tuple(events)
