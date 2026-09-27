from __future__ import annotations

import hashlib
from pathlib import Path
from types import TracebackType
from typing import Any, Self

from pokemon_agent.environment.events import detect_events
from pokemon_agent.environment.extractor import Gen1StateExtractor
from pokemon_agent.environment.gen1 import (
    SUPPORTED_CARTRIDGE_TITLES,
    SUPPORTED_ROM_SHA1,
)
from pokemon_agent.models import (
    AgentObservation,
    ButtonAction,
    DebugSnapshot,
    GameAction,
    StepResult,
    StepStatus,
    WaitAction,
)


class PyBoyPokemonEnvironment:
    """Pokemon Red/Blue environment backed by PyBoy 2.x."""

    def __init__(
        self,
        rom_path: str | Path,
        *,
        window: str = "SDL2",
        scale: int = 4,
        no_input: bool = False,
        emulation_speed: int = 1,
        save_ram_on_close: bool = False,
    ) -> None:
        self.rom_path = Path(rom_path).expanduser().resolve()
        if not self.rom_path.is_file():
            raise FileNotFoundError(f"ROM file not found: {self.rom_path}")
        if scale < 1:
            raise ValueError("scale must be at least 1")
        if emulation_speed < 0:
            raise ValueError("emulation_speed cannot be negative")

        try:
            from pyboy import PyBoy
        except ImportError as error:
            raise RuntimeError(
                "PyBoy is not installed. Run `uv sync --extra dev` or "
                "`python -m pip install -e '.[dev]'`."
            ) from error

        self.rom_sha1 = self._sha1(self.rom_path)
        self.supported_rom = self.rom_sha1 in SUPPORTED_ROM_SHA1
        self._pyboy: Any = PyBoy(
            str(self.rom_path),
            window=window,
            scale=scale,
            no_input=no_input,
            title_status=True,
        )
        self._pyboy.set_emulation_speed(emulation_speed)
        self.cartridge_title = str(self._pyboy.cartridge_title).rstrip("\x00")
        if self.cartridge_title not in SUPPORTED_CARTRIDGE_TITLES:
            self._pyboy.stop(save=False)
            raise ValueError(
                "Expected an English Pokemon Red or Blue ROM, but cartridge title was "
                f"{self.cartridge_title!r}."
            )

        self._extractor = Gen1StateExtractor(
            cartridge_title=self.cartridge_title,
            rom_sha1=self.rom_sha1,
            supported_rom=self.supported_rom,
        )
        self._frames_advanced = 0
        self._initialized = False
        self._closed = False
        self._save_ram_on_close = save_ram_on_close

    @staticmethod
    def _sha1(path: Path) -> str:
        digest = hashlib.sha1()  # noqa: S324 - compatibility identifier, not security
        with path.open("rb") as file:
            for chunk in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def reset(self, *, skip_intro: bool = False) -> AgentObservation:
        self._ensure_open()
        if skip_intro:
            raise RuntimeError(
                "Automatic intro skipping is not implemented. Navigate once, save a "
                "checkpoint, and load that checkpoint for repeatable agent runs."
            )
        if self._initialized:
            raise RuntimeError(
                "A running PyBoy instance cannot return to power-on state. "
                "Create a new environment or load a checkpoint."
            )
        self.tick(1, render=True)
        self._initialized = True
        return self.observe()

    def observe(self) -> AgentObservation:
        self._ensure_open()
        return self._extractor.extract(self._pyboy, self.frame_count)

    def debug_snapshot(self) -> DebugSnapshot:
        return self._extractor.debug_snapshot()

    @property
    def frame_count(self) -> int:
        value = getattr(self._pyboy, "frame_count", self._frames_advanced)
        try:
            return int(value)
        except (TypeError, ValueError):
            return self._frames_advanced

    def step(self, action: GameAction) -> StepResult:
        self._ensure_open()
        if not self._initialized:
            raise RuntimeError("reset() must be called before step()")
        before = self.observe()
        if isinstance(action, ButtonAction):
            self._pyboy.button(action.button.value, delay=action.hold_frames)
            running = self.tick(action.frames, render=True)
            frames_advanced = action.frames
        elif isinstance(action, WaitAction):
            running = self.tick(action.frames, render=True)
            frames_advanced = action.frames
        else:  # pragma: no cover - protected by the public type boundary
            raise TypeError(f"Unsupported action: {type(action).__name__}")

        after = self.observe()
        return StepResult(
            status=StepStatus.COMPLETED if running else StepStatus.EMULATOR_STOPPED,
            action=action,
            observation=after,
            events=detect_events(before, after, action, emulator_running=running),
            frames_advanced=frames_advanced,
        )

    def tick(self, frames: int = 1, *, render: bool = True) -> bool:
        self._ensure_open()
        if frames < 1:
            raise ValueError("frames must be at least 1")
        running = bool(self._pyboy.tick(frames, render=render))
        self._frames_advanced += frames
        return running

    def save_state(self, path: Path) -> None:
        self._ensure_open()
        target = path.expanduser().resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("wb") as file:
            self._pyboy.save_state(file)

    def load_state(self, path: Path) -> AgentObservation:
        self._ensure_open()
        source = path.expanduser().resolve()
        if not source.is_file():
            raise FileNotFoundError(f"Save state not found: {source}")
        with source.open("rb") as file:
            self._pyboy.load_state(file)
        self._initialized = True
        self.tick(1, render=True)
        return self.observe()

    def screenshot(self, path: Path) -> None:
        self._ensure_open()
        target = path.expanduser().resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        self._pyboy.screen.image.save(target)

    def close(self) -> None:
        if self._closed:
            return
        self._pyboy.stop(save=self._save_ram_on_close)
        self._closed = True

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("environment is closed")

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()
