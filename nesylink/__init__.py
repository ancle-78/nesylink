from __future__ import annotations

from typing import Any

from .env import make_env, register_gym_envs

__version__ = "0.1.0"

register_gym_envs()

__all__ = ["DungeonEnv", "ZeldaLikeGame", "__version__", "make_env", "register_gym_envs"]


def __getattr__(name: str) -> Any:
    if name == "ZeldaLikeGame":
        from .game import ZeldaLikeGame

        return ZeldaLikeGame
    if name == "DungeonEnv":
        from .env import DungeonEnv

        return DungeonEnv
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
