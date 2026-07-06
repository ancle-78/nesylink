# NesyLink Documentation

This documentation is focused on using `nesylink` as a Gymnasium-compatible
reinforcement learning environment.

## Recommended Reading Order

1. guides/env-overview.md ([open](guides/env-overview.md))
   - Environment architecture, package boundaries, built-in tasks, and the
     Gymnasium usage flow.
2. guides/map-creation.md ([open](guides/map-creation.md))
   - How to create JSON maps with rooms, objects, exits, and validation rules.
3. reference/game-content.md ([open](reference/game-content.md))
   - Current player capabilities, items, monsters, map object meanings, exit
     requirements, and built-in map content.
4. reference/rewards.md ([open](reference/rewards.md))
   - Built-in reward modules, reward signals, weight overrides, and custom
     rewards.
5. guides/training-config.md ([open](guides/training-config.md))
   - Practical training configuration patterns for random rollouts, PPO-style
     loops, and Dreamer-style wrappers.
6. reference/env-api.md ([open](reference/env-api.md))
   - Exact `reset`, `step`, action, observation, and `info` contracts.
7. reference/tasks-and-validators.md ([open](reference/tasks-and-validators.md))
   - Python task registry and task-level environment construction.

## Documentation Scope

Keep docs centered on:

- creating environments
- understanding the architecture
- authoring maps and tasks
- configuring rewards
- training RL agents
- reading observations, events, and episode metadata

Avoid adding evaluation process notes, contributor workflow logs, or unrelated
project history here unless they directly help a user run or extend the
environment.
