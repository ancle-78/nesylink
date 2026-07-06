from __future__ import annotations

from typing import Any

from .constants import TILE_SIZE
from .events import build_event_records, event_counts_to_flags, event_records_to_counts
from .runtime import RuntimeState


def build_info(
    runtime: RuntimeState,
    *,
    events: list[str],
    event_details: list[dict[str, Any]],
    map_id: str | None = None,
    movement_pixels: int | float | None = None,
    action_repeat: int = 1,
    inner_steps: int = 1,
    control_mode: str = "pixel",
    observation_mode: str = "full",
    monster_move_periods: dict[str, int] | None = None,
    max_monster_slots: int | None = None,
    engine_terminated: bool = False,
    terminal_reason: str | None = None,
    debug_message: str | None | object = ...,
) -> dict[str, Any]:
    event_records = build_event_records(events, event_details)
    event_counts = event_records_to_counts(event_records)
    event_flags = event_counts_to_flags(event_counts)
    player_tile = runtime.snapshot().player_tile
    inventory = {
        "gold": runtime.player.gold,
        "keys": runtime.player.keys,
        "items": list(runtime.player.items),
        "tools": list(runtime.player.tools),
        "equipped": dict(runtime.player.equipped),
    }
    resolved_debug_message = runtime.last_message or None
    if debug_message is not ...:
        resolved_debug_message = debug_message

    entities = _build_entities(runtime, control_mode=control_mode, max_monster_slots=max_monster_slots)
    debug_info = {
        "message": resolved_debug_message,
        "engine_done": bool(engine_terminated),
        "action_item": runtime.player.action_item,
        "action_pose": runtime.player.action_pose,
        "action_ticks_remaining": int(runtime.player.action_ticks_remaining),
        "control_lock_steps_remaining": int(runtime.control_lock_steps_remaining),
        "pending_respawn_tile": (
            None
            if runtime.pending_respawn_tile is None
            else [int(runtime.pending_respawn_tile[0]), int(runtime.pending_respawn_tile[1])]
        ),
    }
    game = {
        "dead": bool(runtime.player.health <= 0 or terminal_reason == "agent_dead"),
        "room_changed": bool(event_flags.get("room_changed", False)),
        "exit_reached": bool(event_flags.get("exit_reached", False)),
        "world_completed": bool(terminal_reason == "world_completed"),
    }

    info: dict[str, Any] = {
        "episode": {
            "id": runtime.episode,
            "step_count": runtime.step_count,
            "seed": runtime.seed,
            "no_progress_steps": runtime.no_progress_steps,
        },
        "env": {
            "map_id": map_id,
            "room_id": runtime.room.room_id,
            "room_coord": runtime.room.coord,
        },
        "agent": _build_agent(runtime, player_tile, control_mode=control_mode),
        "inventory": inventory,
        "entities": entities,
        "dynamic": _build_dynamic(runtime),
        "events": {
            "records": event_records,
            "flags": event_flags,
            "counts": event_counts,
            "details": list(event_details),
        },
        "game": game,
        "terminal_reason": terminal_reason,
        "control": _build_control(
            control_mode=control_mode,
            observation_mode=observation_mode,
            movement_pixels=movement_pixels,
            action_repeat=action_repeat,
            inner_steps=inner_steps,
            monster_move_periods=monster_move_periods,
        ),
        "debug": debug_info,
    }
    return info


def _build_agent(runtime: RuntimeState, player_tile: tuple[int, int], *, control_mode: str) -> dict[str, Any]:
    agent = {
        "hp": runtime.player.health,
        "tile": player_tile,
        "facing": runtime.player.facing,
    }
    if control_mode != "grid":
        agent["position_px"] = runtime.player.position_px
    return agent


def _build_entities(
    runtime: RuntimeState,
    *,
    control_mode: str,
    max_monster_slots: int | None,
) -> dict[str, Any]:
    entities: dict[str, Any] = {
        "monsters_remaining": len(runtime.room.monsters),
        "monster_ids": sorted(runtime.room.monsters),
        "chests_remaining": sum(
            1 for chest in runtime.room.chests.values() if chest.is_visible and not chest.is_open
        ),
        "chests_hidden": sum(1 for chest in runtime.room.chests.values() if not chest.is_visible),
        "traps_active": sum(1 for trap in runtime.room.traps.values() if trap.is_active),
        "buttons_pressed": sum(1 for button in runtime.room.buttons.values() if button.is_pressed),
        "switches_total": len(runtime.room.switches),
        "exits_open": sum(1 for exit_cfg in runtime.room.exits if runtime.room.exit_state(exit_cfg).opened),
        "exits_total": len(runtime.room.exits),
    }
    if control_mode != "grid":
        return entities

    slots = max_monster_slots if max_monster_slots is not None else max(1, len(runtime.room.monsters))
    monster_ids = list(runtime.room.monsters)
    monster_types: list[str | None] = [None] * slots
    monster_tiles: list[list[int]] = [[-1, -1] for _ in range(slots)]
    monster_masks: list[bool] = [False] * slots
    monster_hp: list[int] = [0] * slots
    for index, monster in enumerate(runtime.room.monsters.values()):
        if index >= slots:
            break
        monster_types[index] = monster.monster_type
        monster_tiles[index] = [int(monster.tile_pos[0]), int(monster.tile_pos[1])]
        monster_masks[index] = True
        monster_hp[index] = int(monster.hp)
    entities.update(
        {
            "monster_ids": monster_ids[:slots],
            "monster_types": monster_types,
            "monsters_tile": monster_tiles,
            "monsters_active_mask": monster_masks,
            "monsters_hp": monster_hp,
        }
    )
    return entities


def _build_dynamic(runtime: RuntimeState) -> dict[str, Any]:
    objects: dict[str, Any] = {}
    for coord, room in runtime.room_manager.rooms.items():
        del coord
        for object_id, dynamic_object in room.dynamic_objects.items():
            objects[object_id] = {
                "kind": dynamic_object.kind,
                "room_id": room.room_id,
                "state": room.dynamic_states.get(object_id, dynamic_object.initial_state),
            }
    for template in runtime.room_manager.room_templates.values():
        for dynamic_object in template.dynamic_objects:
            if dynamic_object.object_id in objects:
                continue
            objects[dynamic_object.object_id] = {
                "kind": dynamic_object.kind,
                "room_id": template.room_id,
                "state": dynamic_object.initial_state,
            }
    current_room_tiles = [
        {"pos": [int(pos[0]), int(pos[1])], "tile": tile_kind}
        for pos, tile_kind in sorted(runtime.room.dynamic_tiles.items())
    ]
    return {
        "objects": objects,
        "current_room_tiles": current_room_tiles,
    }


def _build_control(
    *,
    control_mode: str,
    observation_mode: str,
    movement_pixels: int | float | None,
    action_repeat: int,
    inner_steps: int,
    monster_move_periods: dict[str, int] | None,
) -> dict[str, Any]:
    if control_mode == "grid":
        return {
            "control_mode": control_mode,
            "observation_mode": observation_mode,
            "tile_size": TILE_SIZE,
            "monster_move_periods": dict(monster_move_periods or {}),
        }
    return {
        "action_repeat": int(action_repeat),
        "inner_steps": int(inner_steps),
        "movement_pixels": movement_pixels,
    }
