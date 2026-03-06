from __future__ import annotations

import json
from pathlib import Path

from video_to_assets.models.transcript import Transcript, format_ts


def export_transcript_files(
    transcript: Transcript,
    subtitles_clean_dir: Path,
    text_exports_dir: Path,
    title: str = "Video Transcript",
) -> dict[str, Path]:
    subtitles_clean_dir.mkdir(parents=True, exist_ok=True)
    text_exports_dir.mkdir(parents=True, exist_ok=True)

    cleaned_srt = subtitles_clean_dir / "cleaned.srt"
    cleaned_json = subtitles_clean_dir / "cleaned.json"
    cleaned_ts = subtitles_clean_dir / "cleaned_with_timestamps.txt"
    cleaned_plain = subtitles_clean_dir / "cleaned_plain.txt"

    full_ts = text_exports_dir / "full_with_timestamps.txt"
    full_plain = text_exports_dir / "full_plain.txt"
    full_md = text_exports_dir / "full_markdown.md"

    cleaned_srt.write_text(_to_srt(transcript), encoding="utf-8")
    cleaned_json.write_text(json.dumps(transcript.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    cleaned_ts.write_text(transcript.with_timestamps(), encoding="utf-8")
    plain = transcript.plain_text()
    cleaned_plain.write_text(plain, encoding="utf-8")

    full_ts.write_text(transcript.with_timestamps(), encoding="utf-8")
    full_plain.write_text(plain, encoding="utf-8")
    full_md.write_text(f"# {title}\n\n{plain}\n", encoding="utf-8")

    return {
        "cleaned_srt": cleaned_srt,
        "cleaned_json": cleaned_json,
        "cleaned_with_timestamps": cleaned_ts,
        "cleaned_plain": cleaned_plain,
        "full_with_timestamps": full_ts,
        "full_plain": full_plain,
        "full_markdown": full_md,
    }


def _to_srt(transcript: Transcript) -> str:
    lines = []
    for idx, seg in enumerate(transcript.segments, start=1):
        lines.append(str(idx))
        lines.append(f"{format_ts(seg.start)} --> {format_ts(seg.end)}")
        lines.append(seg.text)
        lines.append("")
    return "\n".join(lines)
