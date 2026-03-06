from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs, urlparse


VIDEO_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{6,20}$")


@dataclass
class OutputPaths:
    root: Path
    source: Path
    normalized: Path
    metadata: Path
    subtitles_raw: Path
    asr: Path
    subtitles_clean: Path
    text_exports: Path
    llm_review: Path
    summaries: Path
    articles_wechat: Path
    articles_xiaohongshu: Path
    highlights: Path
    source_attribution: Path
    logs: Path
    readme: Path


class PathManager:
    def __init__(self, output_root: Path):
        self.output_root = output_root

    def infer_video_id(self, url: str) -> str:
        parsed = urlparse(url)
        if parsed.hostname and "youtube" in parsed.hostname:
            qs = parse_qs(parsed.query)
            if "v" in qs and qs["v"]:
                candidate = qs["v"][0]
                if VIDEO_ID_PATTERN.match(candidate):
                    return candidate
            parts = [p for p in parsed.path.split("/") if p]
            if parts:
                tail = parts[-1]
                if VIDEO_ID_PATTERN.match(tail):
                    return tail
        if parsed.hostname and "youtu.be" in parsed.hostname:
            parts = [p for p in parsed.path.split("/") if p]
            if parts and VIDEO_ID_PATTERN.match(parts[0]):
                return parts[0]

        digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]
        return f"video_{digest}"

    def build(self, video_id: str) -> OutputPaths:
        root = self.output_root / video_id
        return OutputPaths(
            root=root,
            source=root / "source",
            normalized=root / "normalized",
            metadata=root / "metadata",
            subtitles_raw=root / "subtitles_raw",
            asr=root / "asr",
            subtitles_clean=root / "subtitles_clean",
            text_exports=root / "text_exports",
            llm_review=root / "llm_review",
            summaries=root / "summaries",
            articles_wechat=root / "articles_wechat",
            articles_xiaohongshu=root / "articles_xiaohongshu",
            highlights=root / "highlights",
            source_attribution=root / "source_attribution",
            logs=root / "logs",
            readme=root / "README.md",
        )

    def ensure(self, video_id: str) -> OutputPaths:
        return self.ensure_source(video_id, include_video_dirs=True)

    def ensure_source(self, source_id: str, include_video_dirs: bool = False) -> OutputPaths:
        paths = self.build(source_id)
        base_dirs = [
            paths.root,
            paths.source,
            paths.normalized,
            paths.llm_review,
            paths.summaries,
            paths.articles_wechat,
            paths.articles_xiaohongshu,
            paths.highlights,
            paths.source_attribution,
            paths.logs,
        ]
        for p in base_dirs:
            p.mkdir(parents=True, exist_ok=True)
        if include_video_dirs:
            for p in [
                paths.metadata,
                paths.subtitles_raw,
                paths.asr,
                paths.subtitles_clean,
                paths.text_exports,
            ]:
                p.mkdir(parents=True, exist_ok=True)
        return paths
