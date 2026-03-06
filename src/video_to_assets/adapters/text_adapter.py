from __future__ import annotations

import hashlib
from pathlib import Path

from video_to_assets.adapters.base_adapter import BaseAdapter
from video_to_assets.canonical.canonical_content import CanonicalContent
from video_to_assets.canonical.normalizer import build_canonical
from video_to_assets.canonical.metadata_merger import merge_metadata
from video_to_assets.models.source_input import SourceInput
from video_to_assets.parsers.text_parsers import parse_txt


class TextAdapter(BaseAdapter):
    def to_canonical(self, source: SourceInput) -> CanonicalContent:
        source.validate()
        text = source.text
        if not text and source.file_path:
            text, _ = parse_txt(Path(source.file_path))
        if not text:
            raise ValueError("text input is empty")

        source_id = self._derive_id(text)
        metadata = merge_metadata(source.metadata or {}, {
            "source_name": source.source_name,
            "source_url": source.source_url,
            "author": source.author,
            "publish_date": source.publish_date,
            "platform": source.platform,
            "input_type": source.input_type,
        })
        attribution = {
            "source_type": "text",
            "source_note": "user-provided text / source metadata incomplete",
        }
        return build_canonical(
            source_id=source_id,
            source_type="text",
            title=source.title or "User Text",
            raw_text=text,
            language=None,
            source_metadata=metadata,
            attribution=attribution,
        )

    def _derive_id(self, text: str) -> str:
        digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]
        return f"text_{digest}"
