from __future__ import annotations

from .common import MathematicalLogicReward


class MathematicalLogicTask1Reward(MathematicalLogicReward):
    reward_name = "mathematical_logic/task_1"
    reward_weights = {
        **MathematicalLogicReward.reward_weights,
        "key_collected": 5.0,
        "keys_delta": 5.0,
        "door_opened": 10.0,
        "exit_reached": 10.0,
    }


def make_reward(**kwargs):
    return MathematicalLogicTask1Reward(**kwargs)
