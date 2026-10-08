package com.example.barrysconcertagenda

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class TicketSwapSearchTest {
    private val sample = Concert(
        artist = "Robert Jon & The Wreck",
        venue = "TivoliVredenburg",
        city = "Utrecht",
        country = "NL",
        date = "2026-10-10",
        source = "TivoliVredenburg",
        url = "https://example.com/robert-jon"
    )

    @Test
    fun acceptsExactConcertDateAndPlace() {
        assertTrue(TicketSwapSearch.exactMatch(
            sample,
            "https://www.ticketswap.nl/concert-tickets/robert-jon-the-wreck-utrecht-2026-10-10-Ab123"
        ))
    }

    @Test
    fun rejectsWrongDate() {
        assertFalse(TicketSwapSearch.exactMatch(
            sample,
            "https://www.ticketswap.nl/concert-tickets/robert-jon-the-wreck-utrecht-2026-10-11-Ab123"
        ))
    }

    @Test
    fun rejectsWrongCity() {
        assertFalse(TicketSwapSearch.exactMatch(
            sample,
            "https://www.ticketswap.nl/concert-tickets/robert-jon-the-wreck-berlin-2026-10-10-Ab123"
        ))
    }

    @Test
    fun rejectsOtherArtist() {
        assertFalse(TicketSwapSearch.exactMatch(
            sample,
            "https://www.ticketswap.nl/concert-tickets/random-band-utrecht-2026-10-10-Ab123"
        ))
    }
}
