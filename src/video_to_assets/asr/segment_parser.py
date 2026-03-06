from __future__ import annotations

import re
from pathlib import Path

from video_to_assets.models.transcript import Transcript, TranscriptSegment


SRT_BLOCK_RE = re.compile(
    r"(?:^|\n)(\d+)\s*\n(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*\n(.*?)(?=\n\d+\s*\n|\Z)",
    re.DOTALL,
)


def parse_srt_to_transcript(path: Path, source: str = "asr") -> Transcript:
    content = path.read_text(encoding="utf-8", errors="ignore")
    segments: list[TranscriptSegment] = []
    for _, start, end, text in SRT_BLOCK_RE.findall(content):
        clean = " ".join(t.strip() for t in text.splitlines() if t.strip())
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
