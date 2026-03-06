from __future__ import annotations

from pathlib import Path

from video_to_assets.collectors.yt_dlp_adapter import YtDlpAdapter


class AudioFetcher:
    def __init__(self, adapter: YtDlpAdapter):
        self.adapter = adapter

    def fetch_audio(self, url: str, asr_dir: Path) -> Path:
        return self.adapter.download_audio(url, asr_dir)
