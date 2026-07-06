# NesyLink Tasks

Tasks are registered in Python. They compose map selection, reward selection,
episode defaults, Gymnasium ID, and mission text without putting task logic into
map JSON.

## Built-in Tasks

- `mathematical_logic/task_1` -> `NesyLink-MathematicalLogic-Task1-v0`
- `mathematical_logic/task_2` -> `NesyLink-MathematicalLogic-Task2-v0`
- `mathematical_logic/task_3` -> `NesyLink-MathematicalLogic-Task3-v0`
- `mathematical_logic/task_4` -> `NesyLink-MathematicalLogic-Task4-v0`
- `mathematical_logic/task_5` -> `NesyLink-MathematicalLogic-Task5-v0`

Task ids use `theme/task_name` so future themes can reuse names like `task_1`
without colliding.

## Use a Task

```python
from nesylink.env import make_env

env = make_env(task_id="mathematical_logic/task_1")
```

or through Gymnasium:

```python
import gymnasium as gym
import nesylink

env = gym.make("NesyLink-MathematicalLogic-Task1-v0")
```

## Register a Custom Task

```python
from nesylink.tasks import TaskSpec, register_task

register_task(TaskSpec(
    task_id="my_task",
    gym_id="NesyLink-MyTask-v0",
    map_id="dungeon",
    reward_id="sparse_exit",
    max_steps=500,
    mission="Reach the exit.",
))
```

Map JSON still only describes the world: layout, spawns, objects, exits, and
room graph data. Reward and task metadata belong in `TaskSpec` or direct
`make_env(...)` arguments.
