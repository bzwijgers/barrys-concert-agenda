import unittest
from datetime import date
from unittest.mock import patch

from scrapers.podiuminfo_full import (
    parse_full_podiuminfo_anchor,
    scrape_full_podiuminfo_source,
)


class FullPodiuminfoTests(unittest.TestCase):
    def make_link(self, title, day, venue="Amare", city="Den Haag"):
        return {
            "href": "https://www.podiuminfo.nl/concert/457139/Test-Concert/"
                    + venue.replace(" ","-") + "/",
            "aria-label": f"Concert {title}, {day}, {venue}, {city}, tickets beschikbaar",
        }

    def test_amare_real_event(self):
        a=self.make_link("DeWolff - Full Moon Ritual", "zondag 6 december 2026 om 20:15")
        x=parse_full_podiuminfo_anchor(a,"Amare","Amare","Den Haag",today=date(2026,10,8))
        self.assertIsNotNone(x)
        self.assertEqual((x["artist"],x["date"],x["time"]),
                         ("DeWolff - Full Moon Ritual","2026-12-06","20:15"))

    def test_bolwerk_real_event(self):
        a=self.make_link("Ana Popovic","vrijdag 15 oktober 2027 om 20:30",
                         venue="Het Bolwerk",city="Sneek")
        x=parse_full_podiuminfo_anchor(a,"Het Bolwerk","Bolwerk","Sneek",
                                       today=date(2026,10,8))
        self.assertEqual((x["artist"],x["date"],x["venue"]),
                         ("Ana Popovic","2027-10-15","Het Bolwerk"))

    def test_excludes_social_dance(self):
        a=self.make_link("Social Dance: BachaZouk Night",
                         "donderdag 8 oktober 2026 om 19:30")
        self.assertIsNone(parse_full_podiuminfo_anchor(a,"Amare","Amare","Den Haag",
                                                       today=date(2026,10,8)))

    def test_excludes_different_venue(self):
        a=self.make_link("Teenage Fanclub","zaterdag 31 oktober 2026 om 20:30",
                         venue="Het Bolwerk",city="Sneek")
        self.assertIsNone(parse_full_podiuminfo_anchor(a,"Amare","Amare","Den Haag",
                                                       today=date(2026,10,8)))

    @patch("scrapers.podiuminfo_full.download_page_retry")
    def test_scrape_full_not_truncated_to_25(self, download):
        def anchor(i):
            return ('<a href="https://www.podiuminfo.nl/concert/'
                    + str(100000+i) + '/Test-Band-'+str(i)+'/Amare/"'
                    + ' aria-label="Concert Test Band '+str(i)
                    + ', vrijdag 6 november 2026 om 20:15, Amare, Den Haag">'
                    + 'Test Band</a>')
        download.return_value="<html>"+"".join(anchor(x) for x in range(39))+"</html>"
        with patch("scrapers.podiuminfo_full.date") as fake_date:
            fake_date.today.return_value=date(2026,10,8)
            fake_date.side_effect=date
            r=scrape_full_podiuminfo_source("Amare")
        self.assertEqual(len(r),39)


if __name__=="__main__":
    unittest.main()
