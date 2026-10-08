import unittest
from audit.publish_ticketswap_sitemaps import assign, score

ROBERT = {
    "artist": "Robert Jon & The Wreck", "city": "Utrecht",
    "venue": "TivoliVredenburg", "date": "2026-10-10",
}
RIGHT = ("https://www.ticketswap.com/concert-tickets/"
         "robert-jon-and-the-wreck-utrecht-tivolivredenburg-2026-10-10-CYLnnmdzxYMPnAcUdXr8i")

class TicketSwapOfficialSitemapTests(unittest.TestCase):
    def test_exact_date_artist_venue(self):
        self.assertGreaterEqual(score(ROBERT, RIGHT), 0)

    def test_wrong_date_is_rejected(self):
        self.assertEqual(score(ROBERT, RIGHT.replace("2026-10-10", "2026-10-11")), -1)

    def test_wrong_city_and_venue_rejected(self):
        self.assertEqual(score(ROBERT, RIGHT.replace("utrecht-tivolivredenburg",
                                                    "berlin-rockclub")), -1)

    def test_wrong_artist_rejected(self):
        self.assertEqual(score(ROBERT, RIGHT.replace("robert-jon-and-the-wreck",
                                                    "unknown-other-band")), -1)

    def test_known_exact_link_is_never_overwritten(self):
        row = dict(ROBERT, ticketSwapUrl="https://example.org/verified")
        self.assertEqual(assign([row], [RIGHT]), 0)
        self.assertEqual(row["ticketSwapUrl"], "https://example.org/verified")

if __name__ == "__main__":
    unittest.main()
