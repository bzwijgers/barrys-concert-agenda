"""Regression: transient Metropool HTTP 500 must not wipe verified shows."""
import unittest
from datetime import date, timedelta
from unittest.mock import patch

from scrapers.new_venues import scrape_venue, previous_published_venue_events
from scrapers.common import normalize_url


class MetropoolRecoveryTests(unittest.TestCase):
    def test_previous_feed_only_recovers_exact_future_metropool_links(self):
        import json
        from tempfile import NamedTemporaryFile
        from pathlib import Path

        good_date = (date.today() + timedelta(days=28)).isoformat()
        past_date = (date.today() - timedelta(days=2)).isoformat()
        entries = [
            {"artist": "Future band", "venue": "Metropool Hengelo", "city": "Hengelo",
             "country": "NL", "date": good_date, "time": "", "source": "Metropool",
             "url": "https://metropool.nl/agenda/future"},
            {"artist": "Past band", "venue": "Metropool Hengelo", "city": "Hengelo",
             "country": "NL", "date": past_date, "time": "", "source": "Metropool",
             "url": "https://metropool.nl/agenda/past"},
            {"artist": "Other venue", "venue": "Hedon", "city": "Zwolle",
             "country": "NL", "date": good_date, "time": "", "source": "Hedon",
             "url": "https://metropool.nl/agenda/other"},
        ]
        with NamedTemporaryFile(mode="w", suffix=".json", encoding="utf-8") as handle:
            json.dump(entries, handle)
            handle.flush()
            saved = previous_published_venue_events("Metropool", path=handle.name)
        self.assertEqual(list(saved), [normalize_url(entries[0]["url"])])

    @patch("scrapers.new_venues.previous_published_venue_events")
    @patch("scrapers.new_venues.parse_event")
    @patch("scrapers.new_venues.download_page_retry")
    def test_http_500_recovers_saved_events_by_exact_url(self, download, parse, previous):
        urls = ["https://metropool.nl/agenda/show-" + str(i) for i in range(4)]
        good_date = (date.today() + timedelta(days=28)).isoformat()
        entries = {
            normalize_url(url): {
                "artist": "Artist " + str(i), "venue": "Metropool Hengelo",
                "city": "Hengelo", "country": "NL", "date": good_date, "time": "20:00",
                "source": "Metropool", "url": url
            } for i, url in enumerate(urls[:3])
        }
        previous.return_value = entries

        def get(url, attempts=2):
            if url.endswith("/agenda") or "pNumber=2" in url:
                return "".join(f'<a href="/agenda/show-{i}">Show</a>' for i in range(4))
            if url in urls[:3]:
                raise RuntimeError("HTTP Error 500")
            return "<html>valid</html>"

        download.side_effect = get
        parse.side_effect = lambda html, url, name, city: {
            "artist": "Fresh", "venue": "Metropool Hengelo", "city": city,
            "country": "NL", "date": good_date, "time": "20:00",
            "source": name, "url": url,
        }
        concerts = scrape_venue("Metropool")
        self.assertEqual(len(concerts), 4)
        self.assertEqual({c["url"] for c in concerts}, set(urls))
        self.assertEqual(len([c for c in concerts if c["artist"] == "Fresh"]), 1)

    @patch("scrapers.new_venues.previous_published_venue_events", return_value={})
    @patch("scrapers.new_venues.download_page_retry")
    def test_missing_verified_fallback_still_rejects_many_failures(self, download, _previous):
        def get(url, attempts=2):
            if url.endswith("/agenda") or "pNumber=2" in url:
                return "".join(f'<a href="/agenda/show-{i}">Show</a>' for i in range(4))
            if url.endswith("/show-3"):
                return '<html><meta property="og:title" content="Live music"><meta property="og:description" content="Concert 14 November 2027"></html>'
            raise RuntimeError("HTTP Error 500")
        download.side_effect = get
        with self.assertRaisesRegex(RuntimeError, "detail requests failed"):
            scrape_venue("Metropool")


if __name__ == "__main__":
    unittest.main()
