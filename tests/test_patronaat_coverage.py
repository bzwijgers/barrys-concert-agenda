"""Coverage regression cases for previously missing music events."""
import unittest
from unittest.mock import patch

from scrapers.common import scrape_detail_events, scrape_patronaat


class PatronaatCoverageTests(unittest.TestCase):
    @patch("scrapers.common.download_page_retry")
    def test_visible_date_missing_uses_matching_slug(self, download):
        html = """<html><head><title>SlodDe &amp; Vos | Patronaat</title>
        <script type="application/ld+json">{"startDate":"2020-10-16T15:15:00"}</script>
        </head><body><h1>SlodDe &amp; Vos</h1><p>Start: 20:00</p></body></html>"""
        download.return_value = html
        url = "https://patronaat.nl/event/slodde-vos-16-10-26/"
        actual = scrape_detail_events([url],"Patronaat","Haarlem","Patronaat")
        self.assertEqual(len(actual), 1)
        self.assertEqual(actual[0]["artist"], "SlodDe & Vos")
        self.assertEqual(actual[0]["date"], "2026-10-16")
        self.assertEqual(actual[0]["time"], "20:00")

    @patch("scrapers.common.download_page_retry")
    def test_stale_structured_time_is_discarded(self, download):
        download.return_value = """<html><head><title>SlodDe &amp; Vos | Patronaat</title>
            <script>{"startDate":"2020-10-16T15:15:00"}</script></head>
            <body><h1>SlodDe &amp; Vos</h1></body></html>"""
        events = scrape_detail_events(
            ["https://patronaat.nl/event/slodde-vos-16-10-26/"],
            "Patronaat","Haarlem","Patronaat",
        )
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["date"], "2026-10-16")
        self.assertEqual(events[0]["time"], "")

    @patch("scrapers.common.download_page_retry")
    def test_visible_date_clears_old_schema_timestamp(self, download):
        download.return_value = """<html><head><title>SlodDe &amp; Vos | Patronaat</title>
            <script>{"startDate":"2020-10-16T15:15:00"}</script></head>
            <body><h1>SlodDe &amp; Vos</h1>
            <div>vr 16 okt 2026</div></body></html>"""
        events = scrape_detail_events(
            ["https://patronaat.nl/event/slodde-vos-16-10-26/"],
            "Patronaat","Haarlem","Patronaat",
        )
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["date"], "2026-10-16")
        self.assertEqual(events[0]["time"], "")

    @patch("scrapers.common.download_page_retry")
    def test_redirect_to_unrelated_event_must_not_be_mislabeled(self, download):
        download.return_value = """<html><head><title>SpoorBijster | Patronaat</title>
            <script>{"startDate":"2020-10-16T23:00:00"}</script></head>
            <body><h1>SpoorBijster</h1></body></html>"""
        actual = scrape_detail_events(
            ["https://patronaat.nl/event/yuna-10-10-26/"],
            "Patronaat","Haarlem","Patronaat",
        )
        self.assertEqual(actual, [])

    @patch("scrapers.common.scrape_detail_events")
    @patch("scrapers.common.download_page_retry")
    def test_full_programme_adds_concert_absent_from_genres(self, download, detail):
        # Genre pages return one concert; full programme contains that
        # concert plus an uncategorised additional live performance.
        def fetch(url, attempts=3):
            if "/programma/" in url:
                return ('<a href="/event/only-in-full-programme-16-10-26/">Concert</a>'
                        '<a href="/event/genre-show-20-10-26/">Concert</a>')
            return '<a href="/event/genre-show-20-10-26/">Concert</a>'
        download.side_effect = fetch
        detail.return_value = []
        scrape_patronaat()
        checked = detail.call_args.args[0]
        self.assertTrue(any("only-in-full-programme" in x for x in checked))
        self.assertEqual(len(set(x.rstrip("/") for x in checked)),2)


if __name__=="__main__":
    unittest.main()
