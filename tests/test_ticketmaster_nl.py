import unittest
from datetime import date
from scrapers.ticketmaster_nl import (
    event_to_concert, merge_ticketmaster, scrape_ticketmaster_nl,
    _same_performance, _fetch_range,
)


def event(name="Papa Roach", when="2026-11-11", venue="RTM Stage - Rotterdam Ahoy",
          city="Rotterdam", country="NL", segment="Music",
          url="https://www.ticketmaster.nl/event/papa-roach-tickets/123",
          tm="20:00:00", status="onsale"):
    return {
        "type": "event", "name": name, "url": url,
        "classifications": [{"segment": {"name": segment, "id": "KZFzniwnSyZfZ7v7nJ" if segment == "Music" else "abc"}}],
        "dates": {"start": {"localDate": when, "localTime": tm}, "status": {"code": status}},
        "_embedded": {"venues": [{"name": venue, "city": {"name": city},
                                  "country": {"countryCode": country}}]},
    }


class TicketmasterTests(unittest.TestCase):
    def test_only_netherlands_music_and_valid_live_dates(self):
        good = event()
        self.assertEqual(event_to_concert(good, today="2026-10-10")["city"], "Rotterdam")
        self.assertIsNone(event_to_concert(event(country="BE"), today="2026-10-10"))
        self.assertIsNone(event_to_concert(event(segment="Sports"), today="2026-10-10"))
        self.assertIsNone(event_to_concert(event(when="2026-10-09"), today="2026-10-10"))
        self.assertIsNone(event_to_concert(event(status="cancelled"), today="2026-10-10"))
        self.assertIsNone(event_to_concert(event(url="https://www.ticketmaster.be/event/a"), today="2026-10-10"))

    def test_no_premium_or_vip_ticket_products(self):
        for name in ["Papa Roach | Premium Seats", "Papa Roach VIP Package",
                     "Ziggo Dome Parking", "Papa Roach Platinum tickets",
                     "Papa Roach AFAS Live Loge", "Papa Roach Meet & Greet"]:
            with self.subTest(name=name):
                self.assertIsNone(event_to_concert(event(name=name), today="2026-10-10"))
        self.assertIsNotNone(event_to_concert(event(name="Pinkpop 2027",
                                                    venue="Megaland", city="Landgraaf",
                                                    when="2027-06-18"), today="2026-10-10"))

    def test_dutch_festival_classified_outside_music_is_included(self):
        bospop = event(name="Bospop 2027 - weekend",
                       when="2027-07-09", venue="Bospop Festivalterrein",
                       city="Weert", segment="Festival",
                       url="https://www.ticketmaster.nl/event/bospop-2027-tickets/100")
        self.assertIsNotNone(event_to_concert(bospop, today="2026-10-10"))
        # Unknown foreign festival titles are not silently classified as music.
        self.assertIsNone(event_to_concert(event(name="Local Tech Conference",
                                                  segment="Festival"), today="2026-10-10"))

    def test_concert_in_other_nl_city_is_included(self):
        ziggo = event(name="Foo Fighters", when="2027-06-21",
                      venue="Ziggo Dome", city="Amsterdam",
                      url="https://www.ticketmaster.nl/event/foo-fighters-tickets/123")
        self.assertEqual(event_to_concert(ziggo, today="2026-10-10")["venue"], "Ziggo Dome")

    def test_official_venue_wins_ticketmaster_duplicate(self):
        old = {"artist": "Papa Roach", "date": "2026-11-11",
               "venue": "Rotterdam Ahoy", "city": "Rotterdam",
               "source": "MOJO", "url": "https://official.example/papa"}
        tm = event_to_concert(event(name="Papa Roach - Rise Of The Roach Tour 2026"),
                              today="2026-10-10")
        added, duplicate_count = merge_ticketmaster([old], [tm])
        self.assertEqual(added, [])
        self.assertEqual(duplicate_count, 1)
        # Different days are always separate; two gigs in same place can exist.
        day2 = dict(tm, date="2026-11-12")
        not_same_artist = dict(tm, artist="Other Band")
        added, duplicate_count = merge_ticketmaster([old], [day2, not_same_artist])
        self.assertEqual(len(added), 2)
        self.assertEqual(duplicate_count, 0)

    def test_existing_pop_podium_and_main_room_are_not_double_listed(self):
        official = {
            "artist": "Band A", "date": "2027-03-22",
            "city": "Amsterdam", "venue": "Paradiso",
            "source": "Paradiso", "url": "https://www.paradiso.nl/a"
        }
        ticketmaster = {
            "artist": "Band A", "date": "2027-03-22",
            "city": "Amsterdam", "venue": "Paradiso Grote Zaal",
            "source": "Ticketmaster NL",
            "url": "https://www.ticketmaster.nl/event/a"
        }
        added, repeats = merge_ticketmaster([official], [ticketmaster])
        self.assertEqual((len(added), repeats), (0, 1))

    def test_same_artist_same_city_different_venue_stays_separate(self):
        old = {"artist": "Foo Fighters", "date": "2027-02-04", "city": "Amsterdam", "venue": "Ziggo Dome"}
        candidate = dict(old, venue="AFAS Live")
        self.assertFalse(_same_performance(old, candidate))

    def test_missing_api_key_does_not_break_previous_sources(self):
        self.assertEqual(scrape_ticketmaster_nl(api_key=""), [])

    def test_api_is_filtered_by_country_and_paginated_without_deep_paging(self):
        calls = []
        def getter(params, api_key):
            calls.append(params)
            if params.get("keyword"):
                return {"page": {"totalElements": 0, "totalPages": 0}}
            if params.get("page", 0) == 0:
                return {"page": {"totalElements": 2, "totalPages": 2, "number": 0},
                        "_embedded": {"events": [event()]}}
            return {"page": {"totalElements": 2, "totalPages": 2, "number": 1},
                    "_embedded": {"events": [event(name="Bospop 2027", when="2027-05-21",
                                                    venue="Bospop", city="Weert",
                                                    url="https://www.ticketmaster.nl/event/bospop-2027-tickets/abc")]}}
        result = _fetch_range(date(2026, 11, 1), date(2026, 12, 1), "test_key", getter=getter)
        self.assertEqual(len(result), 2)
        self.assertTrue(all(p["countryCode"] == "NL" for p in calls))
        self.assertEqual([p["page"] for p in calls], [0, 1])


if __name__ == "__main__":
    unittest.main()
