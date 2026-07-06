from __future__ import annotations

from .specs import TaskSpec


_TASKS_BY_ID: dict[str, TaskSpec] = {}
_TASKS_BY_GYM_ID: dict[str, TaskSpec] = {}


def register_task(task: TaskSpec) -> TaskSpec:
    if task.task_id in _TASKS_BY_ID:
        raise ValueError(f"duplicate task_id '{task.task_id}'")
    if task.gym_id in _TASKS_BY_GYM_ID:
        raise ValueError(f"duplicate gym_id '{task.gym_id}'")
    _TASKS_BY_ID[task.task_id] = task
    _TASKS_BY_GYM_ID[task.gym_id] = task
    return task


def get_task(task_id: str) -> TaskSpec:
    try:
        return _TASKS_BY_ID[task_id]
    except KeyError as exc:
        available = ", ".join(sorted(_TASKS_BY_ID))
        raise ValueError(f"unknown task_id '{task_id}', available: {available}") from exc


def get_task_by_gym_id(gym_id: str) -> TaskSpec:
    try:
        return _TASKS_BY_GYM_ID[gym_id]
    except KeyError as exc:
        available = ", ".join(sorted(_TASKS_BY_GYM_ID))
        raise ValueError(f"unknown gym_id '{gym_id}', available: {available}") from exc


def list_tasks() -> tuple[TaskSpec, ...]:
    return tuple(_TASKS_BY_ID[key] for key in sorted(_TASKS_BY_ID))
