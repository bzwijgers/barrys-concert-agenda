import unittest
from audit.publication_guard import check


def events(source, count, day="2026-12-01"):
    return [{"source": source, "date": day} for _ in range(count)]


class PublicationGuardTests(unittest.TestCase):
    def test_same_coverage(self):
        self.assertEqual(check(events("Rotown", 50), events("Rotown", 50), "2026-10-17"), (50, 50))

    def test_partial_source_loss_blocked(self):
        old = events("Rotown", 50) + events("013", 50)
        new = events("Rotown", 10) + events("013", 50)
        with self.assertRaisesRegex(ValueError, "Rotown"):
            check(old, new, "2026-10-17")

    def test_total_loss_blocked(self):
        with self.assertRaisesRegex(ValueError, "TOTAL"):
            check(events("Rotown", 10) + events("013", 10),
                  events("Rotown", 7) + events("013", 5), "2026-10-17")

    def test_expired_shows_not_counted(self):
        old = events("Rotown", 60, "2026-10-01") + events("Rotown", 20)
        self.assertEqual(check(old, events("Rotown", 20), "2026-10-17"), (20, 20))

    def test_new_sources_allowed(self):
        self.assertEqual(check(events("Rotown", 20),
                               events("Rotown", 20) + events("New venue", 30),
                               "2026-10-17"), (20, 50))


if __name__ == "__main__":
    unittest.main()
