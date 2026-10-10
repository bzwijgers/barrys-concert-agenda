import unittest
from datetime import date
from scrapers.official_music_events import parse_official_music_events

class OfficialMusicEventsTests(unittest.TestCase):
    def test_music_event_strictly_parsed(self):
        html = '<script type="application/ld+json">{"@context":"https://schema.org","@type":"MusicEvent","name":"Band A","startDate":"2027-01-20T20:30:00+01:00","location":{"name":"AB Club"},"url":"https://www.abconcerts.be/nl/agenda/band-a"}</script>'
        shows = parse_official_music_events(html, "https://www.abconcerts.be/nl/agenda", "Ancienne Belgique", "Brussel", "BE", date(2026, 10, 10))
        self.assertEqual(len(shows), 1)
        self.assertEqual(shows[0]["time"], "20:30")
        self.assertEqual(shows[0]["country"], "BE")
        self.assertEqual(shows[0]["venue"], "AB Club")

    def test_reject_non_music_and_offsite_urls(self):
        html = '<script type="application/ld+json">[{"@type":"Event","name":"Theater","startDate":"2027-01-20"},{"@type":"MusicEvent","name":"Party Night","startDate":"2027-01-20"},{"@type":"MusicEvent","name":"Band B","startDate":"2027-01-20","url":"https://tickets.example.com/show"}]</script>'
        self.assertEqual(parse_official_music_events(html, "https://www.abconcerts.be/nl/agenda", "AB", "Brussel", "BE", date(2026,10,10)), [])

    def test_reject_cancelled_and_past(self):
        html = '<script type="application/ld+json">[{"@type":"MusicEvent","name":"Band C","startDate":"2026-01-20"},{"@type":"MusicEvent","name":"Band D","startDate":"2027-01-20","eventStatus":"https://schema.org/EventCancelled"}]</script>'
        self.assertEqual(parse_official_music_events(html, "https://www.abconcerts.be/nl/agenda", "AB", "Brussel", "BE", date(2026,10,10)), [])

if __name__ == "__main__":
    unittest.main()
