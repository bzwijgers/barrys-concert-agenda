package com.example.barrysconcertagenda

import java.time.LocalDate
import java.time.YearMonth

/**
 * Keep V3 list selections in pure functions so that filters can be tested
 * separately from Android's UI.
 */
object BackstageSelectors {
    fun discover(all: List<Concert>, filter: String): List<Concert> =
        all.filter { concert ->
            !concert.archived && when (filter) {
                "new" -> concert.isNew
                "rotterdam" -> concert.city.equals("Rotterdam", ignoreCase = true)
                "belgium" -> concert.country.equals("BE", ignoreCase = true) ||
                    concert.country.equals("Belgium", ignoreCase = true) ||
                    concert.country.equals("België", ignoreCase = true)
                "club" -> concert.clubCard
                else -> true
            }
        }

    /**
     * On a newly installed app, historical discovery timestamps are unknown.
     * Do not label old concerts as "new"; show upcoming concerts as an
     * explicitly labelled fallback so the Discover tab is never empty.
     */
    fun discoverOrUpcoming(all: List<Concert>, filter: String): List<Concert> {
        val matching = discover(all, filter)
        return if (filter == "new" && matching.isEmpty()) discover(all, "all")
            else matching
    }

    fun mine(all: List<Concert>, section: Int): List<Concert> =
        all.filter {
            when (section) {
                2 -> it.isFavorite && !it.archived
                5 -> it.isAttending && it.archived
                else -> it.isAttending && !it.archived
            }
        }

    /**
     * Match horizontal swipes to the six visible navigation items:
     * Home, Discover, Agenda, Tickets, Favorites, and More.
     */
    fun swipeTarget(selectedTab: Int, mySection: Int, towardsNext: Boolean): Pair<Int, Int>? {
        val order = listOf(9, 10, 1, 3, 2, 8)
        val active = when (selectedTab) {
            11 -> when (mySection) {
                2 -> 2
                3 -> 3
                else -> 8
            }
            4, 5, 7, 8 -> 8
            else -> selectedTab
        }
        val position = order.indexOf(active)
        if (position == -1) return null
        val next = position + (if (towardsNext) 1 else -1)
        if (next !in order.indices) return null
        return when (order[next]) {
            3 -> 11 to 3
            2 -> 11 to 2
            else -> order[next] to mySection
        }
    }

    /**
     * A date selected from the calendar means the rest of the agenda,
     * including the selected day. The end date is optional.
     */
    fun withinDateRange(concert: Concert, from: LocalDate?, to: LocalDate?): Boolean {
        if (from == null && to == null) return true
        val eventDate = try { LocalDate.parse(concert.date) } catch (_: Exception) { return false }
        return (from == null || !eventDate.isBefore(from)) &&
            (to == null || !eventDate.isAfter(to))
    }

    /**
     * The "New" fallback should match the chronological "All" agenda.
     * Only genuinely newly discovered shows are sorted by discovery time.
     */
    fun orderDiscovery(concerts: List<Concert>, filter: String, noNew: Boolean): List<Concert> {
        return if (filter == "new" && !noNew) concerts.sortedByDescending { it.firstFound }
            else concerts
    }

    fun calendar(
        concerts: List<Concert>,
        month: YearMonth,
        date: LocalDate?
    ): List<Concert> =
        concerts.filter { concert ->
            val parsed = try { LocalDate.parse(concert.date) } catch (_: Exception) { null }
            parsed != null && YearMonth.from(parsed) == month && (date == null || parsed == date)
        }
}
