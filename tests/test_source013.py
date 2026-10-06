import unittest

from scrapers.source013 import source013_parse_event


class Source013ArtistTests(unittest.TestCase):
    def _parse(self, name, url):
        html = (
            '<script type="application/ld+json">'
            '{"@type":"Event","name":"' + name + '",'
            '"startDate":"2026-11-03T20:00:00+01:00",'
            '"location":{"@type":"Place","name":"Poppodium 013 - Main"}}'
            '</script>'
        )
        return source013_parse_event(html, url)

    def test_strips_tour_title_when_url_slug_is_artist(self):
        concert = self._parse(
            "Puscifer The Normal Isn't Tour",
            "https://www.013.nl/programma/128504/puscifer",
        )
        self.assertEqual(concert["artist"], "Puscifer")

    def test_keeps_multiword_artist_and_strips_suffix(self):
        concert = self._parse(
            "Queens of the Stone Age World Tour",
            "https://www.013.nl/programma/999999/queens-of-the-stone-age",
        )
        self.assertEqual(concert["artist"], "Queens of the Stone Age")

    def test_keeps_name_when_slug_matches_full_name(self):
        concert = self._parse(
            "The Australian Pink Floyd Show",
            "https://www.013.nl/programma/999998/the-australian-pink-floyd-show",
        )
        self.assertEqual(concert["artist"], "The Australian Pink Floyd Show")


if __name__ == "__main__":
    unittest.main()
