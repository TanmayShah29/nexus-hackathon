"""
youtube_mcp.py — YouTube Transcript MCP (youtube-transcript-api)
"""

import os
from typing import Any, Optional


DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"


YOUTUBE_FIXTURE = {
    "python_tutorial": {
        "video_id": "python_tutorial",
        "title": "Python Tutorial for Beginners",
        "transcript": "Welcome to this Python tutorial. In this video, we'll cover the basics of Python programming...",
    }
}


class YouTubeMCP:
    """
    YouTube transcript extraction using youtube-transcript-api.
    """

    def __init__(self, demo_mode: bool = DEMO_MODE):
        self.demo_mode = demo_mode or DEMO_MODE

    async def get_transcript(self, video_id: str) -> dict[str, Any]:
        """
        Get transcript for a YouTube video.
        Returns {video_id, title, transcript}.
        """
        if self.demo_mode:
            return self._fixture_transcript(video_id)

        return await self._fetch_transcript(video_id)

    def _fixture_transcript(self, video_id: str) -> dict[str, Any]:
        """Return fixture data."""
        for key, data in YOUTUBE_FIXTURE.items():
            if key in video_id:
                result = data.copy()
                result["video_id"] = video_id
                return result
        return {
            "video_id": video_id,
            "title": f"Video {video_id}",
            "transcript": f"Fixture transcript for video {video_id}. In demo mode, YouTube transcripts are mocked.",
        }

    async def _fetch_transcript(self, video_id: str) -> dict[str, Any]:
        """Fetch transcript using youtube-transcript-api."""
        try:
            from youtube_transcript_api import YouTubeTranscriptApi

            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            transcript = transcript_list.find_transcript(["en"])
            data = transcript.fetch()

            text = " ".join([t["text"] for t in data])

            return {
                "video_id": video_id,
                "title": f"Video {video_id}",
                "transcript": text,
            }
        except Exception:
            return self._fixture_transcript(video_id)
