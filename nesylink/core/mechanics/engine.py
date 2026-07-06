from __future__ import annotations

from pathlib import Path
import random

from ..constants import ACTION_A, ACTION_B, ACTION_NOOP, MESSAGE_DEFAULT, MOVE_ACTION_TO_DIRECTION, PLAYER_SPEED_PX_PER_TICK
from ..equipment import trigger_equipment
from ..state import EquipmentSlot, PlayerState, tile_to_top_left_px
from ..runtime import RuntimeState
from ..types import EngineStepResult
from ..world.rooms import RoomManager
from . import combat, interactions, movement, progress


class DungeonEngine:
    def __init__(
        self,
        room_file: str | Path,
        *,
        move_speed_px: float = PLAYER_SPEED_PX_PER_TICK,
        control_mode: str = "pixel",
        monster_move_periods: dict[str, int] | None = None,
        player_config: dict | None = None,
    ):
        self.room_manager = RoomManager(room_file)
        self.map_id = self.room_manager.room_file.stem
        self.move_speed_px = max(1, int(move_speed_px))
        if control_mode not in {"pixel", "grid"}:
            raise ValueError("control_mode must be 'pixel' or 'grid'")
        self.control_mode = str(control_mode)
        self.monster_move_periods = {
            str(monster_type): max(1, int(period))
            for monster_type, period in (monster_move_periods or {}).items()
        }
        self.player_config = dict(getattr(self.room_manager, "player_config", {}))
        self.player_config.update(dict(player_config or {}))
        self.max_monster_slots = max(1, self.room_manager.max_monsters)
        self.world_completion_via_exit = any(
            exit_cfg.complete_task
            for room in self.room_manager.room_templates.values()
            for exit_cfg in room.exits
        )
        self.seed: int | None = None
        self.rng = random.Random()
        self.runtime = self._build_initial_runtime()

    def reset(self, *, seed: int | None = None) -> RuntimeState:
        self.seed = seed
        self.rng = random.Random(seed)
        previous_episode = self.runtime.episode
        self.room_manager.reset_room_cache()
        self.runtime = self._build_initial_runtime()
        self.runtime.episode = previous_episode + 1
        self.runtime.seed = seed
        return self.runtime

    def step(self, action: int) -> EngineStepResult:
        if self.control_mode == "grid":
            return self._step_grid(action)
        return self._step_pixel(action)

    def _step_pixel(self, action: int) -> EngineStepResult:
        runtime = self.runtime
        result = EngineStepResult(
            progress_start_pos=runtime.player.position_px,
            progress_start_room_id=runtime.room.room_id,
        )
        runtime.step_count += 1
        if runtime.control_lock_steps_remaining > 0:
            self._advance_control_lock(result)
            result.last_message = runtime.last_message
            return result
        action_started_this_step = False

        self._advance_player_action_state()

        move_direction = MOVE_ACTION_TO_DIRECTION.get(action)
        if move_direction is not None:
            result.move_direction = move_direction
            movement.handle_move(self, move_direction, result)
        elif action == ACTION_A:
            if not interactions.try_interaction(self, result):
                action_started_this_step = trigger_equipment(self, EquipmentSlot.A, result).used
        elif action == ACTION_B:
            action_started_this_step = trigger_equipment(self, EquipmentSlot.B, result).used
        elif action == ACTION_NOOP:
            runtime.last_message = "WAIT"
            result.events.append("noop")

        if runtime.player.health > 0 and move_direction is not None:
            movement.resolve_transition(self, move_direction, result)
        if runtime.player.health > 0:
            interactions.resolve_tile_effects(self, result)
        if runtime.player.health > 0:
            combat.update_monsters(self, result)
        if runtime.player.health > 0:
            combat.resolve_monster_contact(self, result)

        if runtime.player.health <= 0:
            result.terminated = True
            runtime.pending_reset = True
            runtime.last_message = "GAME OVER"
            result.events.append("agent_dead")
            result.terminated_reason = "agent_dead"
        elif "environment_completed" in result.events or (
            not self.world_completion_via_exit and progress.all_chests_opened(self.room_manager)
        ):
            result.terminated = True
            runtime.pending_reset = True
            runtime.last_message = "WORLD COMPLETE"
            if "environment_completed" not in result.events:
                result.events.append("environment_completed")
            result.terminated_reason = "world_completed"

        if progress.step_made_progress(runtime, result.progress_start_pos, result.progress_start_room_id, result.events):
            runtime.no_progress_steps = 0
        else:
            runtime.no_progress_steps += 1
        self._finalize_player_action_state(action_started_this_step)

        result.last_message = runtime.last_message
        return result

    def _step_grid(self, action: int) -> EngineStepResult:
        runtime = self.runtime
        result = EngineStepResult(
            progress_start_pos=runtime.player.position_px,
            progress_start_room_id=runtime.room.room_id,
        )
        if runtime.control_lock_steps_remaining > 0:
            runtime.step_count += 1
            self._advance_control_lock(result)
            result.last_message = runtime.last_message
            return result
        action_started_this_step = False

        self._advance_player_action_state()

        move_direction = MOVE_ACTION_TO_DIRECTION.get(action)
        if move_direction is not None:
            result.move_direction = move_direction
            movement.handle_grid_move(self, move_direction, result)
        elif action == ACTION_A:
            if not interactions.try_interaction(self, result):
                action_started_this_step = trigger_equipment(self, EquipmentSlot.A, result).used
        elif action == ACTION_B:
            action_started_this_step = trigger_equipment(self, EquipmentSlot.B, result).used
        elif action == ACTION_NOOP:
            runtime.last_message = "WAIT"
            result.events.append("noop")

        if runtime.player.health > 0 and move_direction is not None:
            movement.resolve_transition(self, move_direction, result)
        if runtime.player.health > 0:
            interactions.resolve_tile_effects(self, result)

        runtime.step_count += 1

        if runtime.player.health > 0:
            combat.update_monsters(self, result)
        if runtime.player.health > 0:
            combat.resolve_monster_contact(self, result)

        self._finalize_step(result, action_started_this_step)
        return result

    def _finalize_step(self, result: EngineStepResult, action_started_this_step: bool) -> None:
        runtime = self.runtime
        if runtime.player.health <= 0:
            result.terminated = True
            runtime.pending_reset = True
            runtime.last_message = "GAME OVER"
            result.events.append("agent_dead")
            result.terminated_reason = "agent_dead"
        elif "environment_completed" in result.events or (
            not self.world_completion_via_exit and progress.all_chests_opened(self.room_manager)
        ):
            result.terminated = True
            runtime.pending_reset = True
            runtime.last_message = "WORLD COMPLETE"
            if "environment_completed" not in result.events:
                result.events.append("environment_completed")
            result.terminated_reason = "world_completed"

        if progress.step_made_progress(runtime, result.progress_start_pos, result.progress_start_room_id, result.events):
            runtime.no_progress_steps = 0
        else:
            runtime.no_progress_steps += 1
        self._finalize_player_action_state(action_started_this_step)

        result.last_message = runtime.last_message

    def hud_lines(self) -> tuple[str, str]:
        runtime = self.runtime
        room_text = f"R:{runtime.room.room_id} HP:{runtime.player.health} G:{runtime.player.gold}"
        items = ",".join(runtime.player.items) if runtime.player.items else "-"
        equipment = (
            f"A:{runtime.player.equipped_tool_label(EquipmentSlot.A.value)} "
            f"B:{runtime.player.equipped_tool_label(EquipmentSlot.B.value)}"
        )
        return room_text, f"I:{items} {equipment}"

    def _build_initial_runtime(self) -> RuntimeState:
        room_coord = self.room_manager.start_room
        room = self.room_manager.get_room(room_coord)
        player = PlayerState(position_px=tile_to_top_left_px(room.spawns[room.default_spawn_name]))
        self._apply_player_config(player)
        return RuntimeState(
            room_manager=self.room_manager,
            room_coord=room_coord,
            room=room,
            player=player,
            episode=0,
            step_count=0,
            pending_reset=False,
            last_message=MESSAGE_DEFAULT,
            no_progress_steps=0,
            seed=self.seed,
        )

    def _apply_player_config(self, player: PlayerState) -> None:
        if "items" in self.player_config:
            player.items = [str(item) for item in self.player_config.get("items", [])]
        if "tools" in self.player_config:
            player.tools = [str(tool) for tool in self.player_config.get("tools", [])]
        if "equipped" in self.player_config:
            player.equipped = {
                str(slot): str(tool)
                for slot, tool in dict(self.player_config.get("equipped", {})).items()
            }
        player.action_a_label = player.equipped_tool_label(EquipmentSlot.A.value).upper()
        player.action_b_label = player.equipped_tool_label(EquipmentSlot.B.value).upper()

    def _advance_player_action_state(self) -> None:
        player = self.runtime.player
        if player.action_ticks_remaining > 1:
            player.action_ticks_remaining -= 1

    def _advance_control_lock(self, result: EngineStepResult) -> None:
        runtime = self.runtime
        runtime.control_lock_steps_remaining -= 1
        if runtime.control_lock_steps_remaining > 0:
            runtime.last_message = "FALLING"
            result.events.append("control_locked")
            result.event_details.append(
                {
                    "type": "control_locked",
                    "remaining_steps": runtime.control_lock_steps_remaining,
                    "reason": "abyss_fall",
                }
            )
            return

        if runtime.pending_respawn_tile is not None:
            respawn_tile = runtime.pending_respawn_tile
            runtime.player.position_px = tile_to_top_left_px(respawn_tile)
            runtime.pending_respawn_tile = None
            runtime.last_message = "RESPAWN"
            result.events.append("abyss_respawned")
            result.event_details.append(
                {
                    "type": "abyss_respawned",
                    "respawn_tile": [respawn_tile[0], respawn_tile[1]],
                }
            )
            return

        runtime.last_message = "READY"

    def _finalize_player_action_state(self, action_started_this_step: bool) -> None:
        player = self.runtime.player
        if action_started_this_step or player.action_item is None:
            return
        if player.action_ticks_remaining <= 1:
            player.clear_action()
