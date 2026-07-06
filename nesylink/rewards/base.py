from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _nested_int(mapping: Mapping[str, Any], key: str, default: int = 0) -> int:
    return _int(mapping.get(key, default), default)


def _obs_item(obs: Any, key: str, default: Any = None) -> Any:
    if isinstance(obs, Mapping):
        return obs.get(key, default)
    return default


def _scalar(value: Any, default: int = 0) -> int:
    if value is None:
        return int(default)
    if hasattr(value, "item"):
        try:
            return _int(value.item(), default)
        except ValueError:
            pass
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        if not value:
            return int(default)
        return _scalar(value[0], default)
    try:
        return _int(value[0], default)
    except (TypeError, IndexError, KeyError):
        return _int(value, default)


def _tuple2(value: Any) -> tuple[int, int] | None:
    if value is None:
        return None
    try:
        return int(value[0]), int(value[1])
    except (TypeError, ValueError, IndexError, KeyError):
        return None


def _sum_sequence(value: Any) -> int:
    if value is None:
        return 0
    try:
        return int(sum(int(item) for item in value))
    except TypeError:
        return _scalar(value)


@dataclass(frozen=True)
class RewardContext:
    prev_obs: Any
    obs: Any
    prev_info: Mapping[str, Any]
    info: Mapping[str, Any]
    action: int | None
    prev_agent: Mapping[str, Any]
    agent: Mapping[str, Any]
    prev_inventory: Mapping[str, Any]
    inventory: Mapping[str, Any]
    prev_entities: Mapping[str, Any]
    entities: Mapping[str, Any]
    event_records: tuple[Mapping[str, Any], ...]
    event_counts: Mapping[str, Any]
    event_flags: Mapping[str, Any]
    game: Mapping[str, Any]
    debug: Mapping[str, Any]

    def event_count(self, name: str) -> int:
        return _nested_int(self.event_counts, name)

    def event_flag(self, name: str) -> bool:
        return bool(self.event_flags.get(name, False)) or self.event_count(name) > 0


def build_reward_context(
    *,
    prev_obs: Any = None,
    obs: Any = None,
    prev_info: dict[str, Any] | None = None,
    info: dict[str, Any] | None = None,
    action: int | None = None,
) -> RewardContext:
    current_info = info or {}
    previous_info = prev_info or {}
    events = _mapping(current_info.get("events"))
    return RewardContext(
        prev_obs=prev_obs,
        obs=obs,
        prev_info=previous_info,
        info=current_info,
        action=action,
        prev_agent=_mapping(previous_info.get("agent")),
        agent=_mapping(current_info.get("agent")),
        prev_inventory=_mapping(previous_info.get("inventory")),
        inventory=_mapping(current_info.get("inventory")),
        prev_entities=_mapping(previous_info.get("entities")),
        entities=_mapping(current_info.get("entities")),
        event_records=tuple(
            record for record in events.get("records", ()) if isinstance(record, Mapping)
        ),
        event_counts=_mapping(events.get("counts")),
        event_flags=_mapping(events.get("flags")),
        game=_mapping(current_info.get("game")),
        debug=_mapping(current_info.get("debug")),
    )


EVENT_SIGNAL_NAMES = (
    "key_collected",
    "gold_collected",
    "item_collected",
    "agent_healed",
    "agent_damaged",
    "trap_triggered",
    "abyss_fall",
    "monster_killed",
    "shield_block",
    "door_opened",
    "chest_opened",
    "chest_revealed",
    "button_pressed",
    "switch_activated",
    "bridge_rotated",
    "dynamic_object_state_changed",
    "talked_npc",
    "exit_reached",
    "environment_completed",
)


