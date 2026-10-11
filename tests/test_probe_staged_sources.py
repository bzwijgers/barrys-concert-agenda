import unittest
from scrapers.next_sources import CANDIDATES
from audit.probe_staged_sources import probe

class ProbeTests(unittest.TestCase):
    def test_only_music_events(self):
        venue = next(x for x in CANDIDATES if x.name == "Theater Walhalla")
        html = '<script type="application/ld+json">{"@type":"Event","name":"Cabaret","startDate":"2027-05-10"}</script>'
        self.assertEqual(probe(venue, getter=lambda _: html)["status"], "needs-custom-scraper")

    def test_offline_does_not_publish(self):
        venue = next(x for x in CANDIDATES if x.name == "Van Polanen Presenteert")
        def offline(_):
            raise OSError("offline")
        self.assertEqual(probe(venue, getter=offline)["status"], "unavailable")

    def test_walhalla_music_metadata_still_requires_theaterconcert_category(self):
        venue = next(x for x in CANDIDATES if x.name == "Theater Walhalla")
        html = ('<script type="application/ld+json">'
                '{"@type":"MusicEvent","name":"A live band",'
                '"startDate":"2027-05-10",'
                '"url":"https://www.theaterwalhalla.nl/voorstelling/a-live-band/"}'
                '</script>')
        result = probe(venue, getter=lambda _: html)
        self.assertEqual(result["status"], "needs-theaterconcert-filter")
