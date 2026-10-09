"""Focused regressions for the October 2026 five-venue quality audit."""
import unittest
from unittest.mock import patch

from scrapers.gebouw_t import gebouw_t_parse_event
from scrapers.new_venues import (
    deduplicate_doornroosje_festival_days,
    is_nonconcert_listing,
    klokgebouw_listing_cards,
    parse_event,
    scrape_venue,
)


class VenueQualityTests(unittest.TestCase):
    def test_spot_rejects_collection_and_subscriptions_not_concerts(self):
        self.assertTrue(is_nonconcert_listing(
            "SPOT Groningen", "https://www.spotgroningen.nl/programma/verzameling/english"))
        self.assertTrue(is_nonconcert_listing(
            "SPOT Groningen", "https://www.spotgroningen.nl/programma/abonnement-takeroot-presents"))
        self.assertFalse(is_nonconcert_listing(
            "SPOT Groningen", "https://www.spotgroningen.nl/programma/ed-o-brien"))

    def test_klokgebouw_listing_has_date_and_genre_per_event(self):
        html = (
            '<a href="/agenda/revolution-calling-20-11">'
            '<span>vr. 20 nov.</span><strong>Rock</strong>'
            '<span>Revolution Calling</span></a>'
            '<a href="/agenda/cisco-connect-benelux">'
            '<span>do. 26 nov.</span><b>Business</b>'
            'Cisco Connect Benelux</a>'
            '<a href="/agenda/winson-all-day-long">'
            '<span>vr. 13 nov.</span><b>Dance</b> Winson</a>'
        )
        data = klokgebouw_listing_cards(html)
        rock = data["https://www.klokgebouw.nl/agenda/revolution-calling-20-11"]
        self.assertEqual((rock["day"], rock["month"], rock["genre"]), (20, 11, "rock"))
        self.assertEqual(data["https://www.klokgebouw.nl/agenda/cisco-connect-benelux"]["genre"], "business")
        self.assertEqual(data["https://www.klokgebouw.nl/agenda/winson-all-day-long"]["genre"], "dance")

    @patch("scrapers.new_venues.download_page_retry")
    @patch("scrapers.new_venues.parse_event")
    def test_klokgebouw_filters_business_and_dance_and_corrects_date(self, parse, download):
        listing = (
            '<a href="/agenda/revolution-calling-20-11">vr. 20 nov. Rock Revolution Calling</a>'
            '<a href="/agenda/cisco-connect-benelux">do. 26 nov. Business Cisco Connect</a>'
            '<a href="/agenda/winson-all-day-long">vr. 13 nov. Dance Winson</a>'
        )
        download.side_effect = lambda url, attempts=2: listing if url.endswith("/agenda") else "<html></html>"
        parse.return_value = {
            "artist": "Revolution Calling", "venue": "Klokgebouw", "city": "Eindhoven",
            "country": "NL", "date": "2026-11-21", "time": "20:00",
            "source": "Klokgebouw",
            "url": "https://www.klokgebouw.nl/agenda/revolution-calling-20-11",
        }
        events = scrape_venue("Klokgebouw")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["date"], "2026-11-20")
        self.assertEqual(events[0]["time"], "")
        self.assertEqual(parse.call_count, 1)

    def test_spot_start_programma_is_show_time_not_foyer_opening(self):
        html = (
            '<html><head>'
            '<meta property="og:title" content="Ed O’Brien">'
            '<meta property="og:description" content="woensdag 14 oktober 2026">'
            '</head><body>'
            '<h1>Ed O’Brien</h1><p>Woensdag 14 oktober 2026</p>'
            '<p>19:30 foyerdeuren open</p>'
            '<p>20:30 start programma</p>'
            '<p>20:30 start of event</p>'
            '</body></html>'
        )
        event = parse_event(
            html, "https://www.spotgroningen.nl/programma/ed-obrien",
            "SPOT Groningen", "Groningen",
        )
        self.assertIsNotNone(event)
        self.assertEqual(event["date"], "2026-10-14")
        self.assertEqual(event["time"], "20:30")

    def test_gebouw_t_primary_aanvang_overrides_midnight_metadata(self):
        html = (
            '<html><script type="application/ld+json">'
            '{"startDate":"2026-11-05T00:00:00"}</script>'
            '<h1>Pitou</h1>'
            '<p>Locatie: Zaal Datum: do 05 nov \'26 Zaal open: 20:00 '
            'Aanvang: 21:00 Genre: Indie / Alternative</p>'
            '<p>Live concert met band en zang</p></html>'
        )
        item = gebouw_t_parse_event(html, "https://gebouw-t.nl/agenda/pitou/")
        self.assertIsNotNone(item)
        self.assertEqual(item["date"], "2026-11-05")
        self.assertEqual(item["time"], "21:00")

    def test_gebouw_t_themafeest_does_not_count_as_concert(self):
        html = (
            "<html><h1>Coming Out Night 2026: MEROL (Ratkapje DJ-set)</h1>"
            "<p>10 oktober 2026 Aanvang: 20:00 Genre: Themafeest</p>"
            "<p>Live muziek en pop</p></html>"
        )
        self.assertIsNone(gebouw_t_parse_event(
            html, "https://gebouw-t.nl/agenda/coming-out-night-2026/"))

    def test_doornroosje_soulcrusher_festival_only_once(self):
        def item(url):
            return {
                "artist": "Soulcrusher", "venue": "Doornroosje",
                "city": "Nijmegen", "country": "NL",
                "date": "2026-10-10", "time": "",
                "source": "Doornroosje", "url": url,
            }
        events = deduplicate_doornroosje_festival_days([
            item("https://www.doornroosje.nl/event/soulcrusher-2026-1"),
            item("https://www.doornroosje.nl/event/soulcrusher-2026"),
        ])
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["url"],
                         "https://www.doornroosje.nl/event/soulcrusher-2026")


if __name__ == "__main__":
    unittest.main()
