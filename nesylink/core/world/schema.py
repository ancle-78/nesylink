from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..constants import GRID_HEIGHT, GRID_WIDTH
from ..monsters import MonsterState
from ..state import ButtonState, ChestState, GridPos, NPCState, TrapState


SUPPORTED_OBJECT_KINDS = {
    "button",
    "chest",
    "monster",
    "npc",
    "switch",
    "trap",
}

SUPPORTED_EXIT_DIRECTIONS = {"north", "south", "west", "east"}
SUPPORTED_EXIT_TYPES = {"normal", "locked_key", "conditional"}
SUPPORTED_REQUIREMENT_KEYS = {"key_count", "consume_key", "button_pressed", "item", "all_monsters_defeated"}
SUPPORTED_DYNAMIC_OBJECT_KINDS = {"rotating_bridge"}
SUPPORTED_DYNAMIC_TILE_KINDS = {"none", "gap", "bridge"}
SUPPORTED_SWITCH_ACTIVATIONS = {"interact"}
SUPPORTED_SWITCH_EFFECT_TYPES = {"cycle_state"}
LAYOUT_TILES = {"#", "."}

EXIT_DIRECTION_TILES: dict[str, tuple[GridPos, GridPos]] = {
    "north": ((4, 0), (5, 0)),
    "south": ((4, GRID_HEIGHT - 1), (5, GRID_HEIGHT - 1)),
    "west": ((0, 3), (0, 4)),
    "east": ((GRID_WIDTH - 1, 3), (GRID_WIDTH - 1, 4)),
}

OPPOSITE_EXIT_DIRECTIONS = {
    "north": "south",
    "south": "north",
    "west": "east",
    "east": "west",
}

ENTRY_SPAWN_TILE_CANDIDATES: dict[str, tuple[GridPos, GridPos]] = {
    "north": ((4, 1), (5, 1)),
    "south": ((4, GRID_HEIGHT - 2), (5, GRID_HEIGHT - 2)),
    "west": ((1, 3), (1, 4)),
    "east": ((GRID_WIDTH - 2, 3), (GRID_WIDTH - 2, 4)),
}


def exit_tiles_for_direction(direction: str) -> tuple[GridPos, GridPos]:
    return EXIT_DIRECTION_TILES[direction]


def opposite_direction(direction: str) -> str:
    return OPPOSITE_EXIT_DIRECTIONS[direction]


def direction_from_entry_name(entry_name: str) -> str | None:
    normalized = entry_name.strip().lower()
    for direction in SUPPORTED_EXIT_DIRECTIONS:
        if normalized in {direction, f"from_{direction}", f"{direction}_entry"}:
            return direction
    return None


def entry_spawn_tile_candidates(direction: str) -> tuple[GridPos, GridPos]:
    return ENTRY_SPAWN_TILE_CANDIDATES[direction]


def first_valid_entry_spawn_tile(direction: str, wall_tiles: set[GridPos] | frozenset[GridPos]) -> GridPos | None:
    for candidate in entry_spawn_tile_candidates(direction):
        if candidate not in wall_tiles:
            return candidate
    return None


class MapValidationError(ValueError):
    def __init__(self, file_path: str | Path, field_path: str, message: str):
        self.file_path = str(file_path)
        self.field_path = field_path
        self.message = message
        super().__init__(str(self))

    def __str__(self) -> str:
        location = self.file_path
        if self.field_path:
            location = f"{location}: {self.field_path}"
        return f"{location} - {self.message}"


@dataclass(frozen=True)
class ObjectConfig:
    object_id: str
    kind: str
    pos: GridPos
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DynamicObjectStateConfig:
    state_id: str
    tiles: tuple[GridPos, ...]


@dataclass(frozen=True)
class DynamicObjectConfig:
    object_id: str
    kind: str
    initial_state: str
    states: dict[str, DynamicObjectStateConfig]
    background_tile: str = "gap"
    active_tile: str = "bridge"

    def all_tiles(self) -> set[GridPos]:
        tiles: set[GridPos] = set()
        for state in self.states.values():
            tiles.update(state.tiles)
        return tiles


@dataclass(frozen=True)
class ExitConfig:
    exit_id: str
    direction: str
    tiles: tuple[GridPos, GridPos]
    target_room_id: str
    target_entry: str
    exit_type: str = "normal"
    requires: dict[str, Any] = field(default_factory=dict)
    blocked_message: str = "BLOCKED"
    success_message: str = "MOVED"
    complete_task: bool = False

    def contains(self, pos: GridPos) -> bool:
        return pos in self.tiles


