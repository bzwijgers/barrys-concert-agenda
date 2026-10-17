import unittest
from audit.merge_published_discovery import merge


class MergePublishedDiscoveryTests(unittest.TestCase):
    def test_latest_discovery_survives_older_scrape(self):
        candidate = [{"url": "https://example.com/a/", "date": "2027-01-01", "firstFound": 300}]
        previous = [{"url": "https://example.com/a", "date": "2027-01-01", "firstFound": 200}]
        self.assertEqual(merge(previous, candidate), 1)
        self.assertEqual(candidate[0]["firstFound"], 200)

    def test_does_not_override_earlier_discovery(self):
        candidate = [{"url": "https://example.com/a", "date": "2027-01-01", "firstFound": 100}]
        previous = [{"url": "https://example.com/a", "date": "2027-01-01", "firstFound": 200}]
        self.assertEqual(merge(previous, candidate), 0)

    def test_never_transfer_to_different_performance_date(self):
        candidate = [{"url": "https://example.com/a", "date": "2027-01-02", "firstFound": 300}]
        previous = [{"url": "https://example.com/a", "date": "2027-01-01", "firstFound": 200}]
        self.assertEqual(merge(previous, candidate), 0)

    def test_legacy_zero_does_not_override_positive_timestamp(self):
        candidate = [{"url": "https://example.com/a", "date": "2027-01-01", "firstFound": 300}]
        previous = [{"url": "https://example.com/a", "date": "2027-01-01", "firstFound": 0}]
        self.assertEqual(merge(previous, candidate), 0)

    def test_latest_positive_restores_missing_timestamp(self):
        candidate = [{"url": "https://example.com/a", "date": "2027-01-01", "firstFound": 0}]
        previous = [{"url": "https://example.com/a", "date": "2027-01-01", "firstFound": 200}]
        self.assertEqual(merge(previous, candidate), 1)
        self.assertEqual(candidate[0]["firstFound"], 200)
