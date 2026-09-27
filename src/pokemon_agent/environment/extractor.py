from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

from pokemon_agent.environment.gen1 import MEMORY
from pokemon_agent.models import (
    AgentObservation,
    CellKind,
    DebugSnapshot,
    GameMode,
    InventoryItem,
    PartyMember,
    Position,
    Viewport,
    VisibleSprite,
)


class Gen1Lookups:
    """Names supplied by PyBoy, isolated so the extractor remains testable."""

    def __init__(
        self,
        *,
        map_names: Mapping[int, str] | None = None,
        species_names: Mapping[int, str] | None = None,
        move_names: Mapping[int, str] | None = None,
        item_names: Mapping[int, str] | None = None,
        text_decoding: Mapping[int, str] | None = None,
    ) -> None:
        self.map_names = dict(map_names or {})
        self.species_names = dict(species_names or {})
        self.move_names = dict(move_names or {})
        self.item_names = dict(item_names or {})
        self.text_decoding = dict(text_decoding or {})

    @classmethod
    def from_pyboy(cls) -> Gen1Lookups:
        # PyBoy 2.7 intentionally exposes raw identifiers but does not ship
        # Pokemon data tables. Keeping the lookup seam here lets a later,
        # independently licensed metadata package supply friendly names.
        return cls()


