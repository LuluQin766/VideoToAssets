from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class SourceInput:
    input_type: str
    url: str | None = None
    text: str | None = None
    file_path: Path | None = None
    title: str | None = None
    source_name: str | None = None
    source_url: str | None = None
    author: str | None = None
    publish_date: str | None = None
    platform: str | None = None
    metadata: dict[str, Any] | None = None

    def validate(self) -> None:
        if self.input_type not in {"video", "text", "file"}:
            raise ValueError(f"Unsupported input_type: {self.input_type}")
        if self.input_type == "video" and not self.url:
            raise ValueError("video input requires url")
        if self.input_type == "text" and not (self.text or self.file_path):
            raise ValueError("text input requires text or text file")
        if self.input_type == "file" and not self.file_path:
            raise ValueError("file input requires file_path")
