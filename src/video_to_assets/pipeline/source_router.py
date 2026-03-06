from __future__ import annotations

from pathlib import Path

from video_to_assets.adapters.base_adapter import BaseAdapter
from video_to_assets.adapters.file_adapter import FileAdapter
from video_to_assets.adapters.text_adapter import TextAdapter
from video_to_assets.adapters.video_adapter import VideoAdapter
from video_to_assets.canonical.canonical_content import CanonicalContent
from video_to_assets.models.source_input import SourceInput


class SourceRouter:
    def __init__(self, outputs_root: Path):
        self.outputs_root = outputs_root
        self._adapters: dict[str, BaseAdapter] = {
            "text": TextAdapter(),
            "file": FileAdapter(),
            "video": VideoAdapter(outputs_root=outputs_root),
        }

    def route(self, source: SourceInput) -> CanonicalContent:
        source.validate()
        adapter = self._adapters.get(source.input_type)
        if not adapter:
            raise ValueError(f"No adapter for input_type: {source.input_type}")
        return adapter.to_canonical(source)
