from dataclasses import dataclass
from pathlib import Path

from video_to_assets.models.video_info import VideoInfo
from video_to_assets.postprocess.article_generators import WechatArticleGenerator


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
        if task == "wechat_titles":
            return DummyResp(text="标题一\n标题二\n标题三")
        return DummyResp(text="## 小节\n\n内容")


def test_wechat_article_files_and_source_note(tmp_path: Path):
    root = Path(__file__).resolve().parents[1]
    generator = WechatArticleGenerator(config=DummyConfig(prompts_root=root / "prompts"), client=DummyClient())

    cleaned = tmp_path / "cleaned_plain.txt"
    cleaned.write_text("正文内容", encoding="utf-8")
    summary = tmp_path / "executive_summary.md"
    summary.write_text("摘要", encoding="utf-8")
    source_profile = tmp_path / "source_profile.json"
    source_profile.write_text("{}", encoding="utf-8")

    out = generator.run(
        cleaned_plain_file=cleaned,
        summary_file=summary,
        source_profile_file=source_profile,
        output_dir=tmp_path / "articles_wechat",
        metadata=VideoInfo(video_id="v", title="Video"),
    )

    article1 = out["article_01"]
    assert article1.exists()
    text = article1.read_text(encoding="utf-8")
    assert text.startswith("# 标题一")
    assert "来源说明" in text
    assert out["titles"].exists()
