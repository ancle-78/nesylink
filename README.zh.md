<div align="center">

# NesyLink

*一个兼容 Gymnasium 的 Zelda-like 地牢强化学习环境。*

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/) [![Gymnasium](https://img.shields.io/badge/Gymnasium-compatible-2ea44f.svg)](https://gymnasium.farama.org/) [![Package](https://img.shields.io/badge/install-pip%20install%20-e%20.-orange.svg)](#安装) [![Docs](https://img.shields.io/badge/docs-local-lightgrey.svg)](docs/README.md)

[安装](#安装) · [快速开始](#快速开始) · [内置任务](#内置任务) · [架构](#架构) · [奖励](#奖励) · [训练](#训练) · [文档](#文档) · [English](readme.md)

</div>

---

`nesylink` 是一个面向强化学习实验的小型地牢游戏环境。项目将游戏机制、JSON 地图、Python 任务定义、奖励模块和 Gymnasium wrapper 分离，用户既可以直接使用内置任务，也可以在不修改核心引擎的情况下组合自己的环境。

## 安装

从源码安装：

```bash
git clone <repo-url>
cd nesylink
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

可选依赖：

```bash
pip install -e ".[pygame]"   # 人类游玩 / 调试入口
pip install -e ".[dreamer]"  # Dreamer 风格图像处理依赖
```

## 快速开始

通过 Gymnasium 注册 ID 创建环境：

```python
import gymnasium as gym
import nesylink

env = gym.make("NesyLink-MathematicalLogic-Task1-v0")
obs, info = env.reset(seed=0)

obs, reward, terminated, truncated, info = env.step(env.action_space.sample())

env.close()
```

需要覆盖任务默认值时，使用直接工厂：

```python
from nesylink.env import make_env

env = make_env(
    task_id="mathematical_logic/task_1",
    max_steps=500,
    reward_kwargs={"step": -0.01},
)
```

## 内置任务

| task_id | Gymnasium ID | 目标 |
|---|---|---|
| `mathematical_logic/task_1` | `NesyLink-MathematicalLogic-Task1-v0` | 收集钥匙并打开出口。 |
| `mathematical_logic/task_2` | `NesyLink-MathematicalLogic-Task2-v0` | 击败怪物、收集钥匙并到达出口。 |
| `mathematical_logic/task_3` | `NesyLink-MathematicalLogic-Task3-v0` | 跨房间收集钥匙，返回起点并打开出口。 |
| `mathematical_logic/task_4` | `NesyLink-MathematicalLogic-Task4-v0` | 旋转桥、收集装备、击败守卫并打开最终宝箱。 |
| `mathematical_logic/task_5` | `NesyLink-MathematicalLogic-Task5-v0` | 探索多房间地牢并完成宝箱目标。 |

在 Python 中查看任务：

```python
from nesylink.tasks import list_tasks

for task in list_tasks():
    print(task.task_id, task.gym_id)
```

## 架构

```text
nesylink/
  env.py              make_env(...) 门面和 Gymnasium 注册
  tasks/              Python TaskSpec 注册表
  core/               运行时、状态、机制、地图加载、渲染
  rewards/            奖励模块和奖励信号提取
  wrappers/           Gymnasium 和 Dreamer 适配层
  map_data/           内置 JSON 地图
  tools/              地图工具
```

设计边界：

- JSON 地图只定义世界：房间、布局、对象、出口和出生点。
- Python task 组合地图、奖励、episode 长度、action repeat 和任务说明。
- reward 模块计算标量奖励和由奖励触发的终止条件。
- Gymnasium wrapper 暴露 `reset`、`step`、`render`、spaces 和 `info`。

## 奖励

通过 `reward_id` 选择内置奖励：

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

自定义奖励是暴露 `make_reward(**kwargs)` 的 Python 模块。
详见 [奖励参考](docs/reference/rewards.md)。

## 训练

训练前先跑随机策略 smoke test：

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

PPO 风格和 Dreamer 风格训练配置见
[训练配置指南](docs/guides/training-config.md)。

## 文档

- [文档入口](docs/README.md)
- [环境总览](docs/guides/env-overview.md)
- [地图创建](docs/guides/map-creation.md)
- [训练配置](docs/guides/training-config.md)
- [环境 API](docs/reference/env-api.md)
- [奖励](docs/reference/rewards.md)
- [任务](docs/reference/tasks-and-validators.md)

## 开发检查

```bash
python -m unittest discover -s tests
```
