from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


TS_RE = re.compile(r"\d{2}:\d{2}:\d{2}[,.]\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}[,.]\d{3}")
VTT_TS_RE = re.compile(r"\d{2}:\d{2}:\d{2}[.]\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}[.]\d{3}")


@dataclass
class ValidationResult:
    valid: bool
    reasons: list[str] = field(default_factory=list)
    metrics: dict[str, float | int] = field(default_factory=dict)


class SubtitleValidator:
    def __init__(self, min_entries: int = 10, max_duplicate_line_ratio: float = 0.7):
        self.min_entries = min_entries
        self.max_duplicate_line_ratio = max_duplicate_line_ratio

    def validate(self, path: Path) -> ValidationResult:
        reasons: list[str] = []
        metrics: dict[str, float | int] = {}

        if not path.exists() or not path.is_file():
            return ValidationResult(False, ["file_not_found"], {})

        text = path.read_text(encoding="utf-8", errors="ignore")
        if not text.strip():
            return ValidationResult(False, ["empty_file"], {})

        timestamps = TS_RE.findall(text)
        if path.suffix.lower() == ".vtt":
            timestamps.extend(VTT_TS_RE.findall(text))

        lines = self._extract_content_lines(text)
        unique_lines = {x.strip().lower() for x in lines if x.strip()}

        entry_count = len(timestamps)
        line_count = len(lines)
        unique_count = len(unique_lines)
        duplicate_ratio = 1 - (unique_count / line_count) if line_count else 1.0

        metrics.update(
            {
                "entry_count": entry_count,
                "line_count": line_count,
                "unique_line_count": unique_count,
                "duplicate_ratio": round(duplicate_ratio, 4),
                "char_count": len(text),
            }
        )

        if entry_count < self.min_entries:
            reasons.append("too_few_entries")
        if duplicate_ratio > self.max_duplicate_line_ratio:
            reasons.append("too_many_duplicates")
        if len(text.strip()) < 120:
            reasons.append("too_short")

        return ValidationResult(valid=not reasons, reasons=reasons, metrics=metrics)

    def _extract_content_lines(self, text: str) -> list[str]:
        lines = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.isdigit():
                continue
            if "-->" in stripped:
                continue
            if stripped.upper() == "WEBVTT":
                continue
            lines.append(stripped)
        return lines
