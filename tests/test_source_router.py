from pathlib import Path

from video_to_assets.models.source_input import SourceInput
from video_to_assets.pipeline.source_router import SourceRouter


def test_source_router_text(tmp_path: Path):
    router = SourceRouter(tmp_path)
    src = SourceInput(input_type="text", text="测试内容", title="Demo")
    canonical = router.route(src)
    assert canonical.source_type == "text"
    assert canonical.clean_text


def test_source_router_file(tmp_path: Path):
    sample = tmp_path / "demo.txt"
    sample.write_text("文件内容", encoding="utf-8")
    router = SourceRouter(tmp_path)
    src = SourceInput(input_type="file", file_path=sample, title="Demo File")
    canonical = router.route(src)
    assert canonical.source_type == "file"
    assert "文件内容" in canonical.raw_text
