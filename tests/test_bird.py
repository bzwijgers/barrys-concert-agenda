"""Regression tests for BIRD's official live-category Prismic feed."""
import unittest
from datetime import date
from unittest.mock import patch

from scrapers.bird import parse_bird_prismic_event, scrape_bird


def item(uid="rijck-26-11-2026", title="Rijck", category="live",
         event_date="2026-11-26T19:30:00+0000", times="Start 20:30 | Doors 20:00"):
    return {
        "type": "agenda", "uid": uid,
        "data": {
            "title": [{"type": "paragraph", "text": title}],
            "event_date": event_date,
            "times": [{"type": "paragraph", "text": times}],
            "main_categories": [{
                "main_category": {"uid": category}
            }],
            "meta_title": f"{title} live at BIRD Rotterdam",
        }
    }


class BirdPrismicTests(unittest.TestCase):
    def test_rijck_is_included_from_live_category(self):
        event = parse_bird_prismic_event(item(), today=date(2026, 10, 8))
        self.assertIsNotNone(event)
        self.assertEqual((event["artist"], event["date"], event["time"], event["source"]),
                         ("Rijck", "2026-11-26", "20:30", "BIRD"))
        self.assertEqual(event["url"], "https://bird-rotterdam.nl/event/rijck-26-11-2026")

    def test_partner_venues_from_bird_subtitle(self):
        gallowstreet = item(uid="gallowstreet-at-annabel-13-12-2026", title="Gallowstreet")
        gallowstreet["data"]["subtitle"] = [{"type": "paragraph", "text": "at Annabel"}]
        kraak = item(uid="kraak-smaak-22-04-27", title="Kraak & Smaak")
        kraak["data"]["subtitle"] = [{"type": "paragraph", "text": "At Maassilo"}]
        self.assertEqual(parse_bird_prismic_event(gallowstreet, today=date(2026, 10, 8))["venue"], "Annabel")
        self.assertEqual(parse_bird_prismic_event(kraak, today=date(2026, 10, 8))["venue"], "Maassilo")

    def test_club_event_is_not_a_live_concert(self):
        self.assertIsNone(parse_bird_prismic_event(item(category="club"),
                                                   today=date(2026, 10, 8)))

    def test_mixed_club_live_dj_session_excluded(self):
        record = item(title="CAFÉ DJ SESSIONS")
        record["data"]["main_categories"].append({"main_category": {"uid": "club"}})
        self.assertIsNone(parse_bird_prismic_event(record, today=date(2026, 10, 8)))

    def test_timezone_conversion_summer_and_winter(self):
        winter = item(event_date="2026-11-26T19:30:00+0000", times="")
        summer = item(event_date="2027-07-10T18:30:00+0000", times="")
        self.assertEqual(parse_bird_prismic_event(winter, today=date(2026, 10, 8))["time"], "20:30")
        self.assertEqual(parse_bird_prismic_event(summer, today=date(2026, 10, 8))["time"], "20:30")

    def test_past_event_not_returned(self):
        self.assertIsNone(parse_bird_prismic_event(
            item(event_date="2026-09-25T20:00:00+0000"), today=date(2026, 10, 8)))

    @patch("scrapers.bird._request_json")
    def test_pagination_collects_all_live_events_without_clubs(self, fake_request):
        events = [item(uid=f"artist-{i}", title=f"Artist {i}",
                       event_date="2027-05-10T19:00:00+0000") for i in range(19)]
        events.append(item(uid="club-party", title="Club Party", category="club"))
        fake_request.side_effect = [
            {"refs": [{"ref": "master", "isMasterRef": True}],
             "forms": {"everything": {
                 "action": "https://bird-rotterdam.cdn.prismic.io/api/v2/documents/search"}}},
            {"results": events[:10], "total_results_size": 20,
             "next_page": "https://bird-rotterdam.cdn.prismic.io/api/v2/documents/search?page=2"},
            {"results": events[10:], "total_results_size": 20, "next_page": None},
        ]
        result = scrape_bird()
        self.assertEqual(len(result), 19)
        self.assertTrue(all(x["source"] == "BIRD" for x in result))
        self.assertEqual(fake_request.call_count, 3)


if __name__ == "__main__":
    unittest.main()
