from __future__ import annotations

TASK_ALL = "all"
TASK_SUMMARY = "summary"
TASK_WECHAT = "wechat"
TASK_XHS = "xhs"
TASK_HIGHLIGHTS = "highlights"

VALID_TASKS = {TASK_ALL, TASK_SUMMARY, TASK_WECHAT, TASK_XHS, TASK_HIGHLIGHTS}
ROUND2_TASKS = {TASK_SUMMARY, TASK_WECHAT, TASK_XHS, TASK_HIGHLIGHTS}


def normalize_tasks(values: list[str] | None) -> set[str]:
    if not values:
        return set(ROUND2_TASKS)

    expanded: set[str] = set()
    for value in values:
        parts = [x.strip().lower() for x in value.split(",") if x.strip()]
        expanded.update(parts)

    invalid = expanded - VALID_TASKS
    if invalid:
        raise ValueError(f"Unsupported tasks: {sorted(invalid)}")

    if TASK_ALL in expanded:
        return set(ROUND2_TASKS)
    return expanded


def should_run(task_set: set[str], task: str) -> bool:
    return task in task_set
