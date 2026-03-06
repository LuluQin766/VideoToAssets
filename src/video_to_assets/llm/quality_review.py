from __future__ import annotations

import json
from pathlib import Path

from video_to_assets.config import AppConfig
from video_to_assets.llm.client import LLMClient


class QualityReviewer:
    def __init__(self, config: AppConfig, client: LLMClient):
        self.config = config
        self.client = client

    def run(self, cleaned_plain_file: Path, llm_review_dir: Path) -> dict[str, Path]:
        llm_review_dir.mkdir(parents=True, exist_ok=True)
        prompt_file = self.config.prompts_root / "review" / "quality_check.md"
        prompt = self.client.load_prompt(prompt_file)
        content = cleaned_plain_file.read_text(encoding="utf-8", errors="ignore")

        response = self.client.generate(prompt=prompt, content=content, task="quality_review")

        quality_report = llm_review_dir / "quality_report.md"
        issues_json = llm_review_dir / "issues_found.json"
        suggestions_md = llm_review_dir / "repair_suggestions.md"
        raw_json = llm_review_dir / "quality_raw_response.json"

        quality_report.write_text(
            f"# Quality Report\n\nmode: `{response.mode}`\n\n{response.text}\n",
            encoding="utf-8",
        )

        issues = self._heuristic_issues(content)
        issues_json.write_text(json.dumps(issues, ensure_ascii=False, indent=2), encoding="utf-8")

        suggestions_md.write_text(
            "# Repair Suggestions\n\n"
            "- 复核专有名词、人名、数字\n"
            "- 检查可能重复句并合并\n"
            "- 对长句做断句与标点修复\n",
            encoding="utf-8",
        )
        raw_json.write_text(json.dumps(response.raw, ensure_ascii=False, indent=2), encoding="utf-8")

        return {
            "quality_report": quality_report,
            "issues_found": issues_json,
            "repair_suggestions": suggestions_md,
            "quality_raw_response": raw_json,
        }

    def _heuristic_issues(self, text: str) -> dict:
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        duplicate_count = len(lines) - len(set(lines))
        return {
            "line_count": len(lines),
            "duplicate_line_count": max(0, duplicate_count),
            "risk_flags": [
                "possible_asr_errors",
                "possible_missing_punctuation",
            ],
        }
