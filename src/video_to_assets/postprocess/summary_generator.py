from __future__ import annotations

import re
from pathlib import Path

from video_to_assets.config import AppConfig
from video_to_assets.llm.client import LLMClient


class SummaryGenerator:
    def __init__(self, config: AppConfig, client: LLMClient):
        self.config = config
        self.client = client

    def run(self, cleaned_plain_file: Path, output_dir: Path) -> dict[str, Path]:
        output_dir.mkdir(parents=True, exist_ok=True)
        content = cleaned_plain_file.read_text(encoding="utf-8", errors="ignore")

        one_line = output_dir / "one_line_summary.txt"
        exec_summary = output_dir / "executive_summary.md"
        outline = output_dir / "outline.md"
        topic_map = output_dir / "topic_map.md"
        key_quotes = output_dir / "key_quotes.md"
        entities = output_dir / "entities.md"

        one_line.write_text(
            self._generate("summary_one_line", "summary/one_line_summary.md", content, fallback=self._one_line_fallback(content)),
            encoding="utf-8",
        )
        exec_summary.write_text(
            self._generate("summary_executive", "summary/executive_summary.md", content, markdown_header="# Executive Summary\n\n"),
            encoding="utf-8",
        )
        outline.write_text(
            self._generate("summary_outline", "summary/outline.md", content, markdown_header="# Outline\n\n"),
            encoding="utf-8",
        )
        topic_map.write_text(
            self._generate("summary_topic_map", "summary/topic_map.md", content, markdown_header="# Topic Map\n\n"),
            encoding="utf-8",
        )

        quotes_text = self._generate("summary_key_quotes", "summary/key_quotes.md", content)
        if not quotes_text.strip():
            quotes_text = self._quotes_fallback(content)
        key_quotes.write_text(f"# Key Quotes\n\n{quotes_text}\n", encoding="utf-8")

        entity_text = self._generate("summary_entities", "summary/entities.md", content)
        if not entity_text.strip():
            entity_text = self._entities_fallback(content)
        entities.write_text(f"# Entities\n\n{entity_text}\n", encoding="utf-8")

        return {
            "one_line_summary": one_line,
            "executive_summary": exec_summary,
            "outline": outline,
            "topic_map": topic_map,
            "key_quotes": key_quotes,
            "entities": entities,
        }

    def _generate(
        self,
        task: str,
        prompt_relative_path: str,
        content: str,
        markdown_header: str = "",
        fallback: str = "",
    ) -> str:
        prompt = self.client.load_prompt(self.config.prompts_root / prompt_relative_path)
        resp = self.client.generate(prompt=prompt, content=content, task=task)
        text = (resp.text or "").strip() or fallback
        if markdown_header:
            return f"{markdown_header}{text}\n"
        return text

    def _one_line_fallback(self, content: str) -> str:
        sentence = self._first_sentence(content)
        return sentence[:35] if sentence else "暂无可用总结"

    def _quotes_fallback(self, content: str) -> str:
        lines = [x.strip() for x in content.splitlines() if x.strip()]
        picks = lines[: min(8, len(lines))]
        return "\n".join(f"- \"{p[:140]}\"（来源：转写整理）" for p in picks)

    def _entities_fallback(self, content: str) -> str:
        tokens = re.findall(r"[A-Za-z][A-Za-z0-9_\-]{2,}|[\u4e00-\u9fff]{2,8}", content)
        seen = []
        for t in tokens:
            if t not in seen:
                seen.append(t)
            if len(seen) >= 30:
                break
        return "\n".join(
            [
                "## Concepts",
                *(f"- {x}" for x in seen[:12]),
                "",
                "## Terms (to verify)",
                *(f"- {x}" for x in seen[12:24]),
            ]
        )

    def _first_sentence(self, content: str) -> str:
        normalized = " ".join(x.strip() for x in content.splitlines() if x.strip())
        for sep in ["。", ".", "！", "?", "？"]:
            if sep in normalized:
                return normalized.split(sep)[0] + sep
        return normalized[:120]
