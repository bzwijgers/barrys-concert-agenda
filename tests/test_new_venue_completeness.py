"""Regression tests: never publish a silently truncated new-venue feed."""
import unittest
from unittest.mock import patch

from scrapers import new_venues


def event(url):
    return {
        "artist": "Test Artist", "venue": "De Helling", "city": "Utrecht",
        "country": "NL", "date": "2027-06-01", "time": "20:00",
        "source": "De Helling", "url": url,
    }


class VenueCompletenessTests(unittest.TestCase):
    @patch("scrapers.new_venues.download_page_retry", return_value="<html></html>")
    @patch("scrapers.new_venues.discover")
    def test_limit_is_not_silently_truncated(self, discover, _download):
        discover.return_value = ["https://dehelling.nl/agenda/" + str(n) for n in range(4)]
        with self.assertRaisesRegex(RuntimeError, "exceeding processing limit"):
            new_venues.scrape_venue("De Helling", maximum=3)

    @patch("scrapers.new_venues.download_page_retry", return_value="<html></html>")
    @patch("scrapers.new_venues.discover", return_value=["https://dehelling.nl/agenda/one"])
    @patch("scrapers.new_venues.parse_event", return_value=None)
    def test_zero_parsed_concerts_is_failure(self, _parse, _discover, _download):
        with self.assertRaisesRegex(RuntimeError, "no future concerts parsed"):
            new_venues.scrape_venue("De Helling")

    @patch("scrapers.new_venues.download_page_retry")
    @patch("scrapers.new_venues.discover")
    @patch("scrapers.new_venues.parse_event")
    def test_many_detail_failures_are_failure(self, parse, discover, download):
        links = ["https://dehelling.nl/agenda/" + str(i) for i in range(10)]
        discover.return_value = links
        def fake_download(url, **kwargs):
            if url == "https://dehelling.nl/agenda/":
                return "<html></html>"
            if url.endswith(("/0", "/1", "/2")):
                raise RuntimeError("upstream request failed")
            return "<html></html>"
        download.side_effect = fake_download
        parse.side_effect = lambda html, url, name, city: event(url)
        with self.assertRaisesRegex(RuntimeError, "detail requests failed"):
            new_venues.scrape_venue("De Helling")

    @patch("scrapers.new_venues.scrape_venue")
    def test_one_failed_venue_fails_entire_batch(self, scrape):
        def fake_scrape(name):
            if name == "Hedon":
                raise RuntimeError("source unavailable")
            return [event("https://example.org/" + name.replace(" ", "-"))]
        scrape.side_effect = fake_scrape
        with self.assertRaisesRegex(RuntimeError, "Incomplete new-venue scrape.*Hedon"):
            new_venues.scrape_new_venues()


if __name__ == "__main__":
    unittest.main()
