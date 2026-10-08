import unittest
from unittest.mock import patch
from scrapers.new_venues import scrape_venue


class MetropoolPaginationTests(unittest.TestCase):
    def mock_download(self, url, attempts=2):
        if url.endswith("/agenda"):
            return '<a href="/agenda/khemmis">Khemmis</a>'
        if "pNumber=2" in url:
            return '<a href="/agenda/rowwen-heze">Rowwen Heze</a>'
        if "pNumber=3" in url:
            raise RuntimeError("Lege HTML-response ontvangen voor " + url)
        if "/agenda/khemmis" in url:
            title = "Khemmis"
        elif "/agenda/rowwen-heze" in url:
            title = "Rowwen Heze"
        else:
            raise AssertionError("Unexpected URL " + url)
        return ('<html><head><meta property="og:title" content="' + title + '">'
                '<meta property="og:description" '
                'content="Concert in Hengelo zaterdag 14 november 2026"></head>'
                '<body>Hengelo Tijdschema Aanvang hoofdact 20:30</body></html>')

    @patch("scrapers.new_venues.download_page_retry")
    def test_empty_page_ends_pagination_but_keeps_events(self, download):
        download.side_effect = self.mock_download
        shows = scrape_venue("Metropool")
        self.assertEqual(len(shows), 2)
        self.assertEqual(
            {x["artist"] for x in shows},
            {"Khemmis", "Rowwen Heze"}
        )

    @patch("scrapers.new_venues.download_page_retry")
    def test_unexpected_http_failure_not_silenced(self, download):
        def f(url, attempts=2):
            if "pNumber=3" in url:
                raise RuntimeError("HTTP 500")
            return self.mock_download(url, attempts)
        download.side_effect = f
        with self.assertRaisesRegex(RuntimeError, "page 3 failed"):
            scrape_venue("Metropool")


if __name__ == "__main__":
    unittest.main()
