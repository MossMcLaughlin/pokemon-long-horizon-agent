# Codex project instructions

## Project goal

Build a portfolio-quality long-horizon agent that operates Pokemon Red or Blue
through a structured, observable PyBoy environment. The initial game milestone
is to start a new game and defeat Brock.

## Current milestone

Finish and validate the manually playable environment before implementing LLM
planning. A human, scripted controller, and future agent must all use the same
public `GameEnvironment` interface.

## Design constraints

- Keep emulator integration separate from agent reasoning.
- Preserve a distinction between agent-visible observations and privileged
  evaluator/debug state.
- Prefer typed actions and structured model outputs over parsing free-form text.
- Store immutable traces; never treat prompt memory as the source of truth.
- Use deterministic code for button timing, navigation, dialogue advancement,
  validation, and other mechanics that do not need model judgment.
- Make skills bounded and interruptible when the game changes unexpectedly.
- Do not add large frameworks until a measured requirement justifies them.
- Never commit ROMs, save states, secrets, or copyrighted game assets.

## Engineering workflow

Before a non-trivial change:

1. Inspect the relevant files.
2. State the smallest implementation plan.
3. Implement it.
4. Run relevant tests and checks.
5. Summarize changes, uncertainties, and the next useful step.

## Quality bar

- Python 3.11+
- Type hints for public interfaces
- Pydantic models at external boundaries
- pytest for tests
- Ruff for linting and formatting
- No hidden network calls in the environment layer
- Useful errors when a ROM or optional runtime dependency is unavailable

