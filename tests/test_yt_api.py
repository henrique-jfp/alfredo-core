"""Testes para o serviço do YouTube (youtube_service)"""
from unittest.mock import patch, MagicMock
import pytest

from core.services import youtube_service


@pytest.fixture(autouse=True)
def mock_ytdlp():
    with patch("core.services.youtube_service.yt_dlp.YoutubeDL") as mock:
        mock_ctx = MagicMock()
        mock.return_value = mock_ctx
        mock_ctx.__enter__.return_value = mock_ctx
        mock_ctx.extract_info.return_value = {
            "entries": [{"title": "Test Video", "url": "http://example.com/audio"}],
            "title": "Test Video",
            "url": "http://example.com/audio",
        }
        yield mock


@pytest.fixture(autouse=True)
def mock_requests():
    with patch("core.services.youtube_service.requests.post") as mock:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {}
        mock_resp.raise_for_status.return_value = None
        mock.return_value = mock_resp
        yield mock


class TestSearchAudio:
    def test_search_audio_returns_title_and_url(self, mock_ytdlp):
        result = youtube_service.search_audio("test query", is_live=False)

        assert result is not None
        assert result["title"] == "Test Video"
        assert result["url"] == "http://example.com/audio"
        mock_ytdlp.return_value.extract_info.assert_called_once_with(
            "ytsearch1:test query", download=False
        )

    def test_search_audio_no_entries(self, mock_ytdlp):
        mock_ytdlp.return_value.extract_info.return_value = {"entries": []}

        result = youtube_service.search_audio("test query", is_live=False)
        assert result is None

    def test_search_audio_ytdlp_error(self, mock_ytdlp):
        mock_ytdlp.return_value.extract_info.side_effect = Exception("fail")

        result = youtube_service.search_audio("test query", is_live=False)
        assert result is None


class TestLiveSearch:
    def test_live_search_returns_url(self, mock_requests, mock_ytdlp):
        mock_requests.return_value.json.return_value = {
            "contents": {
                "twoColumnSearchResultsRenderer": {
                    "primaryContents": {
                        "sectionListRenderer": {
                            "contents": [
                                {
                                    "itemSectionRenderer": {
                                        "contents": [
                                            {
                                                "videoRenderer": {
                                                    "videoId": "abc123xyz",
                                                    "title": {
                                                        "runs": [{"text": "Live Now"}]
                                                    },
                                                    "ownerText": {
                                                        "runs": [{"text": "Channel Name"}]
                                                    }
                                                }
                                            }
                                        ]
                                    }
                                }
                            ]
                        }
                    }
                }
            }
        }

        mock_ytdlp.return_value.extract_info.return_value = {
            "title": "Live Now",
            "url": "http://live.url/audio",
        }

        result = youtube_service.search_audio("channel name", is_live=True)
        assert result is not None
        assert "abc123xyz" in mock_ytdlp.return_value.extract_info.call_args[0][0]

    def test_live_search_no_results(self, mock_requests, mock_ytdlp):
        mock_requests.return_value.json.return_value = {}

        mock_ytdlp.return_value.extract_info.return_value = {"entries": []}

        result = youtube_service.search_audio("nonexistent", is_live=True)
        assert result is None

    def test_live_search_fallback_on_fail(self, mock_requests, mock_ytdlp):
        """Live API falha, deve cair no fallback do yt-dlp"""
        mock_requests.side_effect = Exception("API error")

        mock_ytdlp.return_value.extract_info.return_value = {
            "entries": [{"title": "Fallback Video", "url": "http://fallback.url"}],
            "title": "Fallback Video",
            "url": "http://fallback.url",
        }

        result = youtube_service.search_audio("test", is_live=True)
        assert result is not None
        assert result["title"] == "Fallback Video"


class TestIsAmbiguousQuery:
    def test_ambiguous_short_query(self):
        assert youtube_service.is_ambiguous_query("ab") is True

    def test_ambiguous_common_phrases(self):
        assert youtube_service.is_ambiguous_query("youtube") is True
        assert youtube_service.is_ambiguous_query("musica") is True
        assert youtube_service.is_ambiguous_query("video do youtube") is True

    def test_clear_query(self):
        assert youtube_service.is_ambiguous_query("caze tv") is False
        assert youtube_service.is_ambiguous_query("flow podcast 2024") is False


class TestNormalize:
    def test_remove_accents(self):
        assert youtube_service._normalize("coração") == "coracao"

    def test_remove_spaces(self):
        assert youtube_service._normalize("flow podcast") == "flowpodcast"

    def test_empty(self):
        assert youtube_service._normalize("") == ""
        assert youtube_service._normalize(None) == ""
