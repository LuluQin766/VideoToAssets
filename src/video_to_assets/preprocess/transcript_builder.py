from __future__ import annotations

from video_to_assets.models.transcript import Transcript, TranscriptSegment


def merge_adjacent_segments(transcript: Transcript, gap_threshold: float = 0.45) -> Transcript:
    if not transcript.segments:
        return transcript

    merged: list[TranscriptSegment] = []
    current = transcript.segments[0]

    for seg in transcript.segments[1:]:
        short_gap = seg.start - current.end <= gap_threshold
        no_punct_end = current.text and current.text[-1] not in ".!?。！？"
        if short_gap and no_punct_end:
            current = TranscriptSegment(
                start=current.start,
                end=seg.end,
                text=f"{current.text} {seg.text}".strip(),
                source=current.source,
            )
        else:
            merged.append(current)
            current = seg
    merged.append(current)

    return Transcript(segments=merged, source=transcript.source)
