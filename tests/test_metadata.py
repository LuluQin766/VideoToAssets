from video_to_assets.models.video_info import VideoInfo


def test_video_info_from_yt_dlp():
    payload = {
        "id": "vid123",
        "title": "Demo",
        "uploader": "Uploader",
        "upload_date": "20260101",
        "duration": 123,
        "webpage_url": "https://x",
        "subtitles": {"en": [{"ext": "vtt"}]},
    }
    info = VideoInfo.from_yt_dlp(payload)
    assert info.video_id == "vid123"
    assert info.title == "Demo"
    assert "en" in info.subtitles
