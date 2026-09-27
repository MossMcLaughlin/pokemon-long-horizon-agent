from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import TracebackType
from typing import Self

from pokemon_agent.controllers import ScriptedController
from pokemon_agent.models import (
    AgentObservation,
    Button,
    ButtonAction,
    DebugSnapshot,
    GameAction,
    GameMode,
    StepResult,
    StepStatus,
    Viewport,
)
from pokemon_agent.runtime import run_controller


class FakeEnvironment:
    def __init__(self) -> None:
        self.steps = 0

    def observation(self) -> AgentObservation:
        return AgentObservation(
            observation_id=self.steps,
            captured_at=datetime.now(UTC),
            frame_count=self.steps,
            mode=GameMode.OVERWORLD,
            viewport=Viewport(width=0, height=0),
            screen_hash=str(self.steps),
        )

    def reset(self, *, skip_intro: bool = False) -> AgentObservation:
        del skip_intro
        return self.observation()

    def observe(self) -> AgentObservation:
        return self.observation()

    def debug_snapshot(self) -> DebugSnapshot:
        return DebugSnapshot(
            captured_at=datetime.now(UTC),
            cartridge_title="TEST",
            rom_sha1="test",
            supported_rom=True,
            game_started=True,
            battle_state=0,
        )

    def step(self, action: GameAction) -> StepResult:
        self.steps += 1
        return StepResult(
            status=StepStatus.COMPLETED,
            action=action,
            observation=self.observation(),
            frames_advanced=1,
        )

    def tick(self, frames: int = 1, *, render: bool = True) -> bool:
        del frames, render
        return True

    def save_state(self, path: Path) -> None:
        del path

    def load_state(self, path: Path) -> AgentObservation:
        del path
        return self.observation()

    def screenshot(self, path: Path) -> None:
        del path

    def close(self) -> None:
        return None

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None


def test_scripted_controller_uses_bounded_runtime() -> None:
    actions = [ButtonAction(button=Button.DOWN), ButtonAction(button=Button.LEFT)]
    summary = run_controller(
        FakeEnvironment(),
        ScriptedController(actions),
        max_steps=10,
    )
    assert summary.steps == 2
    assert summary.stopped_by_controller is True
    assert summary.final_observation.observation_id == 2
