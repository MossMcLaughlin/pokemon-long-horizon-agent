from __future__ import annotations

from typing import Protocol

from pokemon_agent.models import AgentObservation, GameAction


class Controller(Protocol):
    """Minimal contract implemented by scripts and future agents."""

    def choose_action(self, observation: AgentObservation) -> GameAction | None:
        """Return the next primitive action, or None to stop the run."""
