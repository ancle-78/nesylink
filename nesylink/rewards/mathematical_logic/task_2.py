from __future__ import annotations

from .common import MathematicalLogicReward


class MathematicalLogicTask2Reward(MathematicalLogicReward):
    reward_name = "mathematical_logic/task_2"
    reward_weights = {
        **MathematicalLogicReward.reward_weights,
        "monster_hit": 1.0,
        "monster_kill": 8.0,
        "key_collected": 5.0,
        "keys_delta": 5.0,
        "trap_triggered": -2.0,
        "hp_loss": -2.0,
        "door_opened": 10.0,
        "exit_reached": 10.0,
    }


def make_reward(**kwargs):
    return MathematicalLogicTask2Reward(**kwargs)
