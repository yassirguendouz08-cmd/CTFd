"""Event advertising requires an explicit opt-in and a complete real schedule."""
import json
from unittest.mock import patch

import unittest

from CTFd.plugins.cyberdune_presentation import presentation


def render_state(settings, start=1000, end=2000, now=1500, name="Configured CTF"):
    values = {"theme_settings": settings, "start": start, "end": end, "ctf_name": name}
    with patch("CTFd.plugins.cyberdune_presentation.get_config", side_effect=values.get), patch("CTFd.plugins.cyberdune_presentation.time.time", return_value=now):
        return presentation()


class PresentationTests(unittest.TestCase):
    def test_dates_never_enable_event(self):
        for settings in [None, "{}", "null", "[]", "broken", '{"cyberdune_mode":"platform"}', '{"cyberdune_mode":true}']:
            with self.subTest(settings=settings):
                self.assertEqual(render_state(settings), {"mode": "platform", "status": "Under Development"})

    def test_invalid_schedule_fails_closed(self):
        for start, end in [(None, 2000), (1000, None), (0, 2000), (2000, 1000), (1000, 1000), ("bad", 2000), (1000, 10**30)]:
            with self.subTest(start=start, end=end):
                self.assertEqual(render_state('{"cyberdune_mode":"event"}', start=start, end=end)["mode"], "platform")

    def test_real_event_status_boundaries(self):
        for now, status in [(999, "Starts soon"), (1000, "Event live"), (1999, "Event live"), (2000, "Event ended")]:
            with self.subTest(now=now):
                result = render_state(json.dumps({"cyberdune_mode": "event", "cyberdune_event_briefing": "Real briefing"}), now=now)
                self.assertEqual(result["mode"], "event")
                self.assertEqual(result["status"], status)
                self.assertEqual(result["name"], "Configured CTF")
                self.assertEqual(result["briefing"], "Real briefing")
                self.assertTrue(result["start_date"].endswith("+00:00"))

    def test_missing_name_fails_closed(self):
        self.assertEqual(render_state('{"cyberdune_mode":"event"}', name=" ")["mode"], "platform")
