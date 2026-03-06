from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from video_to_assets.canonical.canonical_content import CanonicalContent


def write_canonical_outputs(
    canonical: CanonicalContent,
    output_root: Path,
    source_snapshot: str,
    input_info: dict[str, Any],
) -> dict[str, Path]:
    source_dir = output_root / "source"
    normalized_dir = output_root / "normalized"
    source_dir.mkdir(parents=True, exist_ok=True)
    normalized_dir.mkdir(parents=True, exist_ok=True)

    source_info = {
        "source_id": canonical.source_id,
        "source_type": canonical.source_type,
        "title": canonical.title,
        "input_info": input_info,
        "source_metadata": canonical.source_metadata,
        "attribution": canonical.attribution,
        "processing_flags": canonical.processing_flags,
    }

    source_info_json = source_dir / "source_info.json"
    source_info_md = source_dir / "source_info.md"
    source_snapshot_txt = source_dir / "source_snapshot.txt"

    source_info_json.write_text(json.dumps(source_info, ensure_ascii=False, indent=2), encoding="utf-8")
    source_info_md.write_text(_to_markdown(source_info), encoding="utf-8")
    source_snapshot_txt.write_text(source_snapshot or canonical.raw_text, encoding="utf-8")

    canonical_json = normalized_dir / "canonical_content.json"
    clean_text = normalized_dir / "clean_text.txt"
    structured_md = normalized_dir / "structured_text.md"

    canonical_json.write_text(json.dumps(canonical.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    clean_text.write_text(canonical.clean_text, encoding="utf-8")
    structured_md.write_text(_structured_text(canonical), encoding="utf-8")

    return {
        "source_info_json": source_info_json,
        "source_info_md": source_info_md,
        "source_snapshot": source_snapshot_txt,
        "canonical_json": canonical_json,
        "clean_text": clean_text,
        "structured_text": structured_md,
    }


def _to_markdown(source_info: dict[str, Any]) -> str:
    lines = [
        f"# {source_info.get('title', 'Untitled')}",
        "",
        f"- source_id: `{source_info.get('source_id')}`",
        f"- source_type: {source_info.get('source_type')}",
    ]
    input_info = source_info.get("input_info") or {}
    for key in ["input_type", "source_name", "source_url", "author", "publish_date", "platform"]:
        if input_info.get(key):
            lines.append(f"- {key}: {input_info.get(key)}")
    lines.append("")
    lines.append("## Source Metadata")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(source_info.get("source_metadata") or {}, ensure_ascii=False, indent=2))
    lines.append("```")
    lines.append("")
    lines.append("## Attribution")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(source_info.get("attribution") or {}, ensure_ascii=False, indent=2))
    lines.append("```")
    return "\n".join(lines) + "\n"


def _structured_text(canonical: CanonicalContent) -> str:
    paragraphs = [p.strip() for p in canonical.raw_text.split("\n\n") if p.strip()]
    body = "\n\n".join(paragraphs) if paragraphs else canonical.clean_text
    return f"# {canonical.title}\n\n{body}\n"
