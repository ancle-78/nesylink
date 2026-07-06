from __future__ import annotations

from .common import MathematicalLogicReward


class MathematicalLogicTask3Reward(MathematicalLogicReward):
    reward_name = "mathematical_logic/task_3"
    reward_weights = {
        **MathematicalLogicReward.reward_weights,
        "room_changed": 1.0,
        "monster_hit": 0.5,
        "monster_kill": 4.0,
        "key_collected": 5.0,
        "keys_delta": 5.0,
        "door_opened": 10.0,
        "exit_reached": 8.0,
    }


def make_reward(**kwargs):
    return MathematicalLogicTask3Reward(**kwargs)
