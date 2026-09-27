from __future__ import annotations

from pathlib import Path
from types import TracebackType
from typing import Protocol, Self

from pokemon_agent.models import AgentObservation, DebugSnapshot, GameAction, StepResult


class GameEnvironment(Protocol):
    """Controller-facing boundary implemented by game runtimes."""

    def reset(self, *, skip_intro: bool = False) -> AgentObservation:
        """Initialize a run and return its first observation."""

    def observe(self) -> AgentObservation:
        """Return a fresh, agent-visible observation without changing the game."""

    def debug_snapshot(self) -> DebugSnapshot:
        """Return privileged evaluator diagnostics."""

    def step(self, action: GameAction) -> StepResult:
        """Apply one validated primitive action."""

    def tick(self, frames: int = 1, *, render: bool = True) -> bool:
        """Advance emulator time and report whether it is still running."""

    def save_state(self, path: Path) -> None:
        """Save a complete emulator checkpoint."""

    def load_state(self, path: Path) -> AgentObservation:
        """Restore an emulator checkpoint and observe it."""

    def screenshot(self, path: Path) -> None:
        """Save the current rendered frame."""

    def close(self) -> None:
        """Release runtime resources."""

    def __enter__(self) -> Self: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...
