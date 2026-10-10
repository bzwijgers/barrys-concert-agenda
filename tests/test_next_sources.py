import unittest
from scrapers.next_sources import CANDIDATES, validate_registry

class PlannedSourceTests(unittest.TestCase):
    def test_registry(self):
        self.assertTrue(validate_registry())
        self.assertEqual(sum(c.country == "NL" for c in CANDIDATES), 23)
        self.assertEqual(sum(c.country == "BE" and c.kind == "venue" for c in CANDIDATES), 5)
        self.assertEqual(sum(c.kind == "promoter" for c in CANDIDATES), 1)

    def test_excluded_sources(self):
        names = {c.name.casefold() for c in CANDIDATES}
        self.assertIn("fluor", names)
        self.assertNotIn("cinetol", names)
        self.assertIn("sound dog", names)
        self.assertIn("musicon", names)
        self.assertIn("hall of fame", names)
        self.assertIn("willem twee poppodium", names)
        self.assertIn("nobel", names)

if __name__ == "__main__":
    unittest.main()
