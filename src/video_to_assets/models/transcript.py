from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class TranscriptSegment:
    start: float
    end: float
    text: str
    source: str = "unknown"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Transcript:
    segments: list[TranscriptSegment] = field(default_factory=list)
    source: str = "unknown"

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "segments": [seg.to_dict() for seg in self.segments],
        }

    def plain_text(self) -> str:
        return "\n".join(seg.text.strip() for seg in self.segments if seg.text.strip())

    def with_timestamps(self) -> str:
        lines = []
        for seg in self.segments:
            lines.append(f"[{format_ts(seg.start)} - {format_ts(seg.end)}] {seg.text.strip()}")
        return "\n".join(lines)


def format_ts(seconds: float) -> str:
    if seconds < 0:
        seconds = 0
    s = int(seconds)
    hh = s // 3600
    mm = (s % 3600) // 60
    ss = s % 60
    ms = int((seconds - int(seconds)) * 1000)
    return f"{hh:02d}:{mm:02d}:{ss:02d},{ms:03d}"
