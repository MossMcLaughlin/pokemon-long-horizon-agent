"""Minimal deterministic controller example.

Run with:
    python examples/scripted_walk.py /path/to/PokemonBlue.gb
"""

from __future__ import annotations

import sys
from pathlib import Path

from pokemon_agent.controllers import ScriptedController
from pokemon_agent.environment import PyBoyPokemonEnvironment
from pokemon_agent.models import Button, ButtonAction
from pokemon_agent.runtime import run_controller


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: python examples/scripted_walk.py /path/to/PokemonBlue.gb")
    actions = [
        ButtonAction(button=Button.DOWN),
        ButtonAction(button=Button.DOWN),
        ButtonAction(button=Button.LEFT),
    ]
    with PyBoyPokemonEnvironment(Path(sys.argv[1]), window="SDL2") as environment:
        summary = run_controller(
            environment,
            ScriptedController(actions),
            max_steps=len(actions),
        )
    print(summary)


if __name__ == "__main__":
    main()
