# NesyLink Environment Overview

`nesylink` is a small Zelda-like dungeon environment exposed through
Gymnasium. The project is intentionally split into map data, mechanics,
rewards, tasks, and API wrappers so an RL user can change one concern without
rewiring the rest of the environment.

## Quick Start

```python
import gymnasium as gym
import nesylink

env = gym.make("NesyLink-MathematicalLogic-Task1-v0")
obs, info = env.reset(seed=0)

done = False
while not done:
    action = env.action_space.sample()
    obs, reward, terminated, truncated, info = env.step(action)
    done = terminated or truncated

env.close()
```

The direct factory gives more control:

```python
from nesylink.env import make_env

env = make_env(
    task_id="mathematical_logic/task_1",
    max_steps=500,
    render_mode="rgb_array",
)
```

## Architecture

```text
nesylink/
  env.py              public make_env(...) facade and Gymnasium registration
  tasks/              Python task specs for built-in and custom tasks
  core/               game runtime, state, world loading, mechanics, rendering
  rewards/            reward functions and reward signal extraction
  wrappers/           Gymnasium and Dreamer-facing adapters
  map_data/           built-in JSON maps
  tools/              map migration/export utilities
```

Runtime responsibilities:

- `core/world` loads and validates room JSON.
- `core/mechanics` applies movement, interaction, combat, traps, doors, and
  episode-end mechanics.
- `core/observation.py` converts runtime state into structured observations.
- `core/info.py` exposes events, inventory, entities, and episode metadata.
- `rewards` computes scalar rewards and optional reward-driven termination.
- `tasks` composes map, reward, max steps, action repeat, and mission text.
- `wrappers/gym_env.py` exposes the Gymnasium API.

## Built-in Tasks

| task_id | Gymnasium ID | Map | Reward |
|---|---|---|---|
| `mathematical_logic/task_1` | `NesyLink-MathematicalLogic-Task1-v0` | `mathematical_logic/task_1` | `mathematical_logic/task_1` |
| `mathematical_logic/task_2` | `NesyLink-MathematicalLogic-Task2-v0` | `mathematical_logic/task_2` | `mathematical_logic/task_2` |
| `mathematical_logic/task_3` | `NesyLink-MathematicalLogic-Task3-v0` | `mathematical_logic/task_3` | `mathematical_logic/task_3` |
| `mathematical_logic/task_4` | `NesyLink-MathematicalLogic-Task4-v0` | `mathematical_logic/task_4` | `mathematical_logic/task_4` |
| `mathematical_logic/task_5` | `NesyLink-MathematicalLogic-Task5-v0` | `mathematical_logic/task_5` | `mathematical_logic/task_5` |

Use a built-in task when you want a stable, named environment:

```python
env = make_env(task_id="mathematical_logic/task_2")
```

Use direct map/reward construction when experimenting:

```python
env = make_env(
    map_id="dungeon",
    reward_id="exploration",
    reward_kwargs={"step": -0.01, "room_changed": 1.0},
    max_steps=500,
)
```

## Core Concepts

Maps are pure world definitions. They contain layouts, spawns, objects, exits,
and room graph references. They should not contain reward weights or task
success criteria.

Rewards are Python modules. A reward reads `obs`, `info`, and the previous
transition context to produce a scalar reward and optional task termination.

Tasks are Python specs. A task says which map and reward to use, plus training
defaults such as `max_steps`, `action_repeat`, and mission text.

Wrappers adapt the same game runtime to different agent APIs. The canonical
wrapper is Gymnasium.

## Actions

| ID | Meaning |
|---:|---|
| 0 | wait |
| 1 | move up |
| 2 | move down |
| 3 | move left |
| 4 | move right |
| 5 | trigger slot A / interact |
| 6 | trigger slot B / shield |

Slot A starts with a sword and also handles nearby chest or NPC interaction.
Slot B starts with a shield.

## Observation and Info

The observation is a Gymnasium `spaces.Dict` with grid, player, inventory, and
monster fields. The `info` dictionary is the main debugging and reward-shaping
surface; it includes episode counters, events, inventory, entities, terminal
reason, and `info["reward"]` metadata.

Use `info["events"]["records"]` and `info["events"]["counts"]` when debugging
why a reward did or did not trigger.
