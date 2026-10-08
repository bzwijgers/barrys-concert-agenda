import unittest
from scrapers.podiuminfo_venues import parse_podiuminfo_music_event

class PodiuminfoVenueTests(unittest.TestCase):
    def fixture(self, name="The Band @ Het Bolwerk", venue="Het Bolwerk", when="2027-02-03T20:30:00+01:00"):
        return {
            "@type": "MusicEvent", "name": name,
            "location": {"@type": "Place", "name": venue},
            "startDate": when,
            "url": "https://www.podiuminfo.nl/concert/12345/The-Band/Het-Bolwerk/",
            "eventStatus": "https://schema.org/EventScheduled",
        }

    def test_bolwerk_music_event(self):
        e = parse_podiuminfo_music_event(self.fixture(), "Bolwerk", "Het Bolwerk", "Sneek")
        self.assertEqual(e["artist"], "The Band")
        self.assertEqual((e["date"],e["time"]),("2027-02-03","20:30"))

    def test_other_sneek_venues_excluded(self):
        self.assertIsNone(parse_podiuminfo_music_event(
            self.fixture(venue="Theater Sneek"), "Bolwerk", "Het Bolwerk", "Sneek"
        ))

    def test_amare_non_concert_activity_excluded(self):
        self.assertIsNone(parse_podiuminfo_music_event(
            self.fixture(name="Social Dance: Salsa Night @ Amare", venue="Amare"),
            "Amare", "Amare", "Den Haag"
        ))

if __name__ == "__main__":
    unittest.main()
