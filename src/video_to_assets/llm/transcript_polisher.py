from __future__ import annotations

import json
from pathlib import Path

from video_to_assets.config import AppConfig
from video_to_assets.llm.client import LLMClient


class TranscriptPolisher:
    def __init__(self, config: AppConfig, client: LLMClient):
        self.config = config
        self.client = client

    def run(self, cleaned_plain_file: Path, llm_review_dir: Path) -> dict[str, Path]:
        llm_review_dir.mkdir(parents=True, exist_ok=True)

        prompt_file = self.config.prompts_root / "polish" / "full_text_polish.md"
        prompt = self.client.load_prompt(prompt_file)
        content = cleaned_plain_file.read_text(encoding="utf-8", errors="ignore")

        response = self.client.generate(prompt=prompt, content=content, task="polish_full_text")

        polished = llm_review_dir / "polished_full_text.md"
        topic_structured = llm_review_dir / "topic_structured_text.md"
        readable = llm_review_dir / "readable_essay_version.md"
        raw_json = llm_review_dir / "polish_raw_response.json"

        polished_text = response.text.strip() or content
        polished.write_text(f"# Polished Full Text\n\n{polished_text}\n", encoding="utf-8")

        topic_structured.write_text(
            "# Topic Structured Text\n\n"
            "## Main Flow\n\n"
            f"{polished_text}\n",
            encoding="utf-8",
        )

        readable.write_text(f"# Readable Essay Version\n\n{polished_text}\n", encoding="utf-8")
        raw_json.write_text(json.dumps(response.raw, ensure_ascii=False, indent=2), encoding="utf-8")

        return {
            "polished_full_text": polished,
            "topic_structured_text": topic_structured,
            "readable_essay_version": readable,
            "polish_raw_response": raw_json,
        }