def extract_reward_signals(context: RewardContext) -> dict[str, Any]:
    obs_hp = _scalar(_obs_item(context.obs, "health"), _nested_int(context.agent, "hp"))
    prev_obs_hp = _scalar(_obs_item(context.prev_obs, "health"), obs_hp)
    hp_current = _nested_int(context.agent, "hp", obs_hp)
    hp_previous = _nested_int(context.prev_agent, "hp", prev_obs_hp)
    hp_delta = hp_current - hp_previous

    obs_gold = _scalar(_obs_item(context.obs, "gold"), _nested_int(context.inventory, "gold"))
    prev_obs_gold = _scalar(_obs_item(context.prev_obs, "gold"), obs_gold)
    gold_current = _nested_int(context.inventory, "gold", obs_gold)
    gold_previous = _nested_int(context.prev_inventory, "gold", prev_obs_gold)
    gold_delta_raw = gold_current - gold_previous

    obs_keys = _scalar(_obs_item(context.obs, "keys"), _nested_int(context.inventory, "keys"))
    prev_obs_keys = _scalar(_obs_item(context.prev_obs, "keys"), obs_keys)
    keys_current = _nested_int(context.inventory, "keys", obs_keys)
    keys_previous = _nested_int(context.prev_inventory, "keys", prev_obs_keys)
    keys_delta_raw = keys_current - keys_previous

    obs_tile = _tuple2(_obs_item(context.obs, "player_tile"))
    prev_obs_tile = _tuple2(_obs_item(context.prev_obs, "player_tile"))
    info_tile = _tuple2(context.agent.get("tile"))
    prev_info_tile = _tuple2(context.prev_agent.get("tile"))
    player_tile = info_tile or obs_tile
    prev_player_tile = prev_info_tile or prev_obs_tile or player_tile

    monsters_remaining = _nested_int(
        context.entities,
        "monsters_remaining",
        _sum_sequence(_obs_item(context.obs, "monsters_active_mask")),
    )
    prev_monsters_remaining = _nested_int(
        context.prev_entities,
        "monsters_remaining",
        _sum_sequence(_obs_item(context.prev_obs, "monsters_active_mask")) or monsters_remaining,
    )
    active_monsters = _sum_sequence(_obs_item(context.obs, "monsters_active_mask"))
    prev_active_monsters = _sum_sequence(_obs_item(context.prev_obs, "monsters_active_mask"))
    monster_hp_total = _sum_sequence(_obs_item(context.obs, "monsters_hp"))
    prev_monster_hp_total = _sum_sequence(_obs_item(context.prev_obs, "monsters_hp"))

    monster_hit = context.event_count("monster_damaged")
    if monster_hit <= 0:
        monster_hit = context.event_count("action_attack")

    invalid_action = int(
        context.event_flag("action_blocked")
        or context.event_flag("action_no_effect")
    )
    world_completed = int(
        bool(context.game.get("world_completed", False))
        or context.event_flag("environment_completed")
        or context.info.get("terminal_reason") == "world_completed"
    )

    signals: dict[str, Any] = {
        "step": 1,
        "hp": hp_current,
        "prev_hp": hp_previous,
        "hp_delta": hp_delta,
        "hp_loss": max(0, -hp_delta),
        "gold": gold_current,
        "prev_gold": gold_previous,
        "gold_delta": max(0, gold_delta_raw),
        "keys": keys_current,
        "prev_keys": keys_previous,
        "keys_delta": max(0, keys_delta_raw),
        "player_tile": player_tile,
        "prev_player_tile": prev_player_tile,
        "player_tile_changed": int(
            player_tile is not None and prev_player_tile is not None and player_tile != prev_player_tile
        ),
        "monster_hit": monster_hit,
        "monster_kill": context.event_count("monster_killed"),
        "invalid_action": invalid_action,
        "room_changed": int(bool(context.game.get("room_changed", False)) or context.event_flag("room_changed")),
        "death": int(bool(context.game.get("dead", False)) or context.event_flag("agent_dead")),
        "world_completed": world_completed,
        "engine_terminated": int(bool(context.debug.get("engine_done", False))),
        "terminal_reason": context.info.get("terminal_reason"),
        "monsters_remaining": monsters_remaining,
        "prev_monsters_remaining": prev_monsters_remaining,
        "monsters_remaining_delta": monsters_remaining - prev_monsters_remaining,
        "active_monsters": active_monsters,
        "prev_active_monsters": prev_active_monsters,
        "monster_hp_total": monster_hp_total,
        "prev_monster_hp_total": prev_monster_hp_total,
    }
    for event_name in EVENT_SIGNAL_NAMES:
        signal_name = "monster_kill" if event_name == "monster_killed" else event_name
        signals[signal_name] = context.event_count(event_name)
    return signals


