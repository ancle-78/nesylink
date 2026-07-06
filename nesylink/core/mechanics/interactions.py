from __future__ import annotations

from typing import Any

from ..equipment import trigger_equipment
from ..state import EquipmentSlot
from ..constants import GRID_HEIGHT, GRID_WIDTH
from ..state import GridPos, is_adjacent, tile_from_position_px, tile_to_top_left_px


def handle_equipped_action(engine: Any, slot: EquipmentSlot, result: Any) -> bool:
    return trigger_equipment(engine, slot, result).used


def try_interaction(engine: Any, result: Any) -> bool:
    runtime = engine.runtime
    player_tile = runtime.snapshot().player_tile

    for chest in runtime.room.chests.values():
        if chest.is_visible and not chest.is_open and is_adjacent(player_tile, chest.pos):
            chest.is_open = True
            apply_loot(runtime, chest.loot, result)
            result.events.append("chest_opened")
            return True

    for npc in runtime.room.npcs.values():
        if is_adjacent(player_tile, npc.pos):
            runtime.last_message = npc.text.upper()[:24]
            result.events.append("talked_npc")
            return True

    for switch in runtime.room.switches.values():
        if is_adjacent(player_tile, switch.pos):
            activate_switch(engine, switch.button_id, result)
            return True

    return False


def activate_switch(engine: Any, switch_id: str, result: Any) -> None:
    runtime = engine.runtime
    switch = runtime.room.switches[switch_id]
    effect = runtime.room.switch_effects.get(switch_id, {})
    effect_type = str(effect.get("type", ""))
    if effect_type != "cycle_state":
        _record_switch_failure(runtime, result, switch_id, "unsupported_effect")
        return

    target = str(effect.get("target", ""))
    order = list(effect.get("order", []))
    if not target or not order:
        _record_switch_failure(runtime, result, switch_id, "invalid_effect")
        return
    if target not in engine.room_manager.dynamic_object_rooms:
        _record_switch_failure(runtime, result, switch_id, "unknown_target", target=target)
        return

    target_room = engine.room_manager.room_for_dynamic_object(target)
    dynamic_object = target_room.dynamic_objects.get(target)
    if dynamic_object is None:
        _record_switch_failure(runtime, result, switch_id, "unknown_target", target=target)
        return
    current_state = target_room.dynamic_states.get(target, dynamic_object.initial_state)
    if current_state not in order:
        _record_switch_failure(runtime, result, switch_id, "state_not_in_order", target=target)
        return
    next_state = order[(order.index(current_state) + 1) % len(order)]
    if next_state == current_state:
        _record_switch_failure(runtime, result, switch_id, "no_state_change", target=target)
        return

    old_state, new_state = target_room.set_dynamic_state(target, next_state)
    switch.is_pressed = True
    runtime.last_message = switch.message.upper()[:24]
    result.events.append("switch_activated")
    result.events.append("dynamic_object_state_changed")
    if dynamic_object.kind == "rotating_bridge":
        result.events.append("bridge_rotated")
    detail = {
        "type": "switch_activated",
        "switch_id": switch_id,
        "room_id": runtime.room.room_id,
        "target": target,
        "effect": effect_type,
        "old_state": old_state,
        "new_state": new_state,
    }
    result.event_details.append(detail)
    result.event_details.append(
        {
            "type": "dynamic_object_state_changed",
            "object_id": target,
            "object_kind": dynamic_object.kind,
            "room_id": target_room.room_id,
            "old_state": old_state,
            "new_state": new_state,
        }
    )
    if dynamic_object.kind == "rotating_bridge":
        result.event_details.append(
            {
                "type": "bridge_rotated",
                "object_id": target,
                "room_id": target_room.room_id,
                "old_state": old_state,
                "new_state": new_state,
            }
        )


def _record_switch_failure(
    runtime: Any,
    result: Any,
    switch_id: str,
    reason: str,
    *,
    target: str | None = None,
) -> None:
    runtime.last_message = "SWITCH FAILED"
    result.events.append("switch_activation_failed")
    detail = {
        "type": "switch_activation_failed",
        "switch_id": switch_id,
        "room_id": runtime.room.room_id,
        "reason": reason,
    }
    if target is not None:
        detail["target"] = target
    result.event_details.append(detail)


