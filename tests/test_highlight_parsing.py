import json
from pathlib import Path

from video_to_assets.postprocess.highlight_miner import HighlightMiner


def test_highlight_json_roundtrip(tmp_path: Path):
    cleaned_json = tmp_path / "cleaned.json"
    cleaned_json.write_text(
        json.dumps(
            {
                "segments": [
                    {"start": 0.0, "end": 8.0, "text": "核心方法是先验证再扩展，不要盲目投入。"},
                    {"start": 8.0, "end": 16.0, "text": "这一步能显著降低试错成本，并提升传播效率。"},
                    {"start": 16.0, "end": 25.0, "text": "关键在于建立可追溯的来源链路和可复用模板。"},
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    miner = HighlightMiner()
    out = miner.run(cleaned_json, tmp_path / "highlights")

    parsed = miner.parse_candidates_file(out["top10_final"])
    assert parsed
    assert len(parsed) <= 10
    assert all(item.score >= 30 for item in parsed)
    assert out["clip_plan"].exists()


def test_highlight_paragraph_mode(tmp_path: Path):
    miner = HighlightMiner()
    text = "第一段落内容，包含一些可传播的观点和建议。\n\n第二段落继续补充细节与步骤。"
    out = miner.run_from_canonical("text", text, tmp_path / "highlights")
    parsed = miner.parse_candidates_file(out["top10_final"])
    assert parsed
    assert parsed[0].start is None
    assert parsed[0].paragraph_id is not None
