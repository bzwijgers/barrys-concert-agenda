import unittest
from audit.merge_published_ticketswap import preserve_ticket_links

class PreserveTicketSwapLinks(unittest.TestCase):
    def test_full_scrape_cannot_erase_newer_known_link(self):
        published = [{"url": "https://example.org/show/", "date": "2027-04-21",
                      "ticketSwapUrl": "https://www.ticketswap.nl/concert-tickets/show-2027-04-21-Cabc"}]
        generated = [{"url": "HTTPS://EXAMPLE.ORG/SHOW", "date": "2027-04-21",
                      "ticketSwapUrl": ""}]
        changed, _, protected = preserve_ticket_links(generated, published)
        self.assertEqual((changed,protected), (1,1))
        self.assertEqual(generated[0]["ticketSwapUrl"], published[0]["ticketSwapUrl"])

    def test_other_date_does_not_inherit_wrong_ticket_url(self):
        published = [{"url": "https://example.org/show", "date": "2027-04-21",
                      "ticketSwapUrl": "https://www.ticketswap.nl/concert-tickets/show"}]
        generated = [{"url": "https://example.org/show", "date": "2027-04-22",
                      "ticketSwapUrl": ""}]
        changed, _, _ = preserve_ticket_links(generated, published)
        self.assertEqual(changed, 0)
        self.assertEqual(generated[0]["ticketSwapUrl"], "")

    def test_keep_new_links_for_other_shows(self):
        published = [{"url": "https://example.org/a", "date": "2027-04-21",
                      "ticketSwapUrl": "https://www.ticketswap.nl/a"}]
        generated = [{"url": "https://example.org/b", "date": "2027-04-22",
                      "ticketSwapUrl": "https://www.ticketswap.nl/b"}]
        preserve_ticket_links(generated, published)
        self.assertEqual(generated[0]["ticketSwapUrl"], "https://www.ticketswap.nl/b")

if __name__ == "__main__":
    unittest.main()
