# NesyLink Rewards

Rewards are Python objects that convert one environment transition into a
scalar reward. Maps do not contain reward values. Tasks select a reward module
and may provide default reward settings.

## Built-in Rewards

| reward_id | Module | Intended use |
|---|---|---|
| `custom_reward` | `nesylink.rewards.custom_template` | starter template |
| `mathematical_logic/task_1` | `nesylink.rewards.mathematical_logic.task_1` | mathematical logic key-door task |
| `mathematical_logic/task_2` | `nesylink.rewards.mathematical_logic.task_2` | mathematical logic monster/key/exit task |
| `mathematical_logic/task_3` | `nesylink.rewards.mathematical_logic.task_3` | mathematical logic multi-room return task |
| `mathematical_logic/task_4` | `nesylink.rewards.mathematical_logic.task_4` | mathematical logic bridge/equipment/guardian task |
| `mathematical_logic/task_5` | `nesylink.rewards.mathematical_logic.task_5` | mathematical logic multi-room exploration task |

## BaseReward

`BaseReward` is the unified reward core.

Responsibilities:

- maintain `prev_obs` / `prev_info`
- extract stable reward signals from `prev_obs/obs/prev_info/info/action`
- compute weighted reward via `reward_weights`
- support task-specific shaping via `extra_reward()`
- support task-specific termination via `check_termination()`

Common signals:

- `step`
- `hp_delta`
- `hp_loss`
- `gold_delta`
- `keys_delta`
- `monster_hit`
- `monster_kill`
- `key_collected`
- `gold_collected`
- `item_collected`
- `agent_healed`
- `agent_damaged`
- `trap_triggered`
- `abyss_fall`
- `shield_block`
- `door_opened`
- `chest_opened`
- `chest_revealed`
- `button_pressed`
- `switch_activated`
- `bridge_rotated`
- `dynamic_object_state_changed`
- `talked_npc`
- `room_changed`
- `exit_reached`
- `environment_completed`
- `world_completed`
- `death`
- `invalid_action`
- `player_tile_changed`
- `monster_hp_total`
- `active_monsters`

`BaseReward.compute_reward(...)` multiplies each signal by its configured
weight, then adds any `extra_reward(...)` returned by a subclass.

## Reward Selection

Use a built-in reward:

```python
from nesylink.env import make_env

env = make_env(map_id="mathematical_logic/task_1", reward_id="mathematical_logic/task_1")
```

Override weights:

```python
env = make_env(
    map_id="mathematical_logic/task_1",
    reward_id="mathematical_logic/task_1",
    reward_kwargs={
        "step": -0.01,
        "keys_delta": 5.0,
        "door_opened": 3.0,
        "exit_reached": 20.0,
        "death": -10.0,
        "invalid_action": -0.05,
    },
)
```

Use a custom module:

```python
env = make_env(
    map_id="dungeon",
    reward_module="experiments.rewards.my_reward",
    reward_kwargs={"step": -0.02},
)
```

## Reward Module Contract

Each concrete reward module must expose:

```python
def make_reward(**kwargs):
    ...
```

Typical custom reward:

```python
from nesylink.rewards.base import BaseReward


class MyReward(BaseReward):
    reward_name = "my_reward"
    reward_weights = {
        "step": -0.01,
        "gold_delta": 1.0,
        "keys_delta": 5.0,
        "exit_reached": 50.0,
        "death": -20.0,
    }


def make_reward(**kwargs):
    return MyReward(**kwargs)
```

## Reward-driven Termination

A reward can terminate an episode by overriding `check_termination(...)`:

```python
class ExitReward(BaseReward):
    reward_name = "exit_reward"
    reward_weights = {"step": -0.01, "exit_reached": 20.0}

    def check_termination(self, signals, obs, info, action=None):
        if signals.get("exit_reached", 0) > 0:
            return True, "exit_reached"
        return False, None
```

The environment merges base termination, such as death or world completion, with
reward-driven termination.

## Inspecting Reward Metadata

Every step stores reward metadata in `info["reward"]`:

```python
obs, reward, terminated, truncated, info = env.step(action)
print(info["reward"]["reward_name"])
print(info["reward"]["reward_signals"])
print(info["reward"]["reward_weights"])
print(info["reward"]["terminated"])
print(info["reward"]["terminated_reason"])
```

Use this metadata during training. It is the fastest way to confirm whether a
learning problem is caused by missing events, weak weights, or an unreachable
map objective.
