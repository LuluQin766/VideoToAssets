from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from video_to_assets.models.video_info import VideoInfo
from video_to_assets.storage.path_manager import OutputPaths


@dataclass
class PipelineState:
    url: str
    video_id: str
    paths: OutputPaths
    input_type: str = "video"
    source_type: str = "video"
    source_id: str | None = None
    source_metadata_complete: bool = True
    tasks: set[str] = field(default_factory=set)
    metadata: VideoInfo | None = None
    subtitle_source: str = "none"
    subtitle_file: Path | None = None
    asr_triggered: bool = False
    asr_placeholder: bool = False
    outputs: dict[str, str] = field(default_factory=dict)
