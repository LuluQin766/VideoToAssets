from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from video_to_assets.canonical.canonical_content import TimestampSegment


SRT_BLOCK_RE = re.compile(
    r"(?:^|\n)(\d+)\s*\n(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*\n(.*?)(?=\n\d+\s*\n|\Z)",
    re.DOTALL,
)
VTT_BLOCK_RE = re.compile(
    r"(?:^|\n)(\d{2}:\d{2}:\d{2}\.\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}\.\d{3})\s*\n(.*?)(?=\n\n|\Z)",
    re.DOTALL,
)


def parse_txt(path: Path) -> tuple[str, list[TimestampSegment]]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    return text, []


def parse_md(path: Path) -> tuple[str, list[TimestampSegment]]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    return text, []


def parse_srt(path: Path) -> tuple[str, list[TimestampSegment]]:
    content = path.read_text(encoding="utf-8", errors="ignore")
    segments: list[TimestampSegment] = []
    texts: list[str] = []
    for _, start, end, text in SRT_BLOCK_RE.findall(content):
        clean = " ".join(line.strip() for line in text.splitlines() if line.strip())
        if not clean:
            continue
        segments.append(TimestampSegment(start=_to_seconds(start), end=_to_seconds(end), text=clean))
        texts.append(clean)
    return "\n".join(texts), segments


def parse_vtt(path: Path) -> tuple[str, list[TimestampSegment]]:
    content = path.read_text(encoding="utf-8", errors="ignore")
    segments: list[TimestampSegment] = []
    texts: list[str] = []
    for start, end, text in VTT_BLOCK_RE.findall(content):
        clean = " ".join(line.strip() for line in text.splitlines() if line.strip())
        if not clean:
            continue
        segments.append(TimestampSegment(start=_to_seconds(start), end=_to_seconds(end), text=clean))
        texts.append(clean)
    return "\n".join(texts), segments


def parse_json(path: Path) -> tuple[str, list[TimestampSegment], dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    segments: list[TimestampSegment] = []
    if isinstance(payload, dict) and "segments" in payload:
        for seg in payload.get("segments", []):
            text = str(seg.get("text", "")).strip()
            if not text:
                continue
            start = float(seg.get("start", 0.0))
            end = float(seg.get("end", start))
            segments.append(TimestampSegment(start=start, end=end, text=text))
    raw_text = "\n".join(seg.text for seg in segments) if segments else json.dumps(payload, ensure_ascii=False)
    return raw_text, segments, payload


def _to_seconds(ts: str) -> float:
    ts = ts.replace(",", ".")
    hh, mm, rest = ts.split(":")
    sec = float(rest)
    return int(hh) * 3600 + int(mm) * 60 + sec
