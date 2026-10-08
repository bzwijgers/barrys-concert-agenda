import unittest
from unittest.mock import patch

from scrapers.gebouw_t import gebouw_t_parse_event
from scrapers.dbs import scrape_dbs


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

    @patch('scrapers.dbs.download_page_retry')
    @patch('scrapers.dbs.find_site_event_urls')
    def test_dbs_parses_event(self, find_urls, download):
        url = 'https://www.dbstudio.nl/event/indie-live/'
        find_urls.return_value = [url]
        download.side_effect = [
            '<html>Agenda</html>',
            ('<html><h1>Indie Live</h1>'
             '<script type="application/ld+json">'
             '{"startDate":"2027-04-11T20:30:00+02:00"}'
             '</script><p>Live concert</p></html>')
        ]
        with patch('scrapers.dbs.date') as mock_date:
            from datetime import date
            mock_date.today.return_value = date(2026, 10, 8)
            mock_date.fromisoformat.side_effect = date.fromisoformat
            events = scrape_dbs()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['date'], '2027-04-11')


if __name__ == '__main__':
    unittest.main()
