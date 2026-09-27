from __future__ import annotations

from collections import defaultdict

from pokemon_agent.environment.extractor import Gen1Lookups, Gen1StateExtractor
from pokemon_agent.environment.gen1 import MEMORY
from pokemon_agent.models import CellKind, GameMode


class FakeArray:
    def __init__(self, value: list[list[int]]) -> None:
        self.value = value

    def tolist(self) -> list[list[int]]:
        return self.value

    def tobytes(self) -> bytes:
        return repr(self.value).encode()


class FakeScreen:
    ndarray = FakeArray([[1, 2], [3, 4]])


class FakeTilemap:
    def __init__(self, dialogue_arrow: int = 0) -> None:
        self.dialogue_arrow = dialogue_arrow

    def __getitem__(self, key: tuple[int, int]) -> int:
        return self.dialogue_arrow if key == (18, 16) else 0


class FakeSprite:
    on_screen = False
    x = 0
    y = 0
    shape = (8, 16)
    tile_identifier = 0


class FakeWrapper:
    party = [
        {
            "species": 7,
            "nickname": (128, 129),
            "level": 5,
            "hp": 19,
            "max_hp": 20,
            "status": 0,
            "moves": (33, 0, 0, 0),
            "pp": (35, 0, 0, 0),
        }
    ]
    inventory = [{"item": 20, "quantity": 2}]
    money = 3000


class FakePyBoy:
    def __init__(self, *, started: bool = True, battle_state: int = 0) -> None:
        self.memory: defaultdict[int, int] = defaultdict(int)
        self.memory[MEMORY.game_started_flags] = 1 if started else 0
        self.memory[MEMORY.battle_state] = battle_state
        self.memory[MEMORY.map_id] = 0
        self.memory[MEMORY.player_x] = 4
        self.memory[MEMORY.player_y] = 6
        self.tilemap_window = FakeTilemap()
        self.screen = FakeScreen()
        self.game_wrapper = FakeWrapper()

    @staticmethod
    def game_area() -> FakeArray:
        return FakeArray([[10, 11], [12, 13]])

    @staticmethod
    def game_area_collision() -> FakeArray:
        return FakeArray([[1, 0], [1, 1]])

    @staticmethod
    def get_sprite(index: int) -> FakeSprite:
        del index
        return FakeSprite()


def extractor() -> Gen1StateExtractor:
    return Gen1StateExtractor(
        cartridge_title="POKEMON BLUE",
        rom_sha1="test",
        supported_rom=True,
        lookups=Gen1Lookups(
            map_names={0: "PALLET_TOWN"},
            species_names={7: "SQUIRTLE"},
            move_names={33: "TACKLE"},
            item_names={20: "POTION"},
            text_decoding={128: "A", 129: "B"},
        ),
    )


def test_extracts_agent_visible_state() -> None:
    observation = extractor().extract(FakePyBoy(), frame_count=12)
    assert observation.mode == GameMode.OVERWORLD
    assert observation.map_name == "PALLET_TOWN"
    assert observation.player_position is not None
    assert observation.player_position.x == 4
    assert observation.viewport.semantic[0][0] == CellKind.WALKABLE
    assert observation.viewport.semantic[0][1] == CellKind.BLOCKED
    assert observation.party[0].species_name == "SQUIRTLE"
    assert observation.party[0].nickname == "AB"
    assert observation.inventory[0].item_name == "POTION"
    assert observation.money == 3000


def test_hides_location_before_game_has_started() -> None:
    state = extractor()
    observation = state.extract(FakePyBoy(started=False), frame_count=1)
    assert observation.mode == GameMode.BOOT
    assert observation.map_id is None
    assert observation.player_position is None
    assert observation.party == ()
    assert state.debug_snapshot().game_started is False


def test_marks_battle_mode() -> None:
    observation = extractor().extract(FakePyBoy(battle_state=1), frame_count=20)
    assert observation.mode == GameMode.BATTLE
