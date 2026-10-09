import unittest
from scrapers.discovery import attach_first_found


def event(artist, url, date="2026-12-10", source="Rotown", city="Rotterdam"):
    return dict(artist=artist, url=url, date=date, source=source, city=city)


class FirstDiscoveryTests(unittest.TestCase):
    def test_existing_legacy_events_are_not_mistakenly_new(self):
        prev = [event("Old", "https://example.nl/old")]
        incoming = [event("Old", "https://example.nl/old")]
        attach_first_found(incoming, prev, 5000)
        self.assertEqual(incoming[0]["firstFound"], 0)

    def test_new_shows_receive_one_timestamp_and_preserve_it(self):
        old = [event("A", "https://example.nl/a")]
        events = [event("A", "https://example.nl/a"), event("B", "https://example.nl/b")]
        attach_first_found(events, old, 100000)
        self.assertEqual([c["firstFound"] for c in events], [0, 100000])
        next_run = [event("A", "https://example.nl/a"), event("B", "https://example.nl/b")]
        attach_first_found(next_run, events, 300000)
        self.assertEqual([c["firstFound"] for c in next_run], [0, 100000])

    def test_url_change_does_not_mark_same_concert_new(self):
        prev = [dict(event("Artist", "https://example.nl/old"), firstFound=50000)]
        changed = [event("Artist", "https://example.nl/new")]
        attach_first_found(changed, prev, 70000)
        self.assertEqual(changed[0]["firstFound"], 50000)

    def test_different_dates_are_separate_concerts(self):
        prev = [dict(event("Artist", "https://example.nl/old"), firstFound=50000)]
        changed = [event("Artist", "https://example.nl/new", date="2026-12-11")]
        attach_first_found(changed, prev, 70000)
        self.assertEqual(changed[0]["firstFound"], 70000)


if __name__ == "__main__":
    unittest.main()
