from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from gymnasium.envs.registration import EnvSpec, register, registry

from .rewards.loader import load_reward
from .tasks import get_task, list_tasks
from .wrappers import DungeonEnv, GymDungeonEnv, get_wrapper
from .core.world.loader import load_map


@dataclass(frozen=True)
class EnvConfig:
    map_id: str | None
    map_path: str | Path
    reward_id: str | None
    reward_module: str | None
    reward_kwargs: dict[str, float] | None
    max_steps: int | None
    action_repeat: int
    control_mode: str
    observation_mode: str
    monster_move_periods: dict[str, int]
    max_monsters: int | None
    max_inventory: int
    mission: str
    player_config: dict[str, Any]
    gym_id: str | None
    task_id: str | None


def make_env(
    config_path: str | Path | None = None,
    *,
    task_id: str | None = None,
    map_id: str | None = None,
    map_path: str | Path | None = None,
    api: str = "gym",
    reward_id: str | None = None,
    reward_module: str | None = None,
    reward_kwargs: dict[str, float] | None = None,
    max_steps: int | None = None,
    action_repeat: int | None = None,
    control_mode: str | None = None,
    observation_mode: str | None = None,
    monster_move_periods: dict[str, int] | None = None,
    max_monsters: int | None = None,
    max_inventory: int | None = None,
    mission: str | None = None,
    **kwargs: Any,
):
    config = _resolve_env_config(
        config_path=config_path,
        task_id=task_id,
        map_id=map_id,
        map_path=map_path,
        reward_id=reward_id,
        reward_module=reward_module,
        reward_kwargs=reward_kwargs,
        max_steps=max_steps,
        action_repeat=action_repeat,
        control_mode=control_mode,
        observation_mode=observation_mode,
        monster_move_periods=monster_move_periods,
        max_monsters=max_monsters,
        max_inventory=max_inventory,
        mission=mission,
    )
    reward_fn = load_reward(
        reward_id=config.reward_id,
        reward_module=config.reward_module,
        reward_kwargs=config.reward_kwargs,
    )
    wrapper_cls = get_wrapper(api)
    env = wrapper_cls(
        config.map_path,
        reward_fn=reward_fn,
        max_steps=config.max_steps,
        action_repeat=config.action_repeat,
        control_mode=config.control_mode,
        observation_mode=config.observation_mode,
        monster_move_periods=config.monster_move_periods,
        max_monsters=config.max_monsters,
        max_inventory=config.max_inventory,
        mission=config.mission,
        player_config=config.player_config,
        map_id=config.map_id,
        **kwargs,
    )
    if config.task_id is not None and config.gym_id is not None:
        env.spec = EnvSpec(
            id=config.gym_id,
            entry_point="nesylink.env:make_env",
            max_episode_steps=config.max_steps,
            kwargs={"task_id": config.task_id},
        )
    return env


def _resolve_env_config(
    *,
    config_path: str | Path | None,
    task_id: str | None,
    map_id: str | None,
    map_path: str | Path | None,
    reward_id: str | None,
    reward_module: str | None,
    reward_kwargs: dict[str, float] | None,
    max_steps: int | None,
    action_repeat: int | None,
    control_mode: str | None,
    observation_mode: str | None,
    monster_move_periods: dict[str, int] | None,
    max_monsters: int | None,
    max_inventory: int | None,
    mission: str | None,
) -> EnvConfig:
    task = get_task(task_id) if task_id is not None else None

    resolved_map_id = _override(map_id, task.map_id if task is not None else None)
    task_map_path = task.map_path if task is not None else None
    resolved_map_path = load_map(
        map_id=resolved_map_id,
        map_path=_override(map_path, task_map_path, config_path),
    )

    resolved_reward_kwargs = reward_kwargs
    if resolved_reward_kwargs is None and task is not None:
        resolved_reward_kwargs = dict(task.reward_kwargs)

    return EnvConfig(
        map_id=resolved_map_id,
        map_path=resolved_map_path,
        reward_id=_override(reward_id, task.reward_id if task is not None else None),
        reward_module=_override(reward_module, task.reward_module if task is not None else None),
        reward_kwargs=resolved_reward_kwargs,
        max_steps=_override(max_steps, task.max_steps if task is not None else None),
        action_repeat=_override(action_repeat, task.action_repeat if task is not None else 1),
        control_mode=_override(control_mode, task.control_mode if task is not None else "pixel"),
        observation_mode=_override(observation_mode, task.observation_mode if task is not None else "full"),
        monster_move_periods=dict(
            _override(monster_move_periods, task.monster_move_periods if task is not None else {})
        ),
        max_monsters=_override(max_monsters, task.max_monsters if task is not None else None),
        max_inventory=_override(max_inventory, task.max_inventory if task is not None else 2),
        mission=_override(mission, task.mission if task is not None else ""),
        player_config=dict(task.player_config if task is not None else {}),
        gym_id=task.gym_id if task is not None else None,
        task_id=task.task_id if task is not None else None,
    )


def _override(*values):
    for value in values:
        if value is not None:
            return value
    return None


def register_gym_envs() -> None:
    for task in list_tasks():
        if task.gym_id in registry:
            continue
        register(
            id=task.gym_id,
            entry_point="nesylink.env:make_env",
            kwargs={"task_id": task.task_id},
            max_episode_steps=task.max_steps,
        )


__all__ = ["DungeonEnv", "GymDungeonEnv", "make_env", "register_gym_envs"]
