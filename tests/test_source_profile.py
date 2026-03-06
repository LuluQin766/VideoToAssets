import json
from dataclasses import dataclass
from pathlib import Path

from video_to_assets.canonical.normalizer import build_canonical
from video_to_assets.postprocess.source_profile import SourceProfileBuilder


@dataclass
class DummyConfig:
    prompts_root: Path


@dataclass
class DummyResp:
    text: str


class DummyClient:
    def load_prompt(self, path: Path) -> str:
        return path.read_text(encoding="utf-8")

    def generate(self, prompt: str, content: str, task: str):
        return DummyResp(text=f"{task} generated")


def test_source_profile_outputs(tmp_path: Path):
    root = Path(__file__).resolve().parents[1]
    builder = SourceProfileBuilder(config=DummyConfig(prompts_root=root / "prompts"), client=DummyClient())

    cleaned = tmp_path / "cleaned_plain.txt"
    cleaned.write_text("这是测试文本。", encoding="utf-8")

    canonical = build_canonical(
        source_id="vid1",
        source_type="video",
        title="Demo",
        raw_text="测试内容",
        source_metadata={"video_id": "vid1", "title": "Demo", "webpage_url": "https://example.com"},
        attribution={"source_type": "video"},
    )
    out = builder.run(canonical, cleaned, tmp_path / "source_attribution")

    profile_json = out["source_profile_json"]
    payload = json.loads(profile_json.read_text(encoding="utf-8"))
    assert payload["source_type"] == "video"
    assert "派生整理" in payload["disclaimer"]
    assert out["publishing_notes"].exists()
