from __future__ import annotations

from .base import BaseReward
from .context import RewardContext, build_reward_context, extract_reward_signals
from .loader import load_reward, load_reward_module, resolve_reward_module
from .mathematical_logic import (
    MathematicalLogicTask1Reward,
    MathematicalLogicTask2Reward,
    MathematicalLogicTask3Reward,
    MathematicalLogicTask4Reward,
    MathematicalLogicTask5Reward,
)
from .custom_template import CustomReward

__all__ = [
    "BaseReward",
    "CollectGoldReward",
    "CollectKeyReward",
    "ExplorationReward",
    "KillMonsterReward",
    "MathematicalLogicTask1Reward",
    "MathematicalLogicTask2Reward",
    "MathematicalLogicTask3Reward",
    "MathematicalLogicTask4Reward",
    "MathematicalLogicTask5Reward",
    "RewardContext",
    "SparseExitReward",
    "build_reward_context",
    "extract_reward_signals",
    "load_reward",
    "load_reward_module",
    "resolve_reward_module",
    "CustomReward",
]
