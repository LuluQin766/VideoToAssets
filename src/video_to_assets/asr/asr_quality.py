from __future__ import annotations

from video_to_assets.models.transcript import Transcript


def basic_asr_quality(transcript: Transcript) -> dict:
    text = transcript.plain_text()
    seg_count = len(transcript.segments)
    return {
        "segment_count": seg_count,
        "char_count": len(text),
        "is_usable": seg_count >= 3 and len(text) >= 60,
    }
