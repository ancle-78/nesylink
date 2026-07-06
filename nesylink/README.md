# NesyLink

`nesylink` is the Gymnasium-compatible dungeon environment in this repo.

## Canonical API

Built-in task form:

```python
from nesylink.env import make_env

env = make_env(task_id="mathematical_logic/task_1")
```

Gymnasium registry form:

```python
import gymnasium as gym
import nesylink

env = gym.make("NesyLink-v0", task_id="mathematical_logic/task_1")
```

Direct map-plus-reward form:

>  TODO: 目前的 nesylink 仍在更改，需要调整说明文档
```python
from nesylink.env import make_env

env = make_env(
    map_id="dungeon",
    reward_id="sparse_exit",
    max_steps=500,
)
```

Equivalent custom-path form:

```python
env = make_env(
    map_path="nesylink/map_data/mathematical_logic/task_5/dungeon.json",
    reward_module="nesylink.rewards.collect_key",
    reward_kwargs={"step": -0.01, "keys_delta": 5.0},
)
```

Human-play / debug entrypoint:

```bash
python -m nesylink.game --rooms nesylink/map_data/mathematical_logic/task_5/dungeon.json
```
use z for slot A and x for slot B. hold for multi-tile interactions like chests and NPCs.

## Package Layout

- `core/`: game runtime, state, world loading, mechanics, rendering, and human input
- `rewards/`: reward calculation modules and loader
- `tasks/`: Python task specs and built-in task registry
- `wrappers/`: Gymnasium and Dreamer-facing adapters
- `env.py`: public training facade exposing `make_env(...)`
- `game.py`: pygame human-play/debug runner

## Boundaries

- map JSON only builds the world
- `core` owns game mechanics and runtime state
- Python task specs compose maps, rewards, episode limits, and mission text
- reward modules compute reward and task-driven termination flags
- wrappers expose agent-facing APIs without owning mechanics
- `info` exposes generic state, events, episode metadata, and `info["reward"]`

## Map Rules

Map JSON may contain:

- layout
- spawns
- objects
- exits
- room graph / dungeon root references

Map JSON must not contain:

- `task_id`
- `task_type`
- `reward`
- `success_condition`
- `failure_condition`
- `progress`

## Task Rules

Builtin task specs live under `nesylink/tasks/`.

- tasks are Python data, not YAML
- tasks reference a map by `map_id` or `map_path`
- tasks reference a reward by `reward_id` or `reward_module`
- tasks may define `max_steps`, `action_repeat`, and `mission`
- tasks can be created with `make_env(task_id="...")`
- built-in tasks are also registered with Gymnasium IDs

## Reward Rules

Builtin reward modules live under `nesylink/rewards/`.

- `BaseReward` maintains `prev_obs` / `prev_info`
- `BaseReward` extracts common reward signals
- concrete reward files usually only define `reward_name`, `reward_weights`, and `make_reward(**kwargs)`

## Gymnasium Contract

```python
obs, info = env.reset(seed=0)
obs, reward, terminated, truncated, info = env.step(action)
```

Action semantics:

- `0`: wait
- `1..4`: move up/down/left/right
- `5`: trigger slot `A`
- `6`: trigger slot `B`

Default equipment:

- slot `A` starts with `sword`
- slot `B` starts with `shield`
- `A` still prioritizes chest/NPC interaction when a target is in range
- `shield` blocks contact damage and applies knockback/stun, but does not deal damage
- `sword` is the only default item that can damage or kill monsters
- sword/shield poses persist for several ticks in render output to make image-based learning easier

`info["reward"]` contains:

- `reward_name`
- `reward_signals`
- `reward_weights`
- `terminated`
- `terminated_reason`
