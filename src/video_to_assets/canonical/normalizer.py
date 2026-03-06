from __future__ import annotations

import re
from typing import Any

from video_to_assets.canonical.canonical_content import CanonicalContent, TimestampSegment


SPACE_RE = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    return SPACE_RE.sub(" ", text).strip()


def build_canonical(
    source_id: str,
    source_type: str,
    title: str | None,
    raw_text: str,
    language: str | None = None,
    timestamps: list[TimestampSegment] | None = None,
    source_metadata: dict[str, Any] | None = None,
    attribution: dict[str, Any] | None = None,
    structure_hints: dict[str, Any] | None = None,
    processing_flags: dict[str, Any] | None = None,
) -> CanonicalContent:
    clean_text = normalize_text(raw_text)
    return CanonicalContent(
        source_id=source_id,
        source_type=source_type,
        title=title or "Untitled",
        raw_text=raw_text,
        clean_text=clean_text,
        language=language,
        timestamps=timestamps or [],
        source_metadata=source_metadata or {},
        attribution=attribution or {},
        structure_hints=structure_hints or {},
        processing_flags=processing_flags or {},
    )
