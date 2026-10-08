import unittest
from unittest.mock import patch

from scrapers.common import download_page_retry


class EmptyResponseRetryTests(unittest.TestCase):
    def test_empty_http_200_gets_retried(self):
        with patch("scrapers.common.download_page", side_effect=["", "<html>concert</html>"]) as download, \
             patch("scrapers.common.time.sleep"):
            actual = download_page_retry("https://www.paradiso.nl/nl/programma/test/1234")
        self.assertEqual(actual, "<html>concert</html>")
        self.assertEqual(download.call_count, 2)
        self.assertIn("_bca_retry=", download.call_args_list[1].args[0])

    def test_persistent_blank_page_raises(self):
        with patch("scrapers.common.download_page", return_value="   ") as download, \
             patch("scrapers.common.time.sleep"):
            with self.assertRaisesRegex(ValueError, "Lege HTML-response"):
                download_page_retry("https://www.paradiso.nl/nl/programma/test/1234")
        self.assertEqual(download.call_count, 3)


if __name__ == "__main__":
    unittest.main()