@dataclass
class ExitRuntimeState:
    unlocked: bool = False
    opened: bool = False


@dataclass(frozen=True)
class RoomTemplate:
    room_id: str
    coord: tuple[int, int]
    width: int
    height: int
    spawns: dict[str, GridPos]
    default_spawn_name: str
    walls: frozenset[GridPos]
    objects: tuple[ObjectConfig, ...]
    exits: tuple[ExitConfig, ...]
    dynamic_objects: tuple[DynamicObjectConfig, ...] = field(default_factory=tuple)


@dataclass
class RoomState:
    room_id: str
    coord: tuple[int, int]
    width: int
    height: int
    spawns: dict[str, GridPos]
    default_spawn_name: str
    walls: set[GridPos]
    chests: dict[str, ChestState]
    npcs: dict[str, NPCState]
    traps: dict[str, TrapState]
    buttons: dict[str, ButtonState]
    switches: dict[str, ButtonState]
    monsters: dict[str, MonsterState]
    exits: list[ExitConfig]
    switch_effects: dict[str, dict[str, Any]] = field(default_factory=dict)
    dynamic_objects: dict[str, DynamicObjectConfig] = field(default_factory=dict)
    dynamic_states: dict[str, str] = field(default_factory=dict)
    dynamic_tiles: dict[GridPos, str] = field(default_factory=dict)
    exit_states: dict[str, ExitRuntimeState] = field(default_factory=dict)

    def chest_at(self, pos: GridPos) -> ChestState | None:
        for chest in self.chests.values():
            if chest.is_visible and chest.pos == pos:
                return chest
        return None

    def npc_at(self, pos: GridPos) -> NPCState | None:
        for npc in self.npcs.values():
            if npc.pos == pos:
                return npc
        return None

    def trap_at(self, pos: GridPos) -> TrapState | None:
        if self.dynamic_tiles.get(pos) == "bridge":
            return None
        for trap in self.traps.values():
            if trap.pos == pos and trap.is_active:
                return trap
        return None

    def button_at(self, pos: GridPos) -> ButtonState | None:
        for button in self.buttons.values():
            if button.pos == pos:
                return button
        return None

    def switch_at(self, pos: GridPos) -> ButtonState | None:
        for switch in self.switches.values():
            if switch.pos == pos:
                return switch
        return None

    def exit_at(self, pos: GridPos, direction: str) -> ExitConfig | None:
        for exit_config in self.exits:
            if exit_config.direction == direction and exit_config.contains(pos):
                return exit_config
        return None

    def exit_state(self, exit_config: ExitConfig) -> ExitRuntimeState:
        if exit_config.exit_id not in self.exit_states:
            self.exit_states[exit_config.exit_id] = ExitRuntimeState(
                unlocked=exit_config.exit_type != "locked_key",
                opened=exit_config.exit_type != "locked_key",
            )
        return self.exit_states[exit_config.exit_id]

    def blocking_tiles(self) -> set[GridPos]:
        tiles = set(self.walls)
        tiles.update(chest.pos for chest in self.chests.values() if chest.is_visible)
        tiles.update(npc.pos for npc in self.npcs.values())
        return tiles

    def dynamic_blocking_tiles(self) -> set[GridPos]:
        return {pos for pos, tile_kind in self.dynamic_tiles.items() if tile_kind == "gap"}

    def runtime_blocking_tiles(self) -> set[GridPos]:
        return self.blocking_tiles() | self.dynamic_blocking_tiles()

    def rebuild_dynamic_tiles(self) -> None:
        tiles: dict[GridPos, str] = {}
        for dynamic_object in self.dynamic_objects.values():
            for tile in dynamic_object.all_tiles():
                if dynamic_object.background_tile == "none":
                    tiles.pop(tile, None)
                else:
                    tiles[tile] = dynamic_object.background_tile
            active_state = self.dynamic_states.get(dynamic_object.object_id, dynamic_object.initial_state)
            state_config = dynamic_object.states[active_state]
            for tile in state_config.tiles:
                tiles[tile] = dynamic_object.active_tile
        self.dynamic_tiles = tiles

    def set_dynamic_state(self, object_id: str, state_id: str) -> tuple[str, str]:
        dynamic_object = self.dynamic_objects[object_id]
        if state_id not in dynamic_object.states:
            raise ValueError(f"unknown state '{state_id}' for dynamic object '{object_id}'")
        old_state = self.dynamic_states.get(object_id, dynamic_object.initial_state)
        self.dynamic_states[object_id] = state_id
        self.rebuild_dynamic_tiles()
        return old_state, state_id
