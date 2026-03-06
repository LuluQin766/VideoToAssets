from video_to_assets.models.transcript import Transcript, TranscriptSegment
from video_to_assets.preprocess.transcript_builder import merge_adjacent_segments


def test_merge_adjacent_segments():
    transcript = Transcript(
        segments=[
            TranscriptSegment(0.0, 1.0, "hello"),
            TranscriptSegment(1.1, 2.0, "world"),
            TranscriptSegment(4.0, 5.0, "next."),
        ],
        source="sub",
    )
    merged = merge_adjacent_segments(transcript, gap_threshold=0.3)
    assert len(merged.segments) == 2
    assert merged.segments[0].text == "hello world"
