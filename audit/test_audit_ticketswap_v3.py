"""Tests for V3's report-only TicketSwap data audit."""
import unittest

from audit.audit_ticketswap_v3 import problem


class TicketSwapAuditExceptionsTests(unittest.TestCase):
    def test_verified_lords_headliner_has_correct_date_venue_and_source(self):
        event = {
            "artist": "LORDS OF ALTAMONT + Sick Shooters",
            "venue": "dB's",
            "city": "Utrecht",
            "date": "2026-11-22",
            "url": "https://dbstudio.nl/event/lords-of-altamont",
            "ticketSwapUrl": (
                "https://www.ticketswap.nl/concert-tickets/"
                "lords-of-altamont-utrecht-dbs-oefenstudios-concertzaal-"
                "muziekcafe-2026-11-22-CdENvHWLHRMhVuoMG4LxW"
            )
        }
        self.assertEqual("verified-exception", problem(event))
        self.assertEqual("wrong-date", problem({**event, "date": "2026-11-23"}))
        self.assertEqual("wrong-artist", problem({**event, "artist": "Different act"}))

    def test_amare_free_entry_is_intentionally_not_a_resale_match(self):
        event = {
            "artist": "Just Graduated: Marco Bernardi en Katrina Kabineca",
            "venue": "Amare",
            "city": "Den Haag",
            "date": "2026-12-06",
            "url": (
                "https://www.podiuminfo.nl/concert/485136/"
                "Just-Graduated-Marco-Bernardi-en-Katrina-Kabineca/Amare"
            ),
            "ticketSwapUrl": (
                "https://www.ticketswap.nl/concert-tickets/"
                "just-graduated-marco-bernardi-katrina-kabinecka-"
                "the-hague-amare-2026-12-06-CaVMYZZezZidh1f2RqyDT"
            )
        }
        self.assertEqual("suppressed-free-admission", problem(event))
        self.assertEqual("wrong-artist", problem({**event, "artist": "Someone else"}))


if __name__ == "__main__":
    unittest.main()
