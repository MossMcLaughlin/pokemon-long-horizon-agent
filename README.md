# Pokemon Long-Horizon Agent

A clean environment and evaluation foundation for a long-horizon agent that
plays Pokemon Red or Blue through [PyBoy](https://github.com/Baekalfen/PyBoy).

The current milestone is intentionally environment-first: a human, a scripted
controller, and a future LLM agent all operate through the same typed interface.
The repository does **not** contain or download a ROM.

## What works in this first pass

- Real-time manual play in PyBoy's SDL2 window.
- Command-by-command manual control through the agent-facing `step()` API.
- Typed, JSON-serializable observations and actions.
- Visible 20x18 tile IDs, collision-derived semantic cells, and on-screen sprites.
- Player map/coordinates, battle state, and schema slots for party, inventory,
  and money on supported English Pokemon Red/Blue ROMs.
- Save/load emulator checkpoints and PNG screenshots.
- Append-only JSONL traces with detected state changes.
- A scripted controller and generic runner that use the same interface a future
  agent will implement.
- Unit tests that do not require a ROM.

Semantic terrain labels are currently conservative: cells are `walkable`,
`blocked`, or `unknown`. PyBoy 2.7 does not expose party, inventory, money, or
Pokemon name tables through its Gen 1 wrapper, so those fields currently report
as unavailable with an observation warning. Direct, tested memory extraction and
identifying grass, doors, ledges, water, NPC roles, and dialogue are the next
environment milestone.

## Requirements

- Python 3.11+
- A legally obtained English Pokemon Red or Blue ROM
- A desktop environment for the SDL2 play window

PyBoy 2.7 is pinned to the supported major version. The known reference ROM
hashes are displayed by `doctor`, but the project never downloads game data.

## Install

Using `uv`:

```bash
uv sync --extra dev
```

Using `pip`:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

Set the ROM path either on the command line or in your shell:

```bash
export POKEMON_ROM_PATH=/absolute/path/to/PokemonBlue.gb
```

ROMs, battery saves, save states, screenshots, recordings, and run traces are
ignored by Git.

## Manual play

Play normally in PyBoy's window:

```bash
pokemon-agent play --rom "$POKEMON_ROM_PATH"
```

PyBoy's default controls are arrow keys for movement and its configured A/B,
Start, and Select keys. Close the window or press Ctrl-C to stop.

To test the exact action interface an agent will use:

```bash
pokemon-agent manual --rom "$POKEMON_ROM_PATH"
```

The manual console accepts:

```text
up, down, left, right, a, b, start, select
wait [frames]
show
json
grid
save PATH
load PATH
shot PATH
help
quit
```

Append a frame count to a button command when needed, for example `down 24`.
After navigating the opening once, use `save saves/bedroom.state`. Future runs
can start there with `--state saves/bedroom.state`; this avoids pretending that
PyBoy's current Gen 1 wrapper can automate the opening sequence.

## Validate the installation

```bash
pokemon-agent doctor --rom "$POKEMON_ROM_PATH"
pytest
ruff check .
```

`doctor` verifies the file, computes its SHA-1, opens it headlessly, confirms
the cartridge title, and prints a compact observation. It does not modify the
ROM.

## Record a trace

```bash
pokemon-agent manual \
  --rom "$POKEMON_ROM_PATH" \
  --trace runs/manual.jsonl
```

Each trace record contains the action, resulting observation, detected events,
and timestamps. This becomes the basis for replay, evaluation, stuck-state
detection, and later LLM cost analysis.

## Agent-facing boundary

```python
from pokemon_agent.environment import PyBoyPokemonEnvironment
from pokemon_agent.models import Button, ButtonAction

with PyBoyPokemonEnvironment("/path/to/PokemonBlue.gb", window="null") as env:
    observation = env.reset()
    result = env.step(ButtonAction(button=Button.DOWN))
    print(result.observation.model_dump_json(indent=2))
```

The future agent will implement the `Controller` protocol and receive only an
`AgentObservation`. Debug information is available separately to evaluators.

## Architecture

```text
Controller (human / script / future agent)
                    |
              typed GameAction
                    v
          GameEnvironment protocol
                    |
        PyBoyPokemonEnvironment
          |       |        |
       input   extractor  checkpoints
                    |
          AgentObservation + events
                    |
               JSONL trace
```

See [`docs/ENVIRONMENT.md`](docs/ENVIRONMENT.md) for observation semantics,
known limitations, and the next implementation steps.

## Legal note

Pokemon is a trademark of Nintendo/Creatures Inc./GAME FREAK inc. This
independent educational project is not affiliated with or endorsed by them.
Do not commit or distribute copyrighted ROMs or extracted game assets.
