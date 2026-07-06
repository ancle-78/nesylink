from __future__ import annotations

import importlib
from types import ModuleType

from .base import BaseReward


BUILTIN_REWARD_MODULES = {
    "custom_reward": "nesylink.rewards.custom_template",
    "mathematical_logic/task_1": "nesylink.rewards.mathematical_logic.task_1",
    "mathematical_logic/task_2": "nesylink.rewards.mathematical_logic.task_2",
    "mathematical_logic/task_3": "nesylink.rewards.mathematical_logic.task_3",
    "mathematical_logic/task_4": "nesylink.rewards.mathematical_logic.task_4",
    "mathematical_logic/task_5": "nesylink.rewards.mathematical_logic.task_5",
}


def resolve_reward_module(module_or_path: str | ModuleType) -> ModuleType:
    module = importlib.import_module(module_or_path) if isinstance(module_or_path, str) else module_or_path
    make_reward = getattr(module, "make_reward", None)
    if not callable(make_reward):
        raise ValueError(f"reward module '{module.__name__}' must define callable make_reward(**kwargs)")
    return module


def load_reward(
    *,
    reward_id: str | None = None,
    reward_module: str | ModuleType | None = None,
    reward_kwargs: dict[str, float] | None = None,
) -> BaseReward:
    kwargs = dict(reward_kwargs or {})

    if reward_module is not None:
        module = resolve_reward_module(reward_module)
        reward = module.make_reward(**kwargs)
    elif reward_id is not None:
        try:
            module_name = BUILTIN_REWARD_MODULES[reward_id]
        except KeyError as exc:
            available = ", ".join(sorted(BUILTIN_REWARD_MODULES))
            raise ValueError(f"unknown reward_id '{reward_id}', available: {available}") from exc
        module = resolve_reward_module(module_name)
        reward = module.make_reward(**kwargs)
    else:
        reward = BaseReward(**kwargs)

    if not isinstance(reward, BaseReward):
        raise TypeError(
            "make_reward(**kwargs) must return an instance of nesylink.rewards.base.BaseReward"
        )
    return reward


def load_reward_module(module_or_path: str | ModuleType) -> ModuleType:
    return resolve_reward_module(module_or_path)
