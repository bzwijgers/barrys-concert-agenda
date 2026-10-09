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
