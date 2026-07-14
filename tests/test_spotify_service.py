"""
Testes para o Spotify Service unificado.
"""
import sys
import os
import unittest
from unittest.mock import MagicMock, patch

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.services.spotify_service import (
    get_best_device, search_and_play, control_playback,
    _creds_hash
)
from core.brain.skills.music_skill import MusicSkill


class TestGetBestDevice(unittest.TestCase):

    def test_prefers_alfredo_speaker(self):
        sp = MagicMock()
        sp.devices.return_value = {
            "devices": [
                {"id": "abc", "name": "Celular", "is_active": True},
                {"id": "def", "name": "Alfredo Speaker", "is_active": False},
            ]
        }
        self.assertEqual(get_best_device(sp), "def")

    def test_falls_back_to_active_device(self):
        sp = MagicMock()
        sp.devices.return_value = {
            "devices": [
                {"id": "abc", "name": "Celular", "is_active": True},
                {"id": "ghi", "name": "Notebook", "is_active": False},
            ]
        }
        self.assertEqual(get_best_device(sp), "abc")

    def test_returns_first_if_no_active(self):
        sp = MagicMock()
        sp.devices.return_value = {
            "devices": [
                {"id": "xyz", "name": "Web Player", "is_active": False},
            ]
        }
        self.assertEqual(get_best_device(sp), "xyz")

    def test_returns_none_if_no_devices(self):
        sp = MagicMock()
        sp.devices.return_value = {"devices": []}
        self.assertIsNone(get_best_device(sp))

    def test_returns_none_if_devices_key_missing(self):
        sp = MagicMock()
        sp.devices.return_value = {}
        self.assertIsNone(get_best_device(sp))


class TestSearchAndPlay(unittest.TestCase):

    def test_plays_track_when_found(self):
        sp = MagicMock()
        sp.search.return_value = {
            "tracks": {"items": [{"name": "Test Song", "artists": [{"name": "Test Artist"}], "album": {"uri": "spotify:album:1"}, "uri": "spotify:track:1"}]},
            "artists": {"items": []},
            "playlists": {"items": []},
        }
        result = search_and_play(sp, "test song", "device1")
        self.assertEqual(result["type"], "track")
        self.assertEqual(result["name"], "Test Song")
        sp.start_playback.assert_called_once()

    def test_plays_artist_when_no_tracks(self):
        sp = MagicMock()
        sp.search.return_value = {
            "tracks": {"items": []},
            "artists": {"items": [{"name": "Test Artist", "uri": "spotify:artist:1"}]},
            "playlists": {"items": []},
        }
        result = search_and_play(sp, "test artist", "device1")
        self.assertEqual(result["type"], "artist")
        self.assertEqual(result["name"], "Test Artist")

    def test_plays_playlist_when_no_tracks(self):
        sp = MagicMock()
        sp.search.return_value = {
            "tracks": {"items": []},
            "artists": {"items": []},
            "playlists": {"items": [{"name": "Test Playlist", "uri": "spotify:playlist:1"}]},
        }
        result = search_and_play(sp, "test playlist", "device1")
        self.assertEqual(result["type"], "playlist")
        self.assertEqual(result["name"], "Test Playlist")

    def test_returns_none_when_no_results(self):
        sp = MagicMock()
        sp.search.return_value = {
            "tracks": {"items": []},
            "artists": {"items": []},
            "playlists": {"items": []},
        }
        result = search_and_play(sp, "nothing", "device1")
        self.assertIsNone(result)

    def test_fallback_to_uris_when_album_context_fails(self):
        sp = MagicMock()
        sp.search.return_value = {
            "tracks": {"items": [{"name": "Test", "artists": [{"name": "Artist"}], "album": {"uri": "spotify:album:1"}, "uri": "spotify:track:1"}]},
            "artists": {"items": []},
            "playlists": {"items": []},
        }
        sp.start_playback.side_effect = [Exception("album fail"), None]
        result = search_and_play(sp, "test", "device1")
        self.assertEqual(result["type"], "track")


class TestControlPlayback(unittest.TestCase):

    def setUp(self):
        self.sp = MagicMock()

    def test_pause(self):
        control_playback(self.sp, "pause", "dev1")
        self.sp.pause_playback.assert_called_once_with(device_id="dev1")

    def test_resume(self):
        control_playback(self.sp, "resume", "dev1")
        self.sp.start_playback.assert_called_once_with(device_id="dev1")

    def test_next(self):
        control_playback(self.sp, "next", "dev1")
        self.sp.next_track.assert_called_once_with(device_id="dev1")

    def test_previous(self):
        control_playback(self.sp, "previous", "dev1")
        self.sp.previous_track.assert_called_once_with(device_id="dev1")

    def test_volume_clamps(self):
        control_playback(self.sp, "volume", "dev1", volume=150)
        self.sp.volume.assert_called_once_with(100, device_id="dev1")

    def test_volume_minimum(self):
        control_playback(self.sp, "volume", "dev1", volume=-10)
        self.sp.volume.assert_called_once_with(0, device_id="dev1")

    def test_without_device_id(self):
        control_playback(self.sp, "pause")
        self.sp.pause_playback.assert_called_once_with()


class TestMusicSkillCleanSearchTerm(unittest.TestCase):

    def setUp(self):
        self.skill = MusicSkill()

    def test_removes_command_verbs(self):
        self.assertEqual(self.skill._clean_search_term("toca the beatles"), "the beatles")

    def test_removes_wake_word(self):
        self.assertEqual(self.skill._clean_search_term("alfredo toca queen"), "queen")

    def test_removes_filler_prefixes(self):
        self.assertEqual(self.skill._clean_search_term("busca no spotify a música radiohead"), "radiohead")

    def test_preserves_articles_in_search(self):
        self.assertEqual(self.skill._clean_search_term("toca Água de Beber"), "água de beber")

    def test_handles_empty_result(self):
        self.assertEqual(self.skill._clean_search_term("toca"), "")

    def test_preserves_english_articles(self):
        self.assertEqual(self.skill._clean_search_term("toca The Beatles"), "the beatles")


class TestCredsHash(unittest.TestCase):

    def test_same_creds_same_hash(self):
        self.assertEqual(_creds_hash("a", "b"), _creds_hash("a", "b"))

    def test_different_creds_different_hash(self):
        self.assertNotEqual(_creds_hash("a", "b"), _creds_hash("a", "c"))


if __name__ == "__main__":
    unittest.main()
