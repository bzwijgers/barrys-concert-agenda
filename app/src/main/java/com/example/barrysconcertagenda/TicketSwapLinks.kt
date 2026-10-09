package com.example.barrysconcertagenda

/**
 * V3 only shows an existing, direct, event-specific TicketSwap URL. No
 * unverified search result or TicketSwap homepage is presented as a match.
 */
internal object TicketSwapLinks {
    private const val APERS =
        "https://www.ticketswap.nl/concert-tickets/maladroit-rotterdam-rotown-2026-10-09-CbSFR53UXMVxNKodxWTdf"
    private const val EXCELSIOR =
        "https://www.ticketswap.nl/concert-tickets/30-jaar-excelsior-recordings-amsterdam-tolhuistuin-2026-12-27-CbhnzqXEdczxvu7WzXVv9"

    private const val LEMONHEADS =
        "https://www.ticketswap.nl/concert-tickets/the-lemonheads-utrecht-tivolivredenburg-2026-10-15-CaQ2oHCb2akaFrGijoRzL"
    private const val DEVIL_WEAR_PRADA =
        "https://www.ticketswap.nl/concert-tickets/the-devil-wears-prada-eindhoven-effenaar-2026-10-10-CWB3YG3uLQCD7ALgTYYxv"
    private const val ROBERT_JON_WEERT =
        "https://www.ticketswap.nl/concert-tickets/robert-jon-the-wreck-weert-poppodium-de-bosuil-2026-10-09-CZps3zUdhSJuXrEnxbCRp"

    // Both exceptions identify the complete event (date, venue, source URL).
    // The Apers are a co-headliner; their band name is not in the URL slug.
    internal fun directUrl(concert: Concert): String {
        val original = concert.url.trimEnd('/')
        if (concert.date == "2026-10-09" &&
            concert.artist.equals("The Apers", ignoreCase = true) &&
            concert.venue.equals("Rotown", ignoreCase = true) &&
            original == "https://www.rotown.nl/agenda/the-apers-1") return APERS
        if (concert.date == "2026-12-27" &&
            concert.artist.equals("30 Jaar Excelsior Recordings", ignoreCase = true) &&
            concert.venue.equals("Tolhuistuin", ignoreCase = true) &&
            original == "https://www.paradiso.nl/nl/programma/30-jaar-excelsior-recordings/2902321") return EXCELSIOR

        // These public TicketSwap event pages were checked against their
        // exact artist, venue, city and date on 9 October 2026.
        if (concert.date == "2026-10-15" &&
            concert.artist.equals("The Lemonheads", ignoreCase = true) &&
            concert.city.equals("Utrecht", ignoreCase = true) &&
            concert.venue.contains("TivoliVredenburg", ignoreCase = true)) return LEMONHEADS
        if (concert.date == "2026-10-10" &&
            concert.artist.equals("The Devil Wears Prada", ignoreCase = true) &&
            concert.city.equals("Eindhoven", ignoreCase = true) &&
            concert.venue.contains("Effenaar", ignoreCase = true)) return DEVIL_WEAR_PRADA
        if (concert.date == "2026-10-09" &&
            concert.artist.equals("Robert Jon & The Wreck", ignoreCase = true) &&
            concert.city.equals("Weert", ignoreCase = true) &&
            concert.venue.contains("Bosuil", ignoreCase = true)) return ROBERT_JON_WEERT

        val candidate = concert.ticketSwapUrl.trim()
        return candidate.takeIf { TicketSwapSearch.exactMatch(concert, it) }.orEmpty()
    }
}
