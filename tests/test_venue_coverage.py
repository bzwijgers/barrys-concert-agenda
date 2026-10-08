"""Regression tests for complete official schedules and Hedon's primary dates."""
import re
import unittest
from datetime import date
from unittest.mock import patch
from urllib.parse import urlsplit

from scrapers.new_venues import hedon_primary_date_time, parse_event, scrape_venue


class VenueCoverageTests(unittest.TestCase):
    def test_hedon_primary_date_weekday_disambiguation(self):
        html = ('<dt class="text-primary">Datum</dt><dd><strong>vr 1 okt.</strong></dd>'
                '<dt>Aanvang</dt><dd><strong>18:30</strong></dd>')
        self.assertEqual(hedon_primary_date_time(html, date(2026, 10, 8)),
                         ("2027-10-01", "18:30"))

    def test_hedon_real_html_structure(self):
        html = ('<html><head><meta property="og:title" content="FROUKJE - Hedon Zwolle"></head>'
                '<body><dt class="text-primary fs-body-xs">Datum</dt>'
                '<dd><strong><!-- --> wo 4 nov. <!-- --></strong></dd>'
                '<dt>Zaal open</dt><dd><strong>19:30</strong></dd>'
                '<dt>Aanvang</dt><dd><strong>19:30</strong></dd>'
                '<aside><time datetime="2026-10-11">Other show</time></aside></body></html>')
        with patch("scrapers.new_venues.date") as mock:
            mock.today.return_value = date(2026, 10, 8)
            mock.side_effect = date
            x = parse_event(html, "https://hedon-zwolle.nl/voorstelling/32972/froukje",
                            "Hedon", "Zwolle")
        self.assertIsNotNone(x)
        self.assertEqual((x["date"],x["time"],x["artist"]),
                         ("2026-11-04","19:30","FROUKJE"))

    @patch("scrapers.new_venues.parse_event")
    @patch("scrapers.new_venues.download_page_retry")
    def test_neushoorn_webflow_pagination(self, download, parse):
        base="https://www.neushoorn.nl/programma"
        def fake_html(url, attempts=2):
            if url==base:
                return ('<a href="?d9baa62c_page=2">Next</a>'
                        + "".join(f'<a href="/events/band-{x}">show</a>' for x in range(100)))
            if url==base+"?d9baa62c_page=2":
                return "".join(f'<a href="/events/band-{x}">show</a>' for x in range(100,125))
            raise AssertionError("Unexpected url: "+url)
        download.side_effect=fake_html
        def fake_parse(html,url,name,city):
            return {"artist":url.rsplit("/",1)[-1],"venue":name,"city":city,"country":"NL",
                    "date":"2027-04-20","time":"20:00","source":name,"url":url}
        parse.side_effect=fake_parse
        events=scrape_venue("Neushoorn")
        self.assertEqual(len(events),125)
        self.assertTrue(any(e["url"].endswith("band-124") for e in events))

    @patch("scrapers.common.scrape_detail_events")
    @patch("scrapers.common.download_page_retry")
    def test_tivoli_follows_each_genre_pagination(self, download, detail):
        from scrapers.common import scrape_tivolivredenburg
        def serve(url, attempts=3):
            match=re.search(r"sf_genre=([^&]+)",url)
            genre=match.group(1)
            number=int(re.search(r"/page/(\d+)/",url).group(1)) if "/page/" in url else 1
            if genre=="pop":
                suffix=f'<a href="/agenda/page/{number+1}/?sf_genre=pop">Next</a>' if number<3 else ""
                return f'<a href="/agenda/{100+number}/artist-{number}">Concert</a>'+suffix
            if number!=1:raise AssertionError("Unexpected genre page")
            return '<a href="/agenda/999/band">Concert</a>'
        download.side_effect=serve
        detail.return_value=[]
        scrape_tivolivredenburg()
        passed_urls=detail.call_args.args[0]
        self.assertTrue(any("/agenda/103/" in u for u in passed_urls))
        self.assertFalse(any("/agenda/page/" in u for u in passed_urls))
        self.assertEqual(download.call_count,15)


if __name__=="__main__":
    unittest.main()
