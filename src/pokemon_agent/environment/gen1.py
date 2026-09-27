"""Canonical English Pokemon Red/Blue memory profile and ROM metadata."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Gen1MemoryProfile:
    battle_state: int = 0xD057
    game_started_flags: int = 0xD732
    game_started_bit: int = 0
    map_id: int = 0xD35E
    player_y: int = 0xD361
    player_x: int = 0xD362


MEMORY = Gen1MemoryProfile()

SUPPORTED_ROM_SHA1: dict[str, str] = {
    "ea9bcae617fdf159b045185467ae58b2e4a48b9a": "Pokemon Red (English)",
    "d7037c83e1ae5b39bde3c30787637ba1d4c48ce2": "Pokemon Blue (English)",
}

SUPPORTED_CARTRIDGE_TITLES = {"POKEMON RED", "POKEMON BLUE"}
