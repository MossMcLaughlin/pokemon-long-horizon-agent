from __future__ import annotations

from dataclasses import dataclass

from pokemon_agent.controllers import Controller
from pokemon_agent.environment import GameEnvironment
from pokemon_agent.models import AgentObservation, StepStatus
from pokemon_agent.tracing import JsonlTraceWriter


@dataclass(frozen=True)
class RunSummary:
    steps: int
    stopped_by_controller: bool
    emulator_stopped: bool
    final_observation: AgentObservation


def run_controller(
    environment: GameEnvironment,
    controller: Controller,
    *,
    max_steps: int,
    skip_intro: bool = False,
    trace: JsonlTraceWriter | None = None,
) -> RunSummary:
    """Run any controller through the same bounded environment loop."""

    if max_steps < 1:
        raise ValueError("max_steps must be at least 1")
    observation = environment.reset(skip_intro=skip_intro)
    if trace:
        trace.record_reset(observation, environment.debug_snapshot())

    steps = 0
    stopped_by_controller = False
    emulator_stopped = False
    while steps < max_steps:
        action = controller.choose_action(observation)
        if action is None:
            stopped_by_controller = True
            break
        result = environment.step(action)
        steps += 1
        observation = result.observation
        if trace:
            trace.record_step(result)
        if result.status == StepStatus.EMULATOR_STOPPED:
            emulator_stopped = True
            break

    return RunSummary(
        steps=steps,
        stopped_by_controller=stopped_by_controller,
        emulator_stopped=emulator_stopped,
        final_observation=observation,
    )
