"""Regression checks for the incremental concert publisher.

These tests never access the network or overwrite concerts.json.
"""
import unittest
from datetime import date, timedelta
from audit.publish_bibelot_pul import validate


def row(url, source="Bibelot"):
    return {
        "source": source,
        "url": url,
        "artist": "Example Artist",
        "date": (date.today() + timedelta(days=5)).isoformat(),
        "venue": source,
    }


class TargetedPublicationSafetyTests(unittest.TestCase):
    def test_valid_future_event(self):
        validate([row("https://example.org/show-1")], "Bibelot", 1)

    def test_reject_missing_url(self):
        with self.assertRaises(RuntimeError):
            validate([row("")], "Bibelot", 1)

    def test_reject_missing_artist(self):
        event = row("https://example.org/show-1")
        event["artist"] = ""
        with self.assertRaises(RuntimeError):
            validate([event], "Bibelot", 1)

    def test_reject_duplicate_urls(self):
        events = [row("https://example.org/show-1"),
                  row("https://example.org/show-1")]
        with self.assertRaises(RuntimeError):
            validate(events, "Bibelot", 1)

    def test_reject_wrong_source(self):
        with self.assertRaises(RuntimeError):
            validate([row("https://example.org/show-1", "Another")], "Bibelot", 1)

    def test_reject_incomplete_feed(self):
        with self.assertRaises(RuntimeError):
            validate([row("https://example.org/show-1")], "Bibelot", 2)


if __name__ == "__main__":
    unittest.main()
