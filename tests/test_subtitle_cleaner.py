from video_to_assets.models.transcript import Transcript, TranscriptSegment
from video_to_assets.preprocess.subtitle_cleaner import clean_transcript


def test_clean_transcript_removes_html_and_duplicates():
    transcript = Transcript(
        segments=[
            TranscriptSegment(0, 1, "<i>Hello</i>"),
            TranscriptSegment(1, 2, "Hello"),
            TranscriptSegment(2, 3, "[music] world"),
        ],
        source="sub",
    )
    cleaned = clean_transcript(transcript)
    assert len(cleaned.segments) == 2
    assert cleaned.segments[0].text == "Hello"
    assert cleaned.segments[1].text == "world"
