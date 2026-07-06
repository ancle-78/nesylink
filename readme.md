<div align="center">

# NesyLink

*A Gymnasium-compatible Zelda-like dungeon environment for reinforcement learning.*

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/) [![Gymnasium](https://img.shields.io/badge/Gymnasium-compatible-2ea44f.svg)](https://gymnasium.farama.org/) [![Package](https://img.shields.io/badge/install-pip%20install%20-e%20.-orange.svg)](#installation) [![Docs](https://img.shields.io/badge/docs-GitHub%20Pages-lightgrey.svg)](https://crazyjassbread.github.io/nesylink/)

[Installation](#installation) · [Quick Start](#quick-start) · [Built-in Tasks](#built-in-tasks) · [Architecture](#architecture) ·  [Rewards](#rewards) · [Training](#training) · [Documentation](#documentation) · [简体中文](README.zh.md)

</div>

---

`nesylink` provides a small, configurable dungeon game environment for RL experiments. It separates game mechanics, JSON maps, Python task specs, reward modules, and Gymnasium wrappers so users can start with built-in tasks or compose new environments without changing the core engine.

> 对于 26 年春季数理逻辑课程的大作业设置，详情见 [数理逻辑大作业说明](docs/Mathematical_logic/readme.md)。

## Installation

From source:

```bash
git clone https://github.com/CrazyJassBread/nesylink.git
cd nesylink
python -m venv .venv
source .venv/bin/activate
# use '.venv\Scripts\Activate.ps1' for PowerShell
pip install -e .
```

Optional extras:

```bash
pip install -e ".[pygame]"   # human-play/debug runner
pip install -e ".[dreamer]"  # Dreamer-style image helper dependencies
```

## Quick Start

Use Gymnasium registration:

```python
import gymnasium as gym
import nesylink

env = gym.make("NesyLink-MathematicalLogic-Task1-v0")
obs, info = env.reset(seed=0)

obs, reward, terminated, truncated, info = env.step(env.action_space.sample())

env.close()
```

Use the direct factory when you want to override task defaults:

```python
from nesylink.env import make_env

env = make_env(
    task_id="mathematical_logic/task_1",
    max_steps=500,
    reward_kwargs={"step": -0.01},
)
```

## Built-in Tasks

| task_id | Gymnasium ID | Objective |
|---|---|---|
| `mathematical_logic/task_1` | `NesyLink-MathematicalLogic-Task1-v0` | Collect a key and open the exit. |
| `mathematical_logic/task_2` | `NesyLink-MathematicalLogic-Task2-v0` | Defeat the monster, collect the key, and exit. |
| `mathematical_logic/task_3` | `NesyLink-MathematicalLogic-Task3-v0` | Travel across rooms, collect the key, return, and unlock the exit. |
| `mathematical_logic/task_4` | `NesyLink-MathematicalLogic-Task4-v0` | Rotate the bridge, collect equipment, defeat the guardian, and open the final chest. |
| `mathematical_logic/task_5` | `NesyLink-MathematicalLogic-Task5-v0` | Explore the multi-room dungeon and complete its chest objectives. |

List tasks in Python:

```python
from nesylink.tasks import list_tasks

for task in list_tasks():
    print(task.task_id, task.gym_id)
```

## Architecture

```text
nesylink/
  env.py              make_env(...) facade and Gymnasium registration
  tasks/              Python TaskSpec registry
  core/               runtime, state, mechanics, world loading, rendering
  rewards/            reward modules and reward signal extraction
  wrappers/           Gymnasium and Dreamer-facing adapters
  map_data/           built-in JSON maps
  tools/              map utilities
```

Design boundaries:

- JSON maps define only the world: rooms, layouts, objects, exits, and spawns.
- Python tasks compose maps, rewards, episode limits, action repeat, and mission text.
- Reward modules compute scalar rewards and reward-driven termination.
- Gymnasium wrappers expose `reset`, `step`, `render`, spaces, and `info`.

## Rewards

Select built-in rewards by `reward_id`:

```python
env = make_env(
    map_id="mathematical_logic/task_1",
    reward_id="mathematical_logic/task_1",
    reward_kwargs={
        "step": -0.01,
        "keys_delta": 5.0,
        "door_opened": 3.0,
        "exit_reached": 20.0,
    },
)
```

Custom rewards are Python modules exposing `make_reward(**kwargs)`.
See [reward reference](docs/reference/rewards.md).

## Training

Start with a random rollout smoke test:

```python
env = make_env(task_id="mathematical_logic/task_1")
obs, info = env.reset(seed=0)

for _ in range(100):
    action = env.action_space.sample()
    obs, reward, terminated, truncated, info = env.step(action)
    if terminated or truncated:
        break

print(info["terminal_reason"], info["reward"]["reward_signals"])
env.close()
```

For PPO-style and Dreamer-style configuration notes, see
[training configuration](docs/guides/training-config.md).

## Documentation

- [Documentation hub](docs/README.md)
- [Environment overview](docs/guides/env-overview.md)
- [Map creation](docs/guides/map-creation.md)
- [Training configuration](docs/guides/training-config.md)
- [Environment API](docs/reference/env-api.md)
- [Rewards](docs/reference/rewards.md)
- [Tasks](docs/reference/tasks-and-validators.md)
