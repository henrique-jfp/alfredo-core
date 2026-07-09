"""
Testes para o fix do bug de mute/unmute em SamsungTVManager.
Garante que set_mute() usa comando ABSOLUTO via SmartThings, e não
mais o KEY_MUTE (toggle) quando SmartThings está configurado.
"""
import sys
import os
import unittest
from unittest.mock import patch, MagicMock

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.services.samsung_tv import SamsungTVManager


class TestSamsungTVMute(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.tv = SamsungTVManager(
            ip="192.168.0.10",
            mac="AA:BB:CC:DD:EE:FF",
            smartthings_pat="fake-pat",
            smartthings_device_id="fake-device-id"
        )

    @patch("core.services.samsung_tv.requests.post")
    async def test_set_mute_true_sends_absolute_mute_command(self, mock_post):
        mock_post.return_value = MagicMock(status_code=200)

        result = await self.tv.set_mute(True)

        self.assertTrue(result)
        sent_payload = mock_post.call_args.kwargs["json"]
        command = sent_payload["commands"][0]["command"]
        self.assertEqual(command, "mute")
        self.assertEqual(sent_payload["commands"][0]["capability"], "audioMute")

    @patch("core.services.samsung_tv.requests.post")
    async def test_set_mute_false_sends_absolute_unmute_command(self, mock_post):
        mock_post.return_value = MagicMock(status_code=200)

        result = await self.tv.set_mute(False)

        self.assertTrue(result)
        sent_payload = mock_post.call_args.kwargs["json"]
        command = sent_payload["commands"][0]["command"]
        self.assertEqual(command, "unmute")

    @patch("core.services.samsung_tv.requests.post")
    async def test_set_mute_never_uses_toggle_key_when_smartthings_ok(self, mock_post):
        """Regressão do bug original: antes, QUALQUER chamada a set_mute
        enviava KEY_MUTE via rede local, independente do valor de `mute`."""
        mock_post.return_value = MagicMock(status_code=200)

        with patch.object(self.tv, "_run_local_command") as mock_local:
            await self.tv.set_mute(True)
            await self.tv.set_mute(False)
            mock_local.assert_not_called()

    async def test_set_mute_falls_back_to_toggle_without_smartthings(self):
        tv_no_st = SamsungTVManager(ip="192.168.0.10")  # sem PAT/device_id
        with patch.object(tv_no_st, "_run_local_command", return_value=True) as mock_local:
            result = await tv_no_st.set_mute(True)
            mock_local.assert_called_once_with(tv_no_st.tv.send_key, "KEY_MUTE")
            self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()