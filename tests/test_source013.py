import unittest

from scrapers.source013 import (source013_parse_event, source013_is_bot_verification,
                                   scrape_013, Source013Blocked)
from unittest.mock import patch


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



class Source013CaptchaTests(unittest.TestCase):
    CAPTCHA = (
        '<!DOCTYPE html><html><head><title>Bot Verification</title></head>'
        '<body><form id="lsrecaptcha-form">Complete captcha</form></body></html>'
    )

    def test_detects_protection_without_confusing_real_listing(self):
        self.assertTrue(source013_is_bot_verification(self.CAPTCHA))
        normal_html = (
            '<html><a href="/programma/128504/puscifer">Puscifer</a></html>'
        )
        self.assertFalse(source013_is_bot_verification(normal_html))

    @patch("scrapers.source013.download_page_retry")
    def test_bot_verification_stops_live_download_early(self, download):
        download.return_value = self.CAPTCHA
        with self.assertRaises(Source013Blocked):
            scrape_013()
        self.assertEqual(download.call_count, 1)

    @patch("scrapers.source013.download_page")
    @patch("scrapers.source013.download_page_retry")
    def test_valid_agenda_followed_by_bot_block_on_details(self, retry, download):
        listing = "<html>" + "".join(
            f'<a href="/programma/{120000+i}/testband-{i}">Band</a>'
            for i in range(30)
        ) + "</html>"
        retry.side_effect = [listing, self.CAPTCHA]
        with self.assertRaises(Source013Blocked):
            scrape_013()
        # Never schedule dozens of detail-page requests after a CAPTCHA.
        download.assert_not_called()



if __name__ == "__main__":
    unittest.main()
