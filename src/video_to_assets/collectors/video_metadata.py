from __future__ import annotations

import json
from pathlib import Path

import requests

from video_to_assets.collectors.yt_dlp_adapter import YtDlpAdapter
from video_to_assets.models.video_info import VideoInfo


class VideoMetadataCollector:
    def __init__(self, adapter: YtDlpAdapter, logger=None):
        self.adapter = adapter
        self.logger = logger

    def collect(self, url: str, metadata_dir: Path) -> VideoInfo:
        metadata_dir.mkdir(parents=True, exist_ok=True)
        info_raw = self.adapter.extract_metadata(url)
        info = VideoInfo.from_yt_dlp(info_raw)

        json_file = metadata_dir / "video_info.json"
        md_file = metadata_dir / "video_info.md"
        with json_file.open("w", encoding="utf-8") as f:
            json.dump(info.to_dict(), f, ensure_ascii=False, indent=2)
        md_file.write_text(info.to_markdown(), encoding="utf-8")

        self._try_download_thumbnail(info, metadata_dir / "thumbnail.jpg")
        return info

    def _try_download_thumbnail(self, info: VideoInfo, output_file: Path) -> None:
        if not info.thumbnail:
            return
        try:
            resp = requests.get(info.thumbnail, timeout=20)
            if resp.ok:
                output_file.write_bytes(resp.content)
        except Exception as exc:
            if self.logger:
                self.logger.warning("thumbnail download failed: %s", exc)
