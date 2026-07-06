from __future__ import annotations

from typing import Any

from ..base import BaseReward


class MathematicalLogicReward(BaseReward):
    reward_weights = {
        "step": -0.01,
        "world_completed": 50.0,
        "environment_completed": 50.0,
        "death": -20.0,
        "invalid_action": -0.05,
    }

    def check_termination(
        self,
        signals: dict[str, Any],
        obs: Any,
        info: dict[str, Any],
        action: int | None = None,
    ) -> tuple[bool, str | None]:
        del obs, info, action
        if signals.get("world_completed", 0) > 0 or signals.get("environment_completed", 0) > 0:
            reason = signals.get("terminal_reason")
            return True, str(reason or "world_completed")
        if signals.get("death", 0) > 0:
            return True, "agent_dead"
        return False, None
