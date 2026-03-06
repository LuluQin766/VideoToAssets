from __future__ import annotations

import hashlib
from pathlib import Path

from video_to_assets.adapters.base_adapter import BaseAdapter
from video_to_assets.canonical.canonical_content import CanonicalContent
from video_to_assets.canonical.normalizer import build_canonical
from video_to_assets.canonical.metadata_merger import merge_metadata
from video_to_assets.models.source_input import SourceInput
from video_to_assets.parsers.text_parsers import parse_json, parse_md, parse_srt, parse_txt, parse_vtt


class FileAdapter(BaseAdapter):
    def to_canonical(self, source: SourceInput) -> CanonicalContent:
        source.validate()
        if not source.file_path:
            raise ValueError("file input missing file_path")
        path = Path(source.file_path)
        if not path.exists():
            raise FileNotFoundError(str(path))

        raw_text, timestamps, metadata = self._parse_file(path)

        source_id = self._derive_id(path)
        merged_meta = merge_metadata(metadata, {
            "source_name": source.source_name,
            "source_url": source.source_url,
            "author": source.author,
            "publish_date": source.publish_date,
            "platform": source.platform,
            "input_type": source.input_type,
            "file_path": str(path),
            "file_ext": path.suffix.lower(),
        })
        attribution = {
            "source_type": "file",
            "source_note": "local file provided by user",
        }
        return build_canonical(
            source_id=source_id,
            source_type="file",
            title=source.title or path.stem,
            raw_text=raw_text,
            timestamps=timestamps,
            language=None,
            source_metadata=merged_meta,
            attribution=attribution,
        )

    def _parse_file(self, path: Path) -> tuple[str, list, dict]:
        ext = path.suffix.lower()
        if ext == ".txt":
            text, timestamps = parse_txt(path)
            return text, timestamps, {}
        if ext == ".md":
            text, timestamps = parse_md(path)
            return text, timestamps, {}
        if ext == ".srt":
            text, timestamps = parse_srt(path)
            return text, timestamps, {}
        if ext == ".vtt":
            text, timestamps = parse_vtt(path)
            return text, timestamps, {}
        if ext == ".json":
            text, timestamps, meta = parse_json(path)
            return text, timestamps, meta
        raise ValueError(f"Unsupported file extension: {ext}")

    def _derive_id(self, path: Path) -> str:
        digest = hashlib.sha1(str(path).encode("utf-8")).hexdigest()[:12]
        return f"file_{digest}"