class BaseReward:
    reward_name = "base"

    default_weights = {
        "step": 0.0,
        "hp_loss": 0.0,
        "gold_delta": 0.0,
        "keys_delta": 0.0,
        "monster_hit": 0.0,
        "monster_kill": 0.0,
        "key_collected": 0.0,
        "gold_collected": 0.0,
        "item_collected": 0.0,
        "agent_healed": 0.0,
        "agent_damaged": 0.0,
        "trap_triggered": 0.0,
        "abyss_fall": 0.0,
        "shield_block": 0.0,
        "door_opened": 0.0,
        "chest_opened": 0.0,
        "chest_revealed": 0.0,
        "button_pressed": 0.0,
        "switch_activated": 0.0,
        "bridge_rotated": 0.0,
        "dynamic_object_state_changed": 0.0,
        "talked_npc": 0.0,
        "room_changed": 0.0,
        "exit_reached": 0.0,
        "environment_completed": 0.0,
        "world_completed": 0.0,
        "death": 0.0,
        "invalid_action": 0.0,
    }

    reward_weights: dict[str, float] = {}

    def __init__(self, **reward_kwargs: float):
        self.prev_obs: Any = None
        self.prev_info: dict[str, Any] | None = None
        self.weights = dict(self.default_weights)
        self.weights.update(getattr(self, "reward_weights", {}))
        self.weights.update(reward_kwargs)

    def reset(self, obs: Any, info: dict[str, Any]) -> None:
        self.prev_obs = obs
        self.prev_info = info

    def __call__(self, obs: Any, info: dict[str, Any], action: int | None = None) -> tuple[float, dict[str, Any]]:
        signals = self.extract_signals(
            prev_obs=self.prev_obs,
            obs=obs,
            prev_info=self.prev_info,
            info=info,
            action=action,
        )
        reward = self.compute_reward(signals, obs, info, action)
        terminated, terminated_reason = self.check_termination(signals, obs, info, action)
        reward_info = self.build_reward_info(
            signals=signals,
            terminated=terminated,
            terminated_reason=terminated_reason,
        )
        self.prev_obs = obs
        self.prev_info = info
        return float(reward), reward_info

    def build_reward_info(
        self,
        *,
        signals: dict[str, Any] | None = None,
        terminated: bool = False,
        terminated_reason: str | None = None,
    ) -> dict[str, Any]:
        return {
            "reward_name": self.reward_name,
            "reward_signals": dict(signals or {}),
            "reward_weights": dict(self.weights),
            "terminated": bool(terminated),
            "terminated_reason": terminated_reason,
        }

    def extract_signals(
        self,
        *,
        prev_obs: Any,
        obs: Any,
        prev_info: dict[str, Any] | None,
        info: dict[str, Any],
        action: int | None = None,
    ) -> dict[str, Any]:
        context = build_reward_context(
            prev_obs=prev_obs,
            obs=obs,
            prev_info=prev_info,
            info=info,
            action=action,
        )
        return extract_reward_signals(context)

    def compute_reward(
        self,
        signals: dict[str, Any],
        obs: Any,
        info: dict[str, Any],
        action: int | None = None,
    ) -> float:
        reward = 0.0
        for key, weight in self.weights.items():
            reward += float(weight) * float(signals.get(key, 0.0))
        reward += self.extra_reward(signals, obs, info, action)
        return reward

    def extra_reward(
        self,
        signals: dict[str, Any],
        obs: Any,
        info: dict[str, Any],
        action: int | None = None,
    ) -> float:
        del signals, obs, info, action
        return 0.0

    def check_termination(
        self,
        signals: dict[str, Any],
        obs: Any,
        info: dict[str, Any],
        action: int | None = None,
    ) -> tuple[bool, str | None]:
        del signals, obs, info, action
        return False, None
