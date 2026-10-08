import json
import unittest
from unittest.mock import patch

from scrapers.gebouw_t import gebouw_t_parse_event, gebouw_t_find_event_urls
from scrapers.dbs import scrape_dbs, parse_dbs_api_event


class NewlyAddedVenueTests(unittest.TestCase):
    def test_gebouw_t_parses_event(self):
        html = ('<html><h1>Indie Rock Live</h1>'
                '<p>zaterdag 24 oktober 2026</p>'
                '<p>Locatie: Gebouw-T Datum: 24 oktober 2026</p>'
                '<p>Aanvang: 20:30</p><p>Live concert met rock band</p></html>')
        event = gebouw_t_parse_event(html, 'https://gebouw-t.nl/agenda/indie-rock-live/')
        self.assertIsNotNone(event)
        self.assertEqual(event['date'], '2026-10-24')
        self.assertEqual(event['source'], 'Gebouw-T')

    def test_gebouw_t_unquoted_links(self):
        html = '<a href=https://gebouw-t.nl/agenda/marble-sounds/ class="event-card">Concert</a>'
        self.assertEqual(gebouw_t_find_event_urls(html),
                         ['https://gebouw-t.nl/agenda/marble-sounds'])

    @patch('scrapers.dbs.download_page_retry')
    def test_dbs_official_api(self, download):
        payload = {
            "events": [{
                "status": "publish",
                "title": "INDIE LIVE + Support",
                "url": "https://dbstudio.nl/event/indie-live/",
                "start_date": "2027-04-11 20:30:00",
                "venue": {"venue": "dB's", "city": "Utrecht"},
            }],
            "total_pages": 1,
        }
        download.return_value = json.dumps(payload)
        events = scrape_dbs()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['date'], '2027-04-11')
        self.assertEqual(events[0]['time'], '20:30')
        self.assertEqual(events[0]['url'], 'https://dbstudio.nl/event/indie-live')

    def test_dbs_ignores_non_utrecht_venues(self):
        result = parse_dbs_api_event({
            "status": "publish",
            "title": "Elsewhere",
            "url": "https://dbstudio.nl/event/out-of-town/",
            "start_date": "2027-04-11 20:30:00",
            "venue": {"venue": "Elsewhere", "city": "Amsterdam"},
        })
        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()
