from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ImmutableModel(BaseModel):
    """Base model for values crossing the environment/controller boundary."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class Button(StrEnum):
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"
    A = "a"
    B = "b"
    START = "start"
    SELECT = "select"


class ButtonAction(ImmutableModel):
    """Press a Game Boy button and then allow the game to settle."""

    type: Literal["button"] = "button"
    button: Button
    hold_frames: int = Field(default=1, ge=1, le=120)
    frames: int = Field(default=16, ge=1, le=600)

    @model_validator(mode="after")
    def hold_must_fit_inside_step(self) -> ButtonAction:
        if self.hold_frames > self.frames:
            raise ValueError("hold_frames cannot exceed frames")
        return self


class WaitAction(ImmutableModel):
    """Advance the emulator without sending controller input."""

    type: Literal["wait"] = "wait"
    frames: int = Field(default=1, ge=1, le=3600)


GameAction = Annotated[ButtonAction | WaitAction, Field(discriminator="type")]


class GameMode(StrEnum):
    BOOT = "boot"
    OVERWORLD = "overworld"
    DIALOGUE = "dialogue"
    MENU = "menu"
    BATTLE = "battle"
    TRANSITION = "transition"
    UNKNOWN = "unknown"


class CellKind(StrEnum):
    WALKABLE = "walkable"
    BLOCKED = "blocked"
    UNKNOWN = "unknown"


class Position(ImmutableModel):
    x: int
    y: int


class VisibleSprite(ImmutableModel):
    """A hardware sprite currently overlapping the visible Game Boy screen."""

    index: int = Field(ge=0, le=39)
    screen_x: int
    screen_y: int
    width: int
    height: int
    tile_identifier: int = Field(ge=0, le=255)


class Viewport(ImmutableModel):
    """Local visual representation exposed to a controller."""

    width: int = Field(ge=0)
    height: int = Field(ge=0)
    tile_ids: tuple[tuple[int, ...], ...] = ()
    walkable: tuple[tuple[bool | None, ...], ...] = ()
    semantic: tuple[tuple[CellKind, ...], ...] = ()
    sprites: tuple[VisibleSprite, ...] = ()

    @model_validator(mode="after")
    def matrices_match_dimensions(self) -> Viewport:
        for name, matrix in (
            ("tile_ids", self.tile_ids),
            ("walkable", self.walkable),
            ("semantic", self.semantic),
        ):
            if matrix and len(matrix) != self.height:
                raise ValueError(f"{name} height does not match viewport height")
            if matrix and any(len(row) != self.width for row in matrix):
                raise ValueError(f"{name} width does not match viewport width")
        return self


class PartyMember(ImmutableModel):
    slot: int = Field(ge=0, le=5)
    species_id: int
    species_name: str | None = None
    nickname: str | None = None
    level: int = Field(ge=0, le=100)
    hp: int = Field(ge=0)
    max_hp: int = Field(ge=0)
    status: int = Field(ge=0, le=255)
    move_ids: tuple[int, ...] = ()
    move_names: tuple[str | None, ...] = ()
    pp: tuple[int, ...] = ()


class InventoryItem(ImmutableModel):
    slot: int = Field(ge=0)
    item_id: int
    item_name: str | None = None
    quantity: int = Field(ge=0)


class AgentObservation(ImmutableModel):
    """State available to a human, script, or future agent controller."""

    schema_version: Literal[1] = 1
    observation_id: int = Field(ge=0)
    captured_at: datetime
    frame_count: int = Field(ge=0)
    mode: GameMode
    map_id: int | None = None
    map_name: str | None = None
    player_position: Position | None = None
    viewport: Viewport
    party: tuple[PartyMember, ...] = ()
    inventory: tuple[InventoryItem, ...] = ()
    money: int | None = None
    screen_hash: str
    warnings: tuple[str, ...] = ()


class DebugSnapshot(ImmutableModel):
    """Privileged diagnostics kept outside the default agent observation."""

    captured_at: datetime
    cartridge_title: str
    rom_sha1: str
    supported_rom: bool
    game_started: bool
    battle_state: int
    raw: dict[str, Any] = Field(default_factory=dict)
    warnings: tuple[str, ...] = ()


class EventKind(StrEnum):
    MODE_CHANGED = "mode_changed"
    MAP_CHANGED = "map_changed"
    POSITION_CHANGED = "position_changed"
    MOVEMENT_BLOCKED = "movement_blocked"
    PARTY_CHANGED = "party_changed"
    INVENTORY_CHANGED = "inventory_changed"
    SCREEN_CHANGED = "screen_changed"
    EMULATOR_STOPPED = "emulator_stopped"


class GameEvent(ImmutableModel):
    kind: EventKind
    message: str
    data: dict[str, Any] = Field(default_factory=dict)


class StepStatus(StrEnum):
    COMPLETED = "completed"
    EMULATOR_STOPPED = "emulator_stopped"


class StepResult(ImmutableModel):
    status: StepStatus
    action: ButtonAction | WaitAction
    observation: AgentObservation
    events: tuple[GameEvent, ...] = ()
    frames_advanced: int = Field(ge=0)
