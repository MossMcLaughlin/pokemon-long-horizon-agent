from __future__ import annotations

from collections.abc import Iterable, Iterator

from pokemon_agent.models import AgentObservation, GameAction


class ScriptedController:
    """Deterministic controller useful for smoke tests and recorded scenarios."""

    def __init__(self, actions: Iterable[GameAction]) -> None:
        self._actions: Iterator[GameAction] = iter(actions)

    def choose_action(self, observation: AgentObservation) -> GameAction | None:
        del observation
        return next(self._actions, None)
