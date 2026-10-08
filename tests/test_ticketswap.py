"""Regression checks for automatic, safe TicketSwap link enrichment."""
import unittest

from scrapers.ticketswap import (
    _ts_candidate_score,
    _ts_link_date,
    VERIFIED_EVENTS,
    enrich_ticketswap_urls,
)
from unittest.mock import patch


class TicketSwapMatchingTests(unittest.TestCase):
    def setUp(self):
        self.concert = {
            "artist": "Robert Jon & The Wreck",
            "venue": "TivoliVredenburg",
            "city": "Utrecht",
            "date": "2026-10-10",
            "url": "https://example.org/robert-jon",
        }

    def test_date_from_direct_link(self):
        self.assertEqual(
            _ts_link_date("https://www.ticketswap.nl/concert-tickets/"
                          "robert-jon-utrecht-2026-10-10-Abc123"),
            "2026-10-10",
        )

    def test_wrong_date_never_matches(self):
        self.assertEqual(
            _ts_candidate_score(
                self.concert,
                "https://www.ticketswap.nl/concert-tickets/"
                "robert-jon-the-wreck-utrecht-2026-10-11-Abc123",
            ),
            -1,
        )

    def test_wrong_location_never_matches(self):
        self.assertEqual(
            _ts_candidate_score(
                self.concert,
                "https://www.ticketswap.nl/concert-tickets/"
                "robert-jon-the-wreck-berlin-2026-10-10-Abc123",
            ),
            -1,
        )

    def test_matching_event_accepts_exact_date_and_location(self):
        self.assertGreaterEqual(
            _ts_candidate_score(
                self.concert,
                "https://www.ticketswap.nl/concert-tickets/"
                "robert-jon-the-wreck-utrecht-2026-10-10-Abc123",
            ),
            0,
        )

    def test_known_excelsior_event_is_persisted_without_network(self):
        event = {
            "artist": "30 Jaar Excelsior Recordings",
            "venue": "Tolhuistuin",
            "city": "Amsterdam",
            "date": "2026-12-27",
            "url": "https://www.paradiso.nl/nl/programma/"
                   "30-jaar-excelsior-recordings/2902321",
        }
        with patch("scrapers.ticketswap._search_candidates", return_value=[]):
            result = enrich_ticketswap_urls([event])
        self.assertEqual(
            result[0]["ticketSwapUrl"],
            VERIFIED_EVENTS[(event["url"] + "/", event["date"])],
        )

    def test_existing_link_survives_failed_search(self):
        event = dict(self.concert)
        event["ticketSwapUrl"] = (
            "https://www.ticketswap.nl/concert-tickets/"
            "robert-jon-the-wreck-utrecht-2026-10-10-Abc123"
        )
        with patch("scrapers.ticketswap._search_candidates",
                   side_effect=Exception("HTTP 403")):
            result = enrich_ticketswap_urls([event])
        self.assertEqual(result[0]["ticketSwapUrl"], event["ticketSwapUrl"])


if __name__ == "__main__":
    unittest.main()
