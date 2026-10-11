"""Regression tests for the targeted three-venue publisher.

No network access: source validation and publication use an isolated feed.
"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from audit import publish_bibelot_pul as publisher


def item(source, index, first_found=1234):
    return dict(
        source=source, artist=f"Band {index}", venue=source, city="Teststad",
        country="NL", date="2099-01-01", time="20:00",
        url=f"https://events.example.org/{source.replace(' ', '-')}/{index}",
        firstFound=first_found,
    )


class TargetedPublisherTests(unittest.TestCase):
    def test_existing_first_found_is_preserved_and_unrelated_shows_survive(self):
        with tempfile.TemporaryDirectory() as temp:
            feed = Path(temp) / "concerts.json"
            cache = Path(temp) / "verified.json"
            previous = [item("Andere zaal", k) for k in range(1000)]
            previous += [item(name, k, 111) for name, minimum in publisher.SOURCES.items()
                         for k in range(minimum)]
            fresh = [item(name, k, 999999) for name, minimum in publisher.SOURCES.items()
                     for k in range(minimum)]
            feed.write_text(json.dumps(previous), encoding="utf-8")
            cache.write_text(json.dumps(fresh), encoding="utf-8")
            with patch.object(publisher, "FEED", feed), patch.object(publisher, "CACHE", cache):
                publisher.apply()
            result = json.loads(feed.read_text(encoding="utf-8"))
            self.assertEqual(len(result), len(previous))
            by_url = {x["url"]: x for x in result}
            for old in previous:
                self.assertIn(old["url"], by_url)
                self.assertEqual(by_url[old["url"]]["firstFound"], old["firstFound"])

    def test_empty_source_is_blocked(self):
        with self.assertRaises(RuntimeError):
            publisher.validate([], "De Pul", 25)


if __name__ == "__main__":
    unittest.main()
