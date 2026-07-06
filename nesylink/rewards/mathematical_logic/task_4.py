from __future__ import annotations

from .common import MathematicalLogicReward


class MathematicalLogicTask4Reward(MathematicalLogicReward):
    reward_name = "mathematical_logic/task_4"
    reward_weights = {
        **MathematicalLogicReward.reward_weights,
        "room_changed": 1.0,
        "switch_activated": 3.0,
        "bridge_rotated": 5.0,
        "key_collected": 5.0,
        "keys_delta": 5.0,
        "item_collected": 8.0,
        "monster_hit": 1.0,
        "monster_kill": 8.0,
        "chest_revealed": 5.0,
        "chest_opened": 3.0,
        "gold_delta": 2.0,
        "abyss_fall": -2.0,
        "hp_loss": -2.0,
        "exit_reached": 8.0,
    }


def make_reward(**kwargs):
    return MathematicalLogicTask4Reward(**kwargs)
