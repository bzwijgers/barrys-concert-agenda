package com.example.barrysconcertagenda

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class TicketSwapLinksTest {
    private fun show(
        artist: String = "Robert Jon & The Wreck",
        venue: String = "TivoliVredenburg",
        city: String = "Utrecht",
        date: String = "2026-10-10",
        url: String = "https://www.tivolivredenburg.nl/example",
        ticketSwapUrl: String = ""
    ) = Concert(
        artist = artist, venue = venue, city = city, country = "NL",
        date = date, url = url, ticketSwapUrl = ticketSwapUrl
    )

    @Test fun acceptsSameArtistDateAndCity() {
        val link = "https://www.ticketswap.nl/concert-tickets/robert-jon-the-wreck-utrecht-2026-10-10-Ab123"
        assertEquals(link, TicketSwapLinks.directUrl(show(ticketSwapUrl = link)))
    }

    @Test fun refusesHomepageWrongHostsAndHttp() {
        listOf(
            "https://www.ticketswap.nl/",
            "https://www.ticketswap.nl/artist/robert-jon",
            "https://www.ticketswap.nl.evil.example/concert-tickets/robert-jon-the-wreck-utrecht-2026-10-10-Ab123",
            "http://www.ticketswap.nl/concert-tickets/robert-jon-the-wreck-utrecht-2026-10-10-Ab123"
        ).forEach { bad ->
            assertEquals(bad, "", TicketSwapLinks.directUrl(show(ticketSwapUrl = bad)))
        }
    }

    @Test fun refusesOtherEventOnSameNightAndAtSameVenue() {
        val wrongArtist = "https://www.ticketswap.nl/concert-tickets/robert-jon-the-friends-utrecht-2026-10-10-Ab123"
        assertFalse(TicketSwapSearch.exactMatch(show(), wrongArtist))
        val wrongDate = "https://www.ticketswap.nl/concert-tickets/robert-jon-the-wreck-utrecht-2026-10-11-Ab123"
        assertFalse(TicketSwapSearch.exactMatch(show(), wrongDate))
        val wrongPlace = "https://www.ticketswap.nl/concert-tickets/robert-jon-the-wreck-berlin-2026-10-10-Ab123"
        assertFalse(TicketSwapSearch.exactMatch(show(), wrongPlace))
    }

    @Test fun verifiedCoHeadlinerHasDeliberateException() {
        val apers = show(
            artist = "The Apers",
            venue = "Rotown",
            city = "Rotterdam",
            date = "2026-10-09",
            url = "https://www.rotown.nl/agenda/the-apers-1"
        )
        assertTrue(TicketSwapLinks.directUrl(apers).contains("maladroit-rotterdam-rotown"))
        assertEquals("", TicketSwapLinks.directUrl(apers.copy(date = "2026-10-10")))
    }

    @Test fun verifiedExcelsiorLinkDoesNotMatchDifferentConcert() {
        val official = show(
            artist = "30 Jaar Excelsior Recordings",
            venue = "Tolhuistuin",
            city = "Amsterdam",
            date = "2026-12-27",
            url = "https://www.paradiso.nl/nl/programma/30-jaar-excelsior-recordings/2902321"
        )
        assertTrue(TicketSwapLinks.directUrl(official).contains("30-jaar-excelsior-recordings"))
        assertEquals("", TicketSwapLinks.directUrl(official.copy(venue = "Paradiso")))
    }
}
