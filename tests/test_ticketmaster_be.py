"""Belgium should reuse the API without leaking Dutch concerts into the BE feed."""
import unittest
from datetime import date

from scrapers.ticketmaster_be import scrape_ticketmaster_be
from scrapers.ticketmaster_nl import event_to_concert, merge_ticketmaster

class TicketmasterBelgiumTests(unittest.TestCase):
    @staticmethod
    def show(country="BE", url="https://www.ticketmaster.be/event/123"):
        return {
            "type": "event", "name": "Test Band",
            "url": url,
            "classifications": [{"segment": {"id": "KZFzniwnSyZfZ7v7nJ"}}],
            "dates": {"status": {"code": "onsale"}, "start": {"localDate": "2027-03-05", "localTime": "20:00:00"}},
            "_embedded": {"venues": [{
                "name": "Testzaal", "city": {"name": "Antwerpen"},
                "country": {"countryCode": country}
            }]}
        }

    def test_valid_belgian_event(self):
        result = event_to_concert(self.show(), today="2026-10-10", country_code="BE")
        self.assertIsNotNone(result)
        self.assertEqual(result["country"], "BE")
        self.assertEqual(result["source"], "Ticketmaster BE")

    def test_dutch_event_is_rejected(self):
        self.assertIsNone(event_to_concert(self.show("NL"), today="2026-10-10", country_code="BE"))

    def test_other_domain_is_rejected(self):
        self.assertIsNone(event_to_concert(
            self.show(url="https://www.ticketmaster.nl/event/123"),
            today="2026-10-10", country_code="BE"))

    def test_scraper_country_query_and_dedup(self):
        calls = []
        def getter(params, key):
            calls.append(params)
            return {"page": {"totalElements": 2, "totalPages": 1},
                    "_embedded": {"events": [self.show(), self.show()]}}
        shows = scrape_ticketmaster_be(api_key="test-key", today=date(2026, 10, 10), getter=getter)
        self.assertEqual(len(shows), 1)
        self.assertEqual(calls[0]["countryCode"], "BE")
        merged, doubles = merge_ticketmaster(shows, shows)
        self.assertFalse(merged)
        self.assertEqual(doubles, 1)

if __name__ == "__main__":
    unittest.main()
