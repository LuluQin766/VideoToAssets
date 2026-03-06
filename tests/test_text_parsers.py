import json
from pathlib import Path

from video_to_assets.parsers import text_parsers


def test_parse_srt(tmp_path: Path):
    srt = tmp_path / "demo.srt"
    srt.write_text(
        "1\n00:00:00,000 --> 00:00:01,000\n第一句\n\n2\n00:00:01,000 --> 00:00:02,000\n第二句\n",
        encoding="utf-8",
    )
    text, segments = text_parsers.parse_srt(srt)
    assert "第一句" in text
    assert len(segments) == 2


def test_parse_vtt(tmp_path: Path):
    vtt = tmp_path / "demo.vtt"
    vtt.write_text(
        "00:00:00.000 --> 00:00:01.000\nHello\n\n00:00:01.000 --> 00:00:02.000\nWorld\n",
        encoding="utf-8",
    )
    text, segments = text_parsers.parse_vtt(vtt)
    assert "Hello" in text
    assert len(segments) == 2


def test_parse_json(tmp_path: Path):
    js = tmp_path / "demo.json"
    payload = {"segments": [{"start": 0.0, "end": 1.0, "text": "A"}, {"start": 1.0, "end": 2.0, "text": "B"}]}
    js.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    text, segments, meta = text_parsers.parse_json(js)
    assert "A" in text
    assert len(segments) == 2
    assert meta["segments"][0]["text"] == "A"
