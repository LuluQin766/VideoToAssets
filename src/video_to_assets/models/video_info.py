from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class VideoInfo:
    video_id: str
    title: str
    uploader: str | None = None
    channel: str | None = None
    upload_date: str | None = None
    duration: int | None = None
    webpage_url: str | None = None
    description: str | None = None
    thumbnail: str | None = None
    view_count: int | None = None
    like_count: int | None = None
    tags: list[str] = field(default_factory=list)
    subtitles: dict[str, Any] = field(default_factory=dict)
    automatic_captions: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_yt_dlp(cls, data: dict[str, Any]) -> "VideoInfo":
        return cls(
            video_id=str(data.get("id") or "unknown_video"),
            title=str(data.get("title") or "Untitled"),
            uploader=data.get("uploader") or data.get("channel") or None,
            channel=data.get("channel") or None,
            upload_date=data.get("upload_date") or data.get("release_date") or None,
            duration=data.get("duration"),
            webpage_url=data.get("webpage_url") or data.get("original_url"),
            description=data.get("description"),
            thumbnail=data.get("thumbnail"),
            view_count=data.get("view_count"),
            like_count=data.get("like_count"),
            tags=[str(t) for t in (data.get("tags") or [])],
            subtitles=data.get("subtitles") or {},
            automatic_captions=data.get("automatic_captions") or {},
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["generated_at"] = datetime.utcnow().isoformat() + "Z"
        return payload

    def to_markdown(self) -> str:
        return "\n".join(
            [
                f"# {self.title}",
                "",
                f"- video_id: `{self.video_id}`",
                f"- uploader/channel: {self.uploader or self.channel or 'N/A'}",
                f"- upload_date: {self.upload_date or 'N/A'}",
                f"- duration_seconds: {self.duration if self.duration is not None else 'N/A'}",
                f"- url: {self.webpage_url or 'N/A'}",
                f"- view_count: {self.view_count if self.view_count is not None else 'N/A'}",
                f"- like_count: {self.like_count if self.like_count is not None else 'N/A'}",
                f"- tags_count: {len(self.tags)}",
                f"- subtitles_languages: {', '.join(sorted(self.subtitles.keys())) or 'none'}",
                f"- auto_captions_languages: {', '.join(sorted(self.automatic_captions.keys())) or 'none'}",
                "",
                "## Description",
                "",
                self.description or "",
            ]
        )