class Gen1StateExtractor:
    """Build conservative public observations and separate debug snapshots."""

    def __init__(
        self,
        *,
        cartridge_title: str,
        rom_sha1: str,
        supported_rom: bool,
        lookups: Gen1Lookups | None = None,
    ) -> None:
        self.cartridge_title = cartridge_title
        self.rom_sha1 = rom_sha1
        self.supported_rom = supported_rom
        self.lookups = lookups or Gen1Lookups.from_pyboy()
        self._observation_id = 0
        self._last_debug: DebugSnapshot | None = None

    def extract(self, pyboy: Any, frame_count: int) -> AgentObservation:
        now = datetime.now(UTC)
        warnings: list[str] = []
        game_started = bool(
            int(pyboy.memory[MEMORY.game_started_flags]) & (1 << MEMORY.game_started_bit)
        )
        battle_state = int(pyboy.memory[MEMORY.battle_state])
        mode = self._detect_mode(pyboy, game_started=game_started, battle_state=battle_state)

        map_id: int | None = None
        map_name: str | None = None
        position: Position | None = None
        if game_started:
            map_id = int(pyboy.memory[MEMORY.map_id])
            map_name = self.lookups.map_names.get(map_id)
            position = Position(
                x=int(pyboy.memory[MEMORY.player_x]),
                y=int(pyboy.memory[MEMORY.player_y]),
            )

        tile_ids = self._read_game_area(pyboy, warnings)
        walkable = self._read_collision(pyboy, tile_ids, warnings)
        semantic = tuple(
            tuple(
                CellKind.UNKNOWN
                if value is None
                else (CellKind.WALKABLE if value else CellKind.BLOCKED)
                for value in row
            )
            for row in walkable
        )
        height = len(tile_ids)
        width = len(tile_ids[0]) if tile_ids else 0
        viewport = Viewport(
            width=width,
            height=height,
            tile_ids=tile_ids,
            walkable=walkable,
            semantic=semantic,
            sprites=self._read_sprites(pyboy, warnings),
        )

        party: tuple[PartyMember, ...] = ()
        inventory: tuple[InventoryItem, ...] = ()
        money: int | None = None
        if game_started:
            party = self._read_party(pyboy, warnings)
            inventory = self._read_inventory(pyboy, warnings)
            money = self._read_money(pyboy, warnings)

        observation = AgentObservation(
            observation_id=self._observation_id,
            captured_at=now,
            frame_count=max(0, frame_count),
            mode=mode,
            map_id=map_id,
            map_name=map_name,
            player_position=position,
            viewport=viewport,
            party=party,
            inventory=inventory,
            money=money,
            screen_hash=self._screen_hash(pyboy, tile_ids),
            warnings=tuple(warnings),
        )
        self._observation_id += 1
        self._last_debug = DebugSnapshot(
            captured_at=now,
            cartridge_title=self.cartridge_title,
            rom_sha1=self.rom_sha1,
            supported_rom=self.supported_rom,
            game_started=game_started,
            battle_state=battle_state,
            raw={
                "map_id": map_id,
                "player_x": position.x if position else None,
                "player_y": position.y if position else None,
            },
            warnings=tuple(warnings),
        )
        return observation

    def debug_snapshot(self) -> DebugSnapshot:
        if self._last_debug is None:
            raise RuntimeError("observe() must be called before debug_snapshot()")
        return self._last_debug

    @staticmethod
    def _detect_mode(pyboy: Any, *, game_started: bool, battle_state: int) -> GameMode:
        if not game_started:
            return GameMode.BOOT
        if battle_state in {1, 2, 255}:
            return GameMode.BATTLE
        if battle_state not in {0, 1, 2, 255}:
            return GameMode.UNKNOWN
        try:
            if int(pyboy.tilemap_window[18, 16]) == 238:
                return GameMode.DIALOGUE
        except (AttributeError, IndexError, TypeError, ValueError):
            pass
        return GameMode.OVERWORLD

    @staticmethod
    def _matrix(value: Any) -> tuple[tuple[int, ...], ...]:
        if hasattr(value, "tolist"):
            value = value.tolist()
        return tuple(tuple(int(cell) for cell in row) for row in value)

    def _read_game_area(self, pyboy: Any, warnings: list[str]) -> tuple[tuple[int, ...], ...]:
        try:
            return self._matrix(pyboy.game_area())
        except (AttributeError, RuntimeError, TypeError, ValueError) as error:
            warnings.append(f"game area unavailable: {error}")
            return ()

    def _read_collision(
        self,
        pyboy: Any,
        tile_ids: tuple[tuple[int, ...], ...],
        warnings: list[str],
    ) -> tuple[tuple[bool | None, ...], ...]:
        try:
            raw = self._matrix(pyboy.game_area_collision())
            return tuple(tuple(bool(cell) for cell in row) for row in raw)
        except (AttributeError, RuntimeError, TypeError, ValueError) as error:
            warnings.append(f"collision map unavailable: {error}")
            return tuple(tuple(None for _ in row) for row in tile_ids)

    @staticmethod
    def _read_sprites(pyboy: Any, warnings: list[str]) -> tuple[VisibleSprite, ...]:
        visible: list[VisibleSprite] = []
        try:
            for index in range(40):
                sprite = pyboy.get_sprite(index)
                if not bool(sprite.on_screen):
                    continue
                width, height = sprite.shape
                visible.append(
                    VisibleSprite(
                        index=index,
                        screen_x=int(sprite.x),
                        screen_y=int(sprite.y),
                        width=int(width),
                        height=int(height),
                        tile_identifier=int(sprite.tile_identifier),
                    )
                )
        except (AttributeError, RuntimeError, TypeError, ValueError) as error:
            warnings.append(f"sprite data unavailable: {error}")
        return tuple(visible)

    def _read_party(self, pyboy: Any, warnings: list[str]) -> tuple[PartyMember, ...]:
        try:
            party = pyboy.game_wrapper.party
        except (AttributeError, RuntimeError, TypeError, ValueError) as error:
            warnings.append(f"party unavailable: {error}")
            return ()

        members: list[PartyMember] = []
        for slot, raw in enumerate(party):
            species_id = int(raw.get("species", 0))
            move_ids = tuple(int(value) for value in raw.get("moves", ()))
            members.append(
                PartyMember(
                    slot=slot,
                    species_id=species_id,
                    species_name=self.lookups.species_names.get(species_id),
                    nickname=self._decode_name(raw.get("nickname")),
                    level=int(raw.get("level", 0)),
                    hp=int(raw.get("hp", 0)),
                    max_hp=int(raw.get("max_hp", 0)),
                    status=int(raw.get("status", 0)),
                    move_ids=move_ids,
                    move_names=tuple(self.lookups.move_names.get(value) for value in move_ids),
                    pp=tuple(int(value) for value in raw.get("pp", ())),
                )
            )
        return tuple(members)

    def _read_inventory(self, pyboy: Any, warnings: list[str]) -> tuple[InventoryItem, ...]:
        try:
            inventory = pyboy.game_wrapper.inventory
        except (AttributeError, RuntimeError, TypeError, ValueError) as error:
            warnings.append(f"inventory unavailable: {error}")
            return ()
        return tuple(
            InventoryItem(
                slot=slot,
                item_id=int(raw.get("item", 0)),
                item_name=self.lookups.item_names.get(int(raw.get("item", 0))),
                quantity=int(raw.get("quantity", 0)),
            )
            for slot, raw in enumerate(inventory)
        )

    @staticmethod
    def _read_money(pyboy: Any, warnings: list[str]) -> int | None:
        try:
            return int(pyboy.game_wrapper.money)
        except (AttributeError, RuntimeError, TypeError, ValueError) as error:
            warnings.append(f"money unavailable: {error}")
            return None

    def _decode_name(self, encoded: Any) -> str | None:
        if encoded is None:
            return None
        if isinstance(encoded, str):
            return encoded
        if not isinstance(encoded, Sequence):
            return None
        decoded: list[str] = []
        for value in encoded:
            token = self.lookups.text_decoding.get(int(value))
            if token is not None:
                decoded.append(token)
        return "".join(decoded) or None

    @staticmethod
    def _screen_hash(pyboy: Any, tile_ids: tuple[tuple[int, ...], ...]) -> str:
        try:
            data = pyboy.screen.ndarray.tobytes()
        except (AttributeError, RuntimeError, TypeError, ValueError):
            data = repr(tile_ids).encode("utf-8")
        return hashlib.sha256(data).hexdigest()[:16]
