from __future__ import annotations

import os
import shlex
from importlib import metadata
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.syntax import Syntax
from rich.table import Table

from pokemon_agent.environment import PyBoyPokemonEnvironment
from pokemon_agent.environment.gen1 import SUPPORTED_ROM_SHA1
from pokemon_agent.models import AgentObservation, Button, ButtonAction, GameAction, WaitAction
from pokemon_agent.tracing import JsonlTraceWriter

app = typer.Typer(
    no_args_is_help=True,
    help="Manually play and inspect Pokemon Red/Blue through the agent environment.",
)
console = Console()

RomOption = Annotated[
    Path | None,
    typer.Option("--rom", help="Path to a legally obtained Pokemon Red/Blue ROM."),
]


def _resolve_rom(rom: Path | None) -> Path:
    configured_path = os.environ.get("POKEMON_ROM_PATH")
    value = rom or (Path(configured_path) if configured_path else None)
    if value is None:
        console.print("[red]No ROM path supplied.[/red] Use --rom PATH or set POKEMON_ROM_PATH.")
        raise typer.Exit(code=2)
    path = value.expanduser().resolve()
    if not path.is_file():
        console.print(f"[red]ROM file not found:[/red] {path}")
        raise typer.Exit(code=2)
    return path


def _summary(observation: AgentObservation) -> Table:
    table = Table(title=f"Observation {observation.observation_id}", show_header=False)
    table.add_column("Field", style="cyan")
    table.add_column("Value")
    location = observation.map_name or (
        str(observation.map_id) if observation.map_id is not None else "unavailable"
    )
    position = (
        f"({observation.player_position.x}, {observation.player_position.y})"
        if observation.player_position
        else "unavailable"
    )
    table.add_row("Mode", observation.mode.value)
    table.add_row("Location", location)
    table.add_row("Position", position)
    table.add_row("Party", str(len(observation.party)))
    table.add_row("Inventory", str(len(observation.inventory)))
    money = str(observation.money) if observation.money is not None else "unavailable"
    table.add_row("Money", money)
    table.add_row("Sprites", str(len(observation.viewport.sprites)))
    table.add_row("Screen hash", observation.screen_hash)
    if observation.warnings:
        table.add_row("Warnings", "\n".join(observation.warnings))
    return table


