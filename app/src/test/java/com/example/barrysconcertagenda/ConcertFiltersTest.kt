package com.example.barrysconcertagenda

import org.junit.Assert.assertEquals
import org.junit.Test

class ConcertFiltersTest {
    private fun concert(name: String, archived: Boolean, attending: Boolean = false) =
        Concert(artist = name, venue = "Testzaal", city = "Rotterdam",
            country = "NL", date = "2026-01-01", url = "https://example.com/$name",
            archived = archived, isAttending = attending)

    @Test
    fun archiveIncludesPastConcertsWithoutTickets() {
        val pastWithoutTicket = concert("PastNoTicket", true)
        val pastWithTicket = concert("PastWithTicket", true, true)
        val upcomingWithTicket = concert("Upcoming", false, true)

        assertEquals(
            listOf(pastWithoutTicket, pastWithTicket),
            archiveConcerts(listOf(pastWithoutTicket, pastWithTicket, upcomingWithTicket))
        )
    }

    @Test
    fun archiveIsEmptyWhenNoPastConcertsAreStored() {
        assertEquals(emptyList<Concert>(), archiveConcerts(listOf(concert("Future", false))))
    }
}
