from pathlib import Path

from video_to_assets.storage.path_manager import PathManager


def test_infer_video_id_from_url(tmp_path: Path):
    pm = PathManager(tmp_path)
    vid = pm.infer_video_id("https://www.youtube.com/watch?v=abc123_DEF")
    assert vid == "abc123_DEF"


def test_ensure_paths(tmp_path: Path):
    pm = PathManager(tmp_path)
    paths = pm.ensure("video_x")
    assert paths.root.exists()
    assert paths.metadata.exists()
    assert paths.logs.exists()
    assert paths.summaries.exists()
    assert paths.articles_wechat.exists()
    assert paths.articles_xiaohongshu.exists()
    assert paths.highlights.exists()
    assert paths.source_attribution.exists()
