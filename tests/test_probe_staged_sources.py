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
