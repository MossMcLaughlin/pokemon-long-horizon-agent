# Environment contract

## Design intent

The environment should be finished infrastructure from the agent developer's
point of view. Emulator details stay behind `GameEnvironment`; agent work should
focus on planning, memory, skill selection, interruption, and evaluation.

## Public observation

`AgentObservation` contains information intended for the controller:

- gameplay mode;
- map identity and player coordinates after the game has started;
- the visible 20x18 PyBoy game area;
- conservative collision-derived semantic cells;
- on-screen hardware sprites;
- reserved party, inventory, and money fields (reported as unavailable until
  the next memory-extraction milestone);
- a screen hash for change and loop detection.

The first pass intentionally retains raw numeric tile and sprite identifiers.
Optional name fields remain `null` until a separately licensed metadata source
is added. This prevents the extractor from pretending it understands more than
it does.

## Debug state

`DebugSnapshot` is obtained separately and must not be inserted into an agent
prompt by default. It includes raw memory flags, cartridge information, ROM
hash, and extractor warnings. Future milestone/event flags belong here.

## Game-mode detection

Mode detection is currently conservative:

- before Pokemon's game-start flag: `boot`;
- `wIsInBattle` non-zero: `battle`;
- visible dialogue-arrow tile: `dialogue`;
- otherwise, after game start: `overworld`;
- unexpected values: `unknown`.

Menus and transitions will need additional state-machine work before an agent
can reliably automate every interface.

## Action timing

`ButtonAction` separates how long a button is held from how many total frames
the emulator advances. This allows the runtime to tune movement and menu inputs
without changing the controller contract.

Every bounded skill built later must stop early when observations indicate an
unexpected mode change, battle, dialogue, blocked movement, or completed goal.

PyBoy 2.7's Gen 1 `start_game()` hook does not navigate the opening sequence.
For repeatable runs, manually reach a playable state once, save an emulator
checkpoint, and load it for later sessions.

## Supported memory profile

The initial address profile targets the canonical English Pokemon Red/Blue
ROMs:

- `wIsInBattle`: `0xD057`
- `wStatusFlags6`: `0xD732`
- `wCurMap`: `0xD35E`
- `wYCoord`: `0xD361`
- `wXCoord`: `0xD362`

The CLI reports the ROM SHA-1. Unknown hashes produce a warning rather than
silently claiming full compatibility.

## Next environment milestone

Before implementing the LLM planner, add and validate:

1. visible dialogue decoding;
2. menu and transition mode detection;
3. semantic terrain classification for grass, doors, ledges, and water;
4. stable player/NPC entity identification;
5. recorded trace replay and golden observations from legal local save states.
