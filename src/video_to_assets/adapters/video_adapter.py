from __future__ import annotations

from pathlib import Path

from video_to_assets.adapters.base_adapter import BaseAdapter
from video_to_assets.canonical.canonical_content import CanonicalContent
from video_to_assets.canonical.normalizer import build_canonical
from video_to_assets.models.source_input import SourceInput
from video_to_assets.models.video_info import VideoInfo


class VideoAdapter(BaseAdapter):
    """Adapter stub: builds canonical content from existing video outputs.

    This does not alter the current video pipeline. It only reads outputs if present.
    """

    def __init__(self, outputs_root: Path):
        self.outputs_root = outputs_root

    def to_canonical(self, source: SourceInput) -> CanonicalContent:
        source.validate()
        if not source.url:
            raise ValueError("video input requires url")

        video_id = source.metadata.get("video_id") if source.metadata else None
        if not video_id:
            raise ValueError("video_id required in source.metadata for video adapter")

        base_dir = self.outputs_root / video_id
        cleaned_plain = base_dir / "subtitles_clean" / "cleaned_plain.txt"
        raw_text = cleaned_plain.read_text(encoding="utf-8", errors="ignore") if cleaned_plain.exists() else ""

        title = source.title or "Video Content"
        metadata = source.metadata or {}
        attribution = {
            "source_type": "video",
            "source_note": "derived from existing video pipeline outputs",
        }
        return build_canonical(
            source_id=video_id,
            source_type="video",
            title=title,
            raw_text=raw_text,
            language=None,
            source_metadata=metadata,
            attribution=attribution,
        )
