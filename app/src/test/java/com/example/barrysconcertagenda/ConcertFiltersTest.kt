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

    private fun stored(name: String, date: String, favorite: Boolean = false, attending: Boolean = false) =
        StoredConcert(artist = name, venue = "Testzaal", city = "Rotterdam",
            country = "NL", date = date, time = "20:00", source = "Test",
            url = "https://example.com/$name", isFavorite = favorite, isAttending = attending)

    @Test
    fun removedUnmarkedFutureConcertIsNotRetained() {
        val removed = stored("removed", "2099-01-01")
        val saved = stored("saved", "2099-01-01", favorite = true)
        val ticket = stored("ticket", "2099-01-01", attending = true)
        val history = stored("history", "2020-01-01")
        val stillPublished = stored("published", "2099-01-01")
        val all = listOf(removed, saved, ticket, history, stillPublished)
        assertEquals(listOf(saved, ticket, history, stillPublished),
            retainedStoredConcerts(all, setOf(stillPublished.url), true))
    }

    @Test
    fun failedRefreshKeepsEverything() {
        val cached = listOf(stored("future", "2099-01-01"))
        assertEquals(cached, retainedStoredConcerts(cached, emptySet(), false))
    }
}
