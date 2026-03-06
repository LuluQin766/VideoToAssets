from __future__ import annotations

from pathlib import Path

from video_to_assets.config import AppConfig
from video_to_assets.llm.client import LLMClient
from video_to_assets.models.video_info import VideoInfo


class WechatArticleGenerator:
    def __init__(self, config: AppConfig, client: LLMClient):
        self.config = config
        self.client = client

    def run(
        self,
        cleaned_plain_file: Path,
        summary_file: Path,
        source_profile_file: Path,
        output_dir: Path,
        metadata: VideoInfo | None,
        source_title: str | None = None,
        source_type: str | None = None,
    ) -> dict[str, Path]:
        output_dir.mkdir(parents=True, exist_ok=True)

        base_content = self._compose_input(cleaned_plain_file, summary_file, source_profile_file)
        titles = self._generate_titles(base_content)

        outputs: dict[str, Path] = {}
        source_context = self._resolve_source_context(source_profile_file, metadata, source_title, source_type)
        for idx in range(1, 4):
            article_path = output_dir / f"article_{idx:02d}.md"
            title = titles[idx - 1] if idx - 1 < len(titles) else f"文章方案 {idx}"
            body = self._generate_article(base_content, idx, title)
            source_line = f"\n\n> 来源说明：{source_context['note']}\n"
            article_path.write_text(f"# {title}\n\n{body}{source_line}", encoding="utf-8")
            outputs[f"article_{idx:02d}"] = article_path

        titles_file = output_dir / "titles.txt"
        titles_file.write_text("\n".join(titles[:3]) + "\n", encoding="utf-8")

        source_file = output_dir / "article_sources.md"
        source_file.write_text(
            "# Article Sources\n\n"
            "- Base content: `normalized/clean_text.txt`\n"
            "- Summary layer: `summaries/executive_summary.md`\n"
            "- Source profile: `source_attribution/source_profile.json`\n"
            "- 注意：文章内容为衍生整理，不可冒充原始一手观点。\n",
            encoding="utf-8",
        )

        outputs["titles"] = titles_file
        outputs["article_sources"] = source_file
        return outputs

    def _compose_input(self, cleaned_plain_file: Path, summary_file: Path, source_profile_file: Path) -> str:
        cleaned = cleaned_plain_file.read_text(encoding="utf-8", errors="ignore")[:22000]
        summary = summary_file.read_text(encoding="utf-8", errors="ignore")[:6000] if summary_file.exists() else ""
        source = source_profile_file.read_text(encoding="utf-8", errors="ignore")[:4000] if source_profile_file.exists() else ""
        return f"{summary}\n\n{source}\n\n{cleaned}"

    def _generate_titles(self, content: str) -> list[str]:
        prompt = self.client.load_prompt(self.config.prompts_root / "wechat/titles.md")
        resp = self.client.generate(prompt=prompt, content=content, task="wechat_titles")
        lines = [x.strip(" -\t") for x in resp.text.splitlines() if x.strip()]
        if len(lines) < 3:
            lines = [
                "从视频到行动：核心方法全拆解",
                "把观点落地：一次完整的实践路线图",
                "高密度复盘：这段内容真正有价值的部分",
            ]
        return lines[:3]

    def _generate_article(self, content: str, idx: int, title: str) -> str:
        prompt = self.client.load_prompt(self.config.prompts_root / "wechat/article_generation.md")
        body = self.client.generate(
            prompt=prompt,
            content=f"Article variant {idx}\nTitle: {title}\n\n{content}",
            task=f"wechat_article_{idx}",
        ).text
        if not body.strip():
            body = (
                "## 开篇\n\n"
                "本文基于视频转写内容进行结构化整理。\n\n"
                "## 核心观点\n\n"
                "- 观点一\n- 观点二\n\n"
                "## 落地建议\n\n"
                "1. 先做最小可行实践\n2. 再逐步扩展\n"
            )
        return body

    def _resolve_source_context(
        self,
        source_profile_file: Path,
        metadata: VideoInfo | None,
        source_title: str | None,
        source_type: str | None,
    ) -> dict[str, str]:
        profile = {}
        if source_profile_file.exists():
            try:
                import json

                profile = json.loads(source_profile_file.read_text(encoding="utf-8"))
            except Exception:
                profile = {}
        resolved_type = source_type or profile.get("source_type") or ("video" if metadata else "text")
        resolved_title = source_title or (metadata.title if metadata else None) or profile.get("title") or "未知标题"
        if resolved_type == "video":
            note = f"本文基于视频《{resolved_title}》转写内容整理，非原视频作者新发布观点。"
        elif resolved_type == "file":
            note = f"本文基于用户提供的文件《{resolved_title}》内容整理，非原发布者新发布观点。"
        else:
            note = f"本文基于用户提供文本《{resolved_title}》整理，非原发布者新发布观点。"
        return {"source_type": resolved_type, "title": resolved_title, "note": note}


class XiaohongshuPostGenerator:
    def __init__(self, config: AppConfig, client: LLMClient):
        self.config = config
        self.client = client

    def run(
        self,
        cleaned_plain_file: Path,
        output_dir: Path,
        metadata: VideoInfo | None,
        source_profile_file: Path | None = None,
        source_title: str | None = None,
        source_type: str | None = None,
    ) -> dict[str, Path]:
        output_dir.mkdir(parents=True, exist_ok=True)
        content = cleaned_plain_file.read_text(encoding="utf-8", errors="ignore")[:20000]
        prompt = self.client.load_prompt(self.config.prompts_root / "xhs/post_generation.md")

        source_context = self._resolve_source_context(source_profile_file, metadata, source_title, source_type)
        outputs: dict[str, Path] = {}
        for idx in range(1, 6):
            p = output_dir / f"xhs_{idx:02d}.md"
            text = self.client.generate(prompt=prompt, content=f"Post variant {idx}\n\n{content}", task=f"xhs_post_{idx}").text
            if not text.strip():
                text = self._fallback_post(idx)
            text += (
                "\n\n---\n"
                f"来源：{source_context['note']}\n"
            )
            p.write_text(text, encoding="utf-8")
            outputs[f"xhs_{idx:02d}"] = p
        return outputs

    def _fallback_post(self, idx: int) -> str:
        return (
            f"# 主题短帖 {idx}\n\n"
            "今天复盘了一段视频内容，最有启发的是：\n"
            "1. 把大目标拆到当天可执行\n"
            "2. 先验证再扩展，不盲目堆动作\n"
            "3. 记录反馈，形成自己的方法库\n\n"
            "你最近在执行中最卡的一步是什么？\n"
            "#学习方法 #效率提升 #内容复盘"
        )

    def _resolve_source_context(
        self,
        source_profile_file: Path | None,
        metadata: VideoInfo | None,
        source_title: str | None,
        source_type: str | None,
    ) -> dict[str, str]:
        profile = {}
        if source_profile_file and source_profile_file.exists():
            try:
                import json

                profile = json.loads(source_profile_file.read_text(encoding="utf-8"))
            except Exception:
                profile = {}
        resolved_type = source_type or profile.get("source_type") or ("video" if metadata else "text")
        resolved_title = source_title or (metadata.title if metadata else None) or profile.get("title") or "未知标题"
        if resolved_type == "video":
            note = f"基于视频《{resolved_title}》转写整理，非原视频作者新发布原文。"
        elif resolved_type == "file":
            note = f"基于用户提供文件《{resolved_title}》整理，非原发布者新发布原文。"
        else:
            note = f"基于用户提供文本《{resolved_title}》整理，非原发布者新发布原文。"
        return {"source_type": resolved_type, "title": resolved_title, "note": note}
