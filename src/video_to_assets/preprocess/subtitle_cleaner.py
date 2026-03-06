from __future__ import annotations

import html
import re

from video_to_assets.models.transcript import Transcript, TranscriptSegment


HTML_RE = re.compile(r"<[^>]+>")
NOISE_RE = re.compile(r"\[(music|applause|noise|laughter)\]", re.IGNORECASE)
SPACE_RE = re.compile(r"\s+")


def clean_transcript(transcript: Transcript) -> Transcript:
    cleaned: list[TranscriptSegment] = []
    previous = None

    for seg in transcript.segments:
        text = seg.text
        text = html.unescape(text)
        text = HTML_RE.sub("", text)
        text = NOISE_RE.sub("", text)
        text = SPACE_RE.sub(" ", text).strip()
        if not text:
            continue
        if previous and previous.lower() == text.lower():
            continue

        cleaned.append(
            TranscriptSegment(
                start=seg.start,
                end=seg.end,
                text=text,
                source=seg.source,
            )
        )
        previous = text

    return Transcript(segments=cleaned, source=transcript.source)