def _grid(observation: AgentObservation) -> str:
    symbols = {"walkable": ".", "blocked": "#", "unknown": "?"}
    rows = [[symbols[cell.value] for cell in row] for row in observation.viewport.semantic]
    for sprite in observation.viewport.sprites:
        row = min(max(sprite.screen_y // 8, 0), max(observation.viewport.height - 1, 0))
        column = min(max(sprite.screen_x // 8, 0), max(observation.viewport.width - 1, 0))
        if rows and 0 <= row < len(rows) and 0 <= column < len(rows[row]):
            rows[row][column] = "S"
    return "\n".join("".join(row) for row in rows) or "<viewport unavailable>"


@app.command()
def play(
    rom: RomOption = None,
    scale: Annotated[int, typer.Option(min=1, max=10)] = 4,
    speed: Annotated[int, typer.Option(min=0, help="1 is real time; 0 is unlimited.")] = 1,
    state: Annotated[
        Path | None, typer.Option(help="Optional emulator checkpoint to load.")
    ] = None,
    trace: Annotated[Path | None, typer.Option(help="Optional JSONL observation trace.")] = None,
    observe_every: Annotated[int, typer.Option(min=1, help="Frames between trace snapshots.")] = 60,
    save_ram: Annotated[
        bool, typer.Option(help="Persist the cartridge battery RAM on close.")
    ] = False,
) -> None:
    """Play in a normal real-time PyBoy window."""

    path = _resolve_rom(rom)
    writer = JsonlTraceWriter(trace) if trace else None
    with PyBoyPokemonEnvironment(
        path,
        window="SDL2",
        scale=scale,
        no_input=False,
        emulation_speed=speed,
        save_ram_on_close=save_ram,
    ) as environment:
        observation = environment.load_state(state) if state else environment.reset()
        if writer:
            writer.record_reset(observation, environment.debug_snapshot())
        console.print(_summary(observation))
        console.print("[dim]Close the PyBoy window or press Ctrl-C to stop.[/dim]")
        frames = 0
        try:
            while environment.tick(1, render=True):
                frames += 1
                if writer and frames % observe_every == 0:
                    writer.record_observation(environment.observe())
        except KeyboardInterrupt:
            pass


@app.command()
def manual(
    rom: RomOption = None,
    scale: Annotated[int, typer.Option(min=1, max=10)] = 4,
    state: Annotated[
        Path | None, typer.Option(help="Optional emulator checkpoint to load.")
    ] = None,
    trace: Annotated[Path | None, typer.Option(help="Optional JSONL step trace.")] = None,
) -> None:
    """Drive the exact agent-facing step interface from a command prompt."""

    path = _resolve_rom(rom)
    writer = JsonlTraceWriter(trace) if trace else None
    with PyBoyPokemonEnvironment(
        path,
        window="SDL2",
        scale=scale,
        no_input=True,
        emulation_speed=0,
    ) as environment:
        observation = environment.load_state(state) if state else environment.reset()
        if writer:
            writer.record_reset(observation, environment.debug_snapshot())
        console.print(_summary(observation))
        console.print(
            Panel(
                "Commands: up/down/left/right/a/b/start/select [frames], "
                "wait [frames], show, json, grid, save PATH, load PATH, "
                "shot PATH, help, quit",
                title="Manual controller",
            )
        )

        while True:
            try:
                parts = shlex.split(Prompt.ask("[bold green]pokemon[/bold green]"))
            except (EOFError, KeyboardInterrupt):
                console.print()
                break
            if not parts:
                continue
            command = parts[0].lower()
            try:
                if command in {"quit", "exit", "q"}:
                    break
                if command in {"help", "?"}:
                    console.print(
                        "Buttons optionally accept total frames, e.g. `down 24`. "
                        "Use `json` for the complete agent observation."
                    )
                    continue
                if command == "show":
                    observation = environment.observe()
                    console.print(_summary(observation))
                    continue
                if command == "json":
                    observation = environment.observe()
                    console.print(Syntax(observation.model_dump_json(indent=2), "json"))
                    continue
                if command == "grid":
                    observation = environment.observe()
                    console.print(_grid(observation))
                    continue
                if command in {"save", "load", "shot"}:
                    if len(parts) != 2:
                        raise ValueError(f"usage: {command} PATH")
                    target = Path(parts[1])
                    if command == "save":
                        environment.save_state(target)
                        console.print(f"Saved checkpoint to {target.expanduser().resolve()}")
                    elif command == "load":
                        observation = environment.load_state(target)
                        console.print(_summary(observation))
                    else:
                        environment.screenshot(target)
                        console.print(f"Saved screenshot to {target.expanduser().resolve()}")
                    continue

                frames = int(parts[1]) if len(parts) > 1 else 16
                action: GameAction
                if command == "wait":
                    action = WaitAction(frames=frames)
                else:
                    action = ButtonAction(button=Button(command), frames=frames)
                result = environment.step(action)
                observation = result.observation
                if writer:
                    writer.record_step(result)
                console.print(_summary(observation))
                if result.events:
                    console.print(
                        "[dim]Events: "
                        + ", ".join(event.kind.value for event in result.events)
                        + "[/dim]"
                    )
            except (ValueError, FileNotFoundError, RuntimeError) as error:
                console.print(f"[red]{error}[/red]")


@app.command()
def doctor(rom: RomOption = None) -> None:
    """Validate the installation, ROM identity, and headless observation path."""

    path = _resolve_rom(rom)
    try:
        pyboy_version = metadata.version("pyboy")
    except metadata.PackageNotFoundError:
        console.print("[red]PyBoy is not installed.[/red]")
        raise typer.Exit(code=1) from None

    try:
        with PyBoyPokemonEnvironment(
            path,
            window="null",
            no_input=True,
            emulation_speed=0,
        ) as environment:
            observation = environment.reset(skip_intro=False)
            debug = environment.debug_snapshot()
            console.print(f"PyBoy: [green]{pyboy_version}[/green]")
            console.print(f"Cartridge: [green]{debug.cartridge_title}[/green]")
            console.print(f"SHA-1: {debug.rom_sha1}")
            if debug.supported_rom:
                console.print(f"Profile: [green]{SUPPORTED_ROM_SHA1[debug.rom_sha1]}[/green]")
            else:
                console.print(
                    "[yellow]Unknown ROM hash; basic emulation may work, but memory "
                    "addresses are not guaranteed.[/yellow]"
                )
            console.print(_summary(observation))
    except (FileNotFoundError, RuntimeError, ValueError) as error:
        console.print(f"[red]Validation failed:[/red] {error}")
        raise typer.Exit(code=1) from error


if __name__ == "__main__":
    app()
