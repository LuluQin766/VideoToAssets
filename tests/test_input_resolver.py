import pytest

from video_to_assets.pipeline.input_resolver import resolve_source_input


def test_resolve_video_default():
    src = resolve_source_input(input_type=None, url="https://example.com/video")
    assert src.input_type == "video"
    assert src.url == "https://example.com/video"


def test_resolve_text_conflict():
    with pytest.raises(ValueError):
        resolve_source_input(input_type="text", text="a", text_file="b.txt")


def test_resolve_file_missing():
    with pytest.raises(ValueError):
        resolve_source_input(input_type="file")


def test_resolve_text_file():
    src = resolve_source_input(input_type="text", text_file="demo.txt")
    assert src.input_type == "text"
    assert src.file_path is not None
