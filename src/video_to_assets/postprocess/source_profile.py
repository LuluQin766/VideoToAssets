from __future__ import annotations

import json
from pathlib import Path

from video_to_assets.config import AppConfig
from video_to_assets.llm.client import LLMClient
from video_to_assets.canonical.canonical_content import CanonicalContent


class SourceProfileBuilder:
    def __init__(self, config: AppConfig, client: LLMClient):
        self.config = config
        self.client = client

    def run(self, canonical: CanonicalContent, cleaned_plain_file: Path, output_dir: Path) -> dict[str, Path]:
        output_dir.mkdir(parents=True, exist_ok=True)
        source_md = output_dir / "source_profile.md"
        source_json = output_dir / "source_profile.json"
        publishing_notes = output_dir / "publishing_notes.md"

        transcript_excerpt = cleaned_plain_file.read_text(encoding="utf-8", errors="ignore")[:4000]
        profile_payload = self._build_payload(canonical)
        source_json.write_text(json.dumps(profile_payload, ensure_ascii=False, indent=2), encoding="utf-8")

        prompt_profile = self.client.load_prompt(self.config.prompts_root / "source/source_profile.md")
        profile_text = self.client.generate(
            prompt=prompt_profile,
            content=json.dumps(profile_payload, ensure_ascii=False) + "\n\n" + transcript_excerpt,
            task="source_profile",
        ).text

        warning_block = ""
        if not profile_payload.get("metadata_complete", True):
            warning_block = "\n## Metadata Warning\n\n来源元数据不完整，请在发布前补全与校验。\n"

        source_md.write_text(
            "# Source Profile\n\n"
            f"{profile_text.strip() or profile_payload['disclaimer']}\n\n"
            "## Core Disclaimer\n\n"
            f"{profile_payload['disclaimer']}\n"
            f"{warning_block}",
            encoding="utf-8",
        )

        prompt_notes = self.client.load_prompt(self.config.prompts_root / "source/publishing_notes.md")
        notes_text = self.client.generate(
            prompt=prompt_notes,
            content=transcript_excerpt,
            task="publishing_notes",
        ).text
        if not notes_text.strip():
            notes_text = (
                "1. 需标注原视频来源与链接\n"
                "2. 引用观点属于原视频内容，不可表述为自有原创观点\n"
                "3. 数据、时间、人名等信息建议二次核验\n"
            )
        publishing_notes.write_text(f"# Publishing Notes\n\n{notes_text}\n", encoding="utf-8")

        return {
            "source_profile_md": source_md,
            "source_profile_json": source_json,
            "publishing_notes": publishing_notes,
        }

    def _build_payload(self, canonical: CanonicalContent) -> dict:
        source_type = canonical.source_type
        metadata_complete = self._metadata_complete(canonical.source_metadata, source_type)
        disclaimer = (
            "本目录下的摘要、文章与高光候选均为基于原始来源内容的派生整理，不代表原作者之外的新原创观点。"
            if source_type == "video"
            else "本目录下的摘要、文章与高光候选均为基于用户提供文本/文件的派生整理，不代表平台发布者以外的新原创观点。"
        )
        base_files = ["normalized/clean_text.txt", "normalized/canonical_content.json"]
        if source_type == "video":
            base_files = [
                "metadata/video_info.json",
                "subtitles_clean/cleaned_plain.txt",
                "subtitles_clean/cleaned_with_timestamps.txt",
                "normalized/clean_text.txt",
                "normalized/canonical_content.json",
            ]

        warnings = []
        if not metadata_complete:
            warnings.append("source metadata incomplete")

        payload = {
            "source_type": source_type,
            "source_id": canonical.source_id,
            "title": canonical.title,
            "metadata_complete": metadata_complete,
            "disclaimer": disclaimer,
            "source_metadata": canonical.source_metadata,
            "attribution": canonical.attribution,
            "warnings": warnings,
            "traceability": {
                "base_files": base_files,
                "verification_rules": [
                    "引用语句应可回溯到 clean_text.txt 或原始来源",
                    "涉及事实性主张时需人工复核原始来源",
                    "发布前检查是否引入未出现的新结论",
                ],
            },
        }
        return payload

    def _metadata_complete(self, metadata: dict, source_type: str) -> bool:
        if source_type == "video":
            required = ["video_id", "title", "webpage_url"]
        else:
            required = ["source_name", "source_url"]
        return all(metadata.get(key) for key in required)
