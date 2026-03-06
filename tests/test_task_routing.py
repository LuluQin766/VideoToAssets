import pytest

from video_to_assets.pipeline.task_router import normalize_tasks, should_run


def test_normalize_all_and_comma_separated():
    tasks = normalize_tasks(["summary,wechat", "xhs", "highlights"])
    assert tasks == {"summary", "wechat", "xhs", "highlights"}
    assert should_run(tasks, "summary")


def test_normalize_all_keyword():
    tasks = normalize_tasks(["all"])
    assert tasks == {"summary", "wechat", "xhs", "highlights"}


def test_invalid_task_raises():
    with pytest.raises(ValueError):
        normalize_tasks(["summary", "bad_task"])
