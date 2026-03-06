from __future__ import annotations

import json
import re
from pathlib import Path

from video_to_assets.models.transcript import Transcript, TranscriptSegment


SRT_BLOCK_RE = re.compile(
    r"(?:^|\n)(\d+)\s*\n(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*\n(.*?)(?=\n\d+\s*\n|\Z)",
    re.DOTALL,
)
VTT_BLOCK_RE = re.compile(
    r"(?:^|\n)(\d{2}:\d{2}:\d{2}\.\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}\.\d{3})\s*\n(.*?)(?=\n\n|\Z)",
    re.DOTALL,
)


def normalize_transcript(source_file: Path, source: str) -> Transcript:
    suffix = source_file.suffix.lower()
    if suffix == ".json":
        return _from_json(source_file, source)
    if suffix == ".vtt":
        return _from_vtt(source_file, source)
    return _from_srt(source_file, source)


def _from_json(path: Path, source: str) -> Transcript:
    data = json.loads(path.read_text(encoding="utf-8"))
    segs = []
    for seg in data.get("segments", []):
        text = str(seg.get("text", "")).strip()
        if not text:
            continue
        segs.append(
            TranscriptSegment(
                start=float(seg.get("start", 0.0)),
                end=float(seg.get("end", seg.get("start", 0.0))),
                text=text,
                source=source,
            )
        )
    return Transcript(segments=segs, source=source)


def _from_srt(path: Path, source: str) -> Transcript:
    content = path.read_text(encoding="utf-8", errors="ignore")
    segments: list[TranscriptSegment] = []
    for _, start, end, text in SRT_BLOCK_RE.findall(content):
        clean = " ".join(line.strip() for line in text.splitlines() if line.strip())
        if not clean:
            continue
        segments.append(
            TranscriptSegment(
                start=_to_seconds(start),
                end=_to_seconds(end),
                text=clean,
                source=source,
            )
        )
    return Transcript(segments=segments, source=source)


def _from_vtt(path: Path, source: str) -> Transcript:
    content = path.read_text(encoding="utf-8", errors="ignore")
    segments: list[TranscriptSegment] = []
    for start, end, text in VTT_BLOCK_RE.findall(content):
        clean = " ".join(line.strip() for line in text.splitlines() if line.strip())
        if not clean:
            continue
        segments.append(
            TranscriptSegment(
                start=_to_seconds(start),
                end=_to_seconds(end),
                text=clean,
                source=source,
            )
        )
    return Transcript(segments=segments, source=source)


def _to_seconds(ts: str) -> float:
    ts = ts.replace(",", ".")
    hh, mm, rest = ts.split(":")
    sec = float(rest)
    return int(hh) * 3600 + int(mm) * 60 + sec