def apply_loot(runtime: Any, loot: dict, result: Any) -> None:
    loot_kind = str(loot.get("kind", "gold"))
    amount = int(loot.get("amount", 1))

    if loot_kind == "key":
        runtime.player.keys += max(1, amount)
        runtime.last_message = "GOT KEY"
        result.events.append("key_collected")
        return
    if loot_kind == "heal":
        healed = min(runtime.player.max_health, runtime.player.health + max(1, amount))
        runtime.player.health = healed
        runtime.last_message = "HEALED"
        result.events.append("agent_healed")
        return
    if loot_kind == "item":
        item_name = str(loot.get("item_id", "item"))
        if item_name not in runtime.player.items:
            runtime.player.items.append(item_name)
        tool_name = loot.get("tool")
        if tool_name is not None:
            tool_name = str(tool_name)
            if tool_name not in runtime.player.tools:
                runtime.player.tools.append(tool_name)
            equip_slot = str(loot.get("equip_slot", "")).upper()
            if equip_slot in {"A", "B"}:
                runtime.player.equip_tool(EquipmentSlot(equip_slot), tool_name)
        runtime.last_message = f"GOT {item_name}".upper()[:24]
        result.events.append("item_collected")
        return

    runtime.player.gold += max(1, amount)
    runtime.last_message = "GOT GOLD"
    result.events.append("gold_collected")


def resolve_tile_effects(engine: Any, result: Any) -> None:
    runtime = engine.runtime
    player_tile = runtime.snapshot().player_tile

    button = runtime.room.button_at(player_tile)
    if button is not None and not button.is_pressed:
        button.is_pressed = True
        runtime.last_message = button.message.upper()[:24]
        result.events.append("button_pressed")

    trap = runtime.room.trap_at(player_tile)
    if trap is not None:
        if trap.trap_type == "abyss":
            resolve_abyss_trap(runtime, trap, result)
        else:
            resolve_spike_trap(runtime, trap, result)
        if trap.single_use:
            trap.is_active = False


def resolve_spike_trap(runtime: Any, trap: Any, result: Any) -> None:
    runtime.player.health = max(0, runtime.player.health - trap.damage)
    respawn_name = trap.respawn_to if trap.respawn_to in runtime.room.spawns else runtime.room.default_spawn_name
    if runtime.player.health > 0:
        runtime.player.position_px = tile_to_top_left_px(runtime.room.spawns[respawn_name])
    runtime.last_message = f"TRAP -{trap.damage}HP"
    result.events.append("trap_triggered")
    result.events.append("agent_damaged")
    result.event_details.append(
        {
            "type": "trap_triggered",
            "trap_id": trap.trap_id,
            "trap_type": trap.trap_type,
            "damage": trap.damage,
            "respawn_to": respawn_name,
        }
    )


def resolve_abyss_trap(runtime: Any, trap: Any, result: Any) -> None:
    runtime.player.health = max(0, runtime.player.health - trap.damage)
    respawn_tile = find_abyss_respawn_tile(runtime, trap.pos, result.progress_start_pos)
    if runtime.player.health > 0:
        delay_steps = max(1, int(trap.respawn_delay_steps or 2))
        runtime.control_lock_steps_remaining = delay_steps
        runtime.pending_respawn_tile = respawn_tile
    runtime.last_message = f"FALL -{trap.damage}HP"
    result.events.append("abyss_fall")
    result.events.append("trap_triggered")
    result.events.append("agent_damaged")
    result.event_details.append(
        {
            "type": "abyss_fall",
            "trap_id": trap.trap_id,
            "trap_type": trap.trap_type,
            "damage": trap.damage,
            "respawn_tile": [respawn_tile[0], respawn_tile[1]],
            "lock_steps": runtime.control_lock_steps_remaining,
        }
    )


def find_abyss_respawn_tile(
    runtime: Any,
    abyss_tile: GridPos,
    previous_position_px: tuple[float, float] | None = None,
) -> GridPos:
    if previous_position_px is not None:
        previous_tile = tile_from_position_px(previous_position_px, runtime.player.size_px)
        if previous_tile != abyss_tile and is_safe_abyss_respawn_tile(runtime, previous_tile):
            return previous_tile

    x, y = abyss_tile
    candidates = [
        (x - 1, y),
        (x + 1, y),
        (x, y - 1),
        (x, y + 1),
    ]
    for candidate in candidates:
        if is_safe_abyss_respawn_tile(runtime, candidate):
            return candidate
    return runtime.room.spawns[runtime.room.default_spawn_name]


def is_safe_abyss_respawn_tile(runtime: Any, tile: GridPos) -> bool:
    x, y = tile
    if x < 0 or x >= GRID_WIDTH or y < 0 or y >= GRID_HEIGHT:
        return False
    active_traps = {trap.pos for trap in runtime.room.traps.values() if trap.is_active}
    if tile in runtime.room.runtime_blocking_tiles() or tile in active_traps:
        return False
    return True
