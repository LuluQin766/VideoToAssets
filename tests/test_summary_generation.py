from dataclasses import dataclass
from pathlib import Path

from video_to_assets.postprocess.summary_generator import SummaryGenerator


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
        return DummyResp(text=f"{task} output")


def test_summary_outputs_created(tmp_path: Path):
    root = Path(__file__).resolve().parents[1]
    generator = SummaryGenerator(config=DummyConfig(prompts_root=root / "prompts"), client=DummyClient())

    cleaned = tmp_path / "cleaned_plain.txt"
    cleaned.write_text("第一句。第二句。第三句。", encoding="utf-8")

    out = generator.run(cleaned, tmp_path / "summaries")
    required = {
        "one_line_summary",
        "executive_summary",
        "outline",
        "topic_map",
        "key_quotes",
        "entities",
    }
    assert required == set(out.keys())
    assert out["one_line_summary"].exists()
    assert "summary_one_line output" in out["one_line_summary"].read_text(encoding="utf-8")
