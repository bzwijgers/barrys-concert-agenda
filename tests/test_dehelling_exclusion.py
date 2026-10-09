"""Keep De Helling club nights out without dropping genuine concerts."""
import unittest
from scrapers.new_venues import parse_event


class DeHellingGenreTests(unittest.TestCase):
    def test_freax_is_club_night(self):
        html = (
            '<html><head><meta property="og:title" content="FREAX">'
            '<meta property="og:description" '
            'content="Zaterdag 7 november 2027 in Utrecht"></head>'
            '<body>De Helling Utrecht · 7 november 2027</body></html>'
        )
        self.assertIsNone(parse_event(
            html, "https://dehelling.nl/agenda/freax-07-11-2027/",
            "De Helling", "Utrecht"
        ))

    def test_music_show_remains_in_agenda(self):
        html = (
            '<html><head><meta property="og:title" content="High Fade">'
            '<meta property="og:description" '
            'content="Concert donderdag 23 april 2027"></head>'
            '<body>De Helling Utrecht · 23 april 2027</body></html>'
        )
        show = parse_event(
            html, "https://dehelling.nl/agenda/high-fade-23-04-2027/",
            "De Helling", "Utrecht"
        )
        self.assertIsNotNone(show)
        self.assertEqual(show["artist"], "High Fade")


if __name__ == "__main__":
    unittest.main()
