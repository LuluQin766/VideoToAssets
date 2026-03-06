from pathlib import Path

from video_to_assets.canonical.normalizer import build_canonical
from video_to_assets.canonical.writer import write_canonical_outputs


def test_canonical_writer_outputs(tmp_path: Path):
    canonical = build_canonical(
        source_id="text_123",
        source_type="text",
        title="Demo",
        raw_text="原始文本内容",
        source_metadata={"source_name": "test"},
        attribution={"source_type": "text"},
    )
    out = write_canonical_outputs(
        canonical,
        tmp_path,
        source_snapshot="原始文本内容",
        input_info={"input_type": "text"},
    )
    assert out["source_info_json"].exists()
    assert out["source_snapshot"].exists()
    assert out["canonical_json"].exists()
    assert out["clean_text"].exists()
