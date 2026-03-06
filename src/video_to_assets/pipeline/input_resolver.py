from __future__ import annotations

from pathlib import Path

from video_to_assets.models.source_input import SourceInput


def resolve_source_input(
    *,
    input_type: str | None,
    url: str | None = None,
    text: str | None = None,
    text_file: str | None = None,
    file: str | None = None,
    title: str | None = None,
    source_name: str | None = None,
    source_url: str | None = None,
    author: str | None = None,
    publish_date: str | None = None,
    platform: str | None = None,
) -> SourceInput:
    inferred = input_type
    if inferred is None:
        if url:
            inferred = "video"
        else:
            raise ValueError("input_type is required when no --url is provided")

    if inferred not in {"video", "text", "file"}:
        raise ValueError(f"Unsupported input_type: {inferred}")

    if inferred == "video":
        if not url:
            raise ValueError("video input requires --url")
        if text or text_file or file:
            raise ValueError("video input cannot be combined with --text/--text-file/--file")
        return SourceInput(
            input_type="video",
            url=url,
            title=title,
            source_name=source_name,
            source_url=source_url,
            author=author,
            publish_date=publish_date,
            platform=platform,
        )

    if inferred == "text":
        if file:
            raise ValueError("text input cannot use --file")
        if text and text_file:
            raise ValueError("text input accepts either --text or --text-file (not both)")
        if not text and not text_file:
            raise ValueError("text input requires --text or --text-file")
        file_path = Path(text_file) if text_file else None
        return SourceInput(
            input_type="text",
            text=text,
            file_path=file_path,
            title=title,
            source_name=source_name,
            source_url=source_url,
            author=author,
            publish_date=publish_date,
            platform=platform,
        )

    if inferred == "file":
        if text or text_file:
            raise ValueError("file input cannot use --text/--text-file")
        if not file:
            raise ValueError("file input requires --file")
        return SourceInput(
            input_type="file",
            file_path=Path(file),
            title=title,
            source_name=source_name,
            source_url=source_url,
            author=author,
            publish_date=publish_date,
            platform=platform,
        )

    raise ValueError(f"Unsupported input_type: {inferred}")
