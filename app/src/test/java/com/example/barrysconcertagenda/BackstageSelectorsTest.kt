package com.example.barrysconcertagenda

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.time.LocalDate
import java.time.YearMonth

class BackstageSelectorsTest {
    private val shows = listOf(
        Concert(artist="Rotown artist",venue="Rotown",city="Rotterdam",country="NL",
            date="2026-10-22",isNew=false,clubCard=true),
        Concert(artist="Belgian artist",venue="Trix",city="Antwerpen",country="BE",
            date="2026-10-25",isNew=true,isFavorite=true),
        Concert(artist="Ticket concert",venue="013",city="Tilburg",country="NL",
            date="2026-11-03",isAttending=true),
        Concert(artist="Archived concert",venue="Paradiso",city="Amsterdam",country="NL",
            date="2026-08-21",archived=true,isAttending=true)
    )
    @Test fun discoverFiltersActuallyReturnDistinctSubsets() {
        assertEquals(3, BackstageSelectors.discover(shows,"all").size)
        assertEquals(listOf("Belgian artist"),BackstageSelectors.discover(shows,"new").map{it.artist})
        assertEquals(listOf("Rotown artist"),BackstageSelectors.discover(shows,"rotterdam").map{it.artist})
        assertEquals(listOf("Rotown artist"),BackstageSelectors.discover(shows,"club").map{it.artist})
        assertEquals(listOf("Belgian artist"),BackstageSelectors.discover(shows,"belgium").map{it.artist})
    }
    @Test fun emptyNewTabShowsUpcomingWithoutPretendingTheyAreNew() {
        val baseline = shows.map { it.copy(isNew = false) }
        val upcoming = BackstageSelectors.discoverOrUpcoming(baseline, "new")
        assertEquals(3, upcoming.size)
        assertTrue(upcoming.all { !it.archived && !it.isNew })
        // If actual new shows arrive, display only those.
        assertEquals(
            listOf("Belgian artist"),
            BackstageSelectors.discoverOrUpcoming(shows, "new").map { it.artist }
        )
    }

    @Test fun myConcertsKeepTicketsFavoritesAndArchiveSeparate() {
        assertEquals(listOf("Belgian artist"),BackstageSelectors.mine(shows,2).map{it.artist})
        assertEquals(listOf("Ticket concert"),BackstageSelectors.mine(shows,3).map{it.artist})
        assertEquals(listOf("Archived concert"),BackstageSelectors.mine(shows,5).map{it.artist})
    }
    @Test fun monthViewIsDifferentFromDaySelection() {
        val upcoming=BackstageSelectors.discover(shows,"all")
        assertEquals(2,BackstageSelectors.calendar(upcoming,YearMonth.of(2026,10),null).size)
        assertEquals(1,BackstageSelectors.calendar(upcoming,YearMonth.of(2026,10),LocalDate.of(2026,10,22)).size)
        assertTrue(BackstageSelectors.calendar(upcoming,YearMonth.of(2026,12),null).isEmpty())
    }
}
