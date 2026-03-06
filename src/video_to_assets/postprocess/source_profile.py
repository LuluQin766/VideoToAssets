from __future__ import annotations

import json
from pathlib import Path

from video_to_assets.config import AppConfig
from video_to_assets.llm.client import LLMClient
from video_to_assets.models.video_info import VideoInfo


class SourceProfileBuilder:
    def __init__(self, config: AppConfig, client: LLMClient):
        self.config = config
        self.client = client

    def run(
        self,
        metadata: VideoInfo | None,
        cleaned_plain_file: Path,
        output_dir: Path,
    ) -> dict[str, Path]:
        output_dir.mkdir(parents=True, exist_ok=True)
        source_md = output_dir / "source_profile.md"
        source_json = output_dir / "source_profile.json"
        publishing_notes = output_dir / "publishing_notes.md"

        transcript_excerpt = cleaned_plain_file.read_text(encoding="utf-8", errors="ignore")[:4000]
        profile_payload = {
            "source_type": "video_transcript_derivative",
            "disclaimer": "本目录下的摘要、文章与高光候选均为基于原视频转写内容的再整理，不代表原作者以外的新原创观点。",
            "video": {
                "video_id": metadata.video_id if metadata else "unknown",
                "title": metadata.title if metadata else "unknown",
                "url": metadata.webpage_url if metadata else "unknown",
                "uploader": metadata.uploader if metadata else "unknown",
                "upload_date": metadata.upload_date if metadata else "unknown",
                "duration": metadata.duration if metadata else None,
            },
            "traceability": {
                "base_files": [
                    "metadata/video_info.json",
                    "subtitles_clean/cleaned_plain.txt",
                    "subtitles_clean/cleaned_with_timestamps.txt",
                ],
                "verification_rules": [
                    "引用语句应可回溯到 cleaned_with_timestamps.txt",
                    "涉及事实性主张时需人工复核原视频",
                    "发布前检查是否引入未出现的新结论",
                ],
            },
        }
        source_json.write_text(json.dumps(profile_payload, ensure_ascii=False, indent=2), encoding="utf-8")

        prompt_profile = self.client.load_prompt(self.config.prompts_root / "source/source_profile.md")
        profile_text = self.client.generate(
            prompt=prompt_profile,
            content=json.dumps(profile_payload, ensure_ascii=False) + "\n\n" + transcript_excerpt,
            task="source_profile",
        ).text

        source_md.write_text(
            "# Source Profile\n\n"
            f"{profile_text.strip() or profile_payload['disclaimer']}\n\n"
            "## Core Disclaimer\n\n"
            f"{profile_payload['disclaimer']}\n",
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
