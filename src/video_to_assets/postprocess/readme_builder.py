from __future__ import annotations

import json
from pathlib import Path

from video_to_assets.pipeline.state import PipelineState


class VideoReadmeBuilder:
    def build(self, state: PipelineState, stage_status: dict, output_file: Path) -> None:
        info = state.metadata
        stages = stage_status.get("stages", {})
        root = state.paths.root
        source_info = self._load_source_info(root / "source" / "source_info.json")
        timestamps_present = self._timestamps_present(root)

        asset_groups = {
            "Source & Canonical": [
                "source/source_info.json",
                "source/source_info.md",
                "source/source_snapshot.txt",
                "normalized/canonical_content.json",
                "normalized/clean_text.txt",
                "normalized/structured_text.md",
            ],
            "Round1 Core": [
                "metadata/video_info.json",
                "metadata/video_info.md",
                "subtitles_clean/cleaned_plain.txt",
                "subtitles_clean/cleaned_with_timestamps.txt",
                "llm_review/quality_report.md",
                "llm_review/polished_full_text.md",
            ],
            "Summaries": [
                "summaries/one_line_summary.txt",
                "summaries/executive_summary.md",
                "summaries/outline.md",
                "summaries/topic_map.md",
                "summaries/key_quotes.md",
                "summaries/entities.md",
            ],
            "Source Attribution": [
                "source_attribution/source_profile.md",
                "source_attribution/source_profile.json",
                "source_attribution/publishing_notes.md",
            ],
            "WeChat Articles": [
                "articles_wechat/article_01.md",
                "articles_wechat/article_02.md",
                "articles_wechat/article_03.md",
                "articles_wechat/titles.txt",
                "articles_wechat/article_sources.md",
            ],
            "Xiaohongshu Posts": [
                "articles_xiaohongshu/xhs_01.md",
                "articles_xiaohongshu/xhs_02.md",
                "articles_xiaohongshu/xhs_03.md",
                "articles_xiaohongshu/xhs_04.md",
                "articles_xiaohongshu/xhs_05.md",
            ],
            "Highlights": [
                "highlights/candidates_round1.json",
                "highlights/selected_round2.json",
                "highlights/top10_final.json",
                "highlights/highlights_table.md",
                "highlights/clip_plan.csv",
            ],
        }

        lines = [
            "# VideoToAssets Asset Index",
            "",
            f"- source_id: `{state.source_id or state.video_id}`",
            f"- source_type: {state.source_type}",
            f"- input_type: {state.input_type}",
            f"- source_url: {state.url or 'N/A'}",
            f"- title: {info.title if info else source_info.get('title', 'N/A')}",
            f"- source_metadata_complete: {state.source_metadata_complete}",
            f"- timestamps_present: {timestamps_present}",
            f"- tasks_requested: {', '.join(sorted(state.tasks)) if state.tasks else 'default'}",
            "",
            "## Stage Status",
            "",
        ]
        if state.input_type == "video":
            lines.extend(
                [
                    f"- subtitle_source: {state.subtitle_source}",
                    f"- asr_triggered: {state.asr_triggered}",
                    f"- asr_placeholder: {state.asr_placeholder}",
                ]
            )
        if source_info.get("input_info"):
            lines.append(f"- input_info: {source_info['input_info']}")

        for name, payload in stages.items():
            status = payload.get("status", "unknown")
            if name == "readme" and status == "running":
                continue
            notes = payload.get("notes") or ""
            lines.append(f"- {name}: {status} {notes}".strip())

        lines.extend(["", "## Navigable Asset Index", ""])
        for group_name, rel_paths in asset_groups.items():
            lines.append(f"### {group_name}")
            lines.append("")
            for rel in rel_paths:
                p = root / rel
                status = "OK" if p.exists() else "MISSING"
                lines.append(f"- [{rel}](./{rel}) - {status}")
            lines.append("")

        lines.extend(
            [
                "## Output Folders",
                "",
                "- source/",
                "- normalized/",
                "- metadata/",
                "- subtitles_raw/",
                "- asr/",
                "- subtitles_clean/",
                "- text_exports/",
                "- llm_review/",
                "- summaries/",
                "- articles_wechat/",
                "- articles_xiaohongshu/",
                "- highlights/",
                "- source_attribution/",
                "- logs/",
            ]
        )

        output_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _load_source_info(self, path: Path) -> dict:
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _timestamps_present(self, root: Path) -> bool:
        canonical = root / "normalized" / "canonical_content.json"
        if canonical.exists():
            try:
                payload = json.loads(canonical.read_text(encoding="utf-8"))
                return bool(payload.get("timestamps"))
            except Exception:
                return False
        return (root / "subtitles_clean" / "cleaned.json").exists()
