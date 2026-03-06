from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class TimestampSegment:
    start: float
    end: float
    text: str


@dataclass
class CanonicalContent:
    source_id: str
    source_type: str
    title: str
    raw_text: str
    clean_text: str
    language: str | None = None
    timestamps: list[TimestampSegment] = field(default_factory=list)
    source_metadata: dict[str, Any] = field(default_factory=dict)
    attribution: dict[str, Any] = field(default_factory=dict)
    structure_hints: dict[str, Any] = field(default_factory=dict)
    processing_flags: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["timestamps"] = [asdict(seg) for seg in self.timestamps]
        return data
