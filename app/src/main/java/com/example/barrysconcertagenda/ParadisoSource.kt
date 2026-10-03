package com.example.barrysconcertagenda

import okhttp3.OkHttpClient
import okhttp3.Request
import java.time.LocalDate
import java.time.OffsetDateTime
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.Locale
import java.util.concurrent.TimeUnit
import kotlin.math.abs

data class ParadisoConcert(
    val artist: String,
    val date: String,
    val time: String,
    val venue: String = "Paradiso",
    val city: String = "Amsterdam",
    val country: String = "NL",
    val source: String = "Paradiso",
    val url: String
)

object ParadisoSource {

    private const val AGENDA_URL =
        "https://www.paradiso.nl/landing/concertagenda-paradiso/2069817"

    var diagnosticInfo: String =
        "Paradiso wordt gecontroleerd..."

    private val client =
        OkHttpClient.Builder()
            .connectTimeout(20, TimeUnit.SECONDS)
            .readTimeout(20, TimeUnit.SECONDS)
            .callTimeout(30, TimeUnit.SECONDS)
            .retryOnConnectionFailure(true)
            .build()

    fun getConcerts(): List<ParadisoConcert> {

        val diagnostic = StringBuilder()

        return try {

            val agendaHtml =
                downloadPage(AGENDA_URL)

            diagnostic.appendLine(
                "Concertagenda: OK"
            )

            val programUrls =
                findProgramUrls(agendaHtml)

            diagnostic.appendLine(
                "Concertlinks gevonden: ${programUrls.size}"
            )

            /*
             * Alle gevonden Paradiso-concerten verwerken.
             */
            val concertUrls =
                programUrls

            diagnostic.appendLine(
                "Concertpagina's te verwerken: ${concertUrls.size}"
            )

            val concerts =
                mutableListOf<ParadisoConcert>()

            var successCount = 0
            var failedCount = 0
            var pastCount = 0

            concertUrls.forEachIndexed { index, eventUrl ->

                try {

                    val html =
                        downloadPage(eventUrl)

                    val concert =
                        parseEvent(
                            html = html,
                            eventUrl = eventUrl
                        )

                    if (concert != null) {

                        val parsedDate =
                            parseDutchDate(
                                concert.date
                            )

                        if (
                            parsedDate == null ||
                            !parsedDate.isBefore(
                                LocalDate.now()
                            )
                        ) {

                            concerts.add(concert)
                            successCount++

                        } else {

                            pastCount++
                        }

                    } else {

                        failedCount++
                    }

                } catch (_: Exception) {

                    failedCount++
                }

                /*
                 * Iedere 10 pagina's een korte voortgang
                 * in de diagnose bewaren.
                 */
                if (
                    (index + 1) % 10 == 0 ||
                    index == concertUrls.lastIndex
                ) {

                    diagnosticInfo =
                        buildString {

                            appendLine(
                                "Concertagenda: OK"
                            )

                            appendLine(
                                "Concertlinks gevonden: ${programUrls.size}"
                            )

                            appendLine(
                                "Verwerkt: ${index + 1} / ${concertUrls.size}"
                            )

                            appendLine(
                                "Gelukt: $successCount"
                            )

                            appendLine(
                                "Mislukt: $failedCount"
                            )

                            appendLine(
                                "Voorbij: $pastCount"
                            )
                        }
                }
            }

            val uniqueConcerts =
                concerts.distinctBy {
                    normalizeUrl(it.url)
                }

            diagnostic.appendLine()
            diagnostic.appendLine(
                "Verwerkt: ${concertUrls.size}"
            )
            diagnostic.appendLine(
                "Gelukt: $successCount"
            )
            diagnostic.appendLine(
                "Mislukt: $failedCount"
            )
            diagnostic.appendLine(
                "Voorbij: $pastCount"
            )
            diagnostic.appendLine(
                "Unieke Paradiso concerten: ${uniqueConcerts.size}"
            )

            diagnosticInfo =
                diagnostic.toString()

            uniqueConcerts

        } catch (e: Exception) {

            diagnosticInfo =
                buildString {

                    appendLine(
                        "Paradiso concertagenda mislukt"
                    )

                    appendLine(
                        e.javaClass.simpleName
                    )

                    appendLine(
                        e.message ?: "Onbekende fout"
                    )
                }

            emptyList()
        }
    }

    private fun findProgramUrls(
        html: String
    ): List<String> {

        val cleanedHtml =
            html
                .replace("\\/", "/")
                .replace("\\u002F", "/")
                .replace("\\u002f", "/")
                .replace("\\u0026", "&")

        val urls =
            mutableListOf<String>()

        val absoluteRegex =
            Regex(
                """https://(?:www\.)?paradiso\.nl/nl/programma/[A-Za-z0-9_%+.\-]+/\d+""",
                RegexOption.IGNORE_CASE
            )

        absoluteRegex
            .findAll(cleanedHtml)
            .forEach { match ->

                urls.add(
                    match.value
                        .substringBefore("?")
                        .substringBefore("#")
                        .trimEnd('/')
                )
            }

        val relativeRegex =
            Regex(
                """/nl/programma/[A-Za-z0-9_%+.\-]+/\d+""",
                RegexOption.IGNORE_CASE
            )

        relativeRegex
            .findAll(cleanedHtml)
            .forEach { match ->

                urls.add(
                    "https://www.paradiso.nl" +
                            match.value
                                .substringBefore("?")
                                .substringBefore("#")
                                .trimEnd('/')
                )
            }

        return urls
            .filter {
                it.startsWith(
                    "https://www.paradiso.nl/nl/programma/",
                    ignoreCase = true
                )
            }
            .distinct()
    }

    private fun parseEvent(
        html: String,
        eventUrl: String
    ): ParadisoConcert? {

        val artist =
            extractArtist(html)

        if (artist.isBlank()) {
            return null
        }

        val isoDate =
            findBestDateCandidate(
                html = html,
                artist = artist
            )

        if (isoDate != null) {

            try {

                val localDateTime =
                    OffsetDateTime
                        .parse(isoDate)
                        .toInstant()
                        .atZone(
                            ZoneId.of(
                                "Europe/Amsterdam"
                            )
                        )

                val dateFormatter =
                    DateTimeFormatter.ofPattern(
                        "d MMMM yyyy",
                        Locale.forLanguageTag(
                            "nl-NL"
                        )
                    )

                val timeFormatter =
                    DateTimeFormatter.ofPattern(
                        "HH:mm"
                    )

                return ParadisoConcert(
                    artist = artist,
                    date =
                        localDateTime.format(
                            dateFormatter
                        ),
                    time =
                        localDateTime.format(
                            timeFormatter
                        ),
                    venue =
                        extractVenue(html),
                    url = eventUrl
                )

            } catch (_: Exception) {
                // Probeer hieronder de zichtbare datum.
            }
        }

        val visibleDate =
            extractVisibleDate(html)
                ?: return null

        val visibleTime =
            extractVisibleTime(html)

        return ParadisoConcert(
            artist = artist,
            date = visibleDate,
            time = visibleTime,
            venue = extractVenue(html),
            url = eventUrl
        )
    }

    private fun extractArtist(
        html: String
    ): String {

        val titleRegex =
            Regex(
                """<title[^>]*>(.*?)</title>""",
                setOf(
                    RegexOption.IGNORE_CASE,
                    RegexOption.DOT_MATCHES_ALL
                )
            )

        val rawTitle =
            titleRegex
                .find(html)
                ?.groupValues
                ?.getOrNull(1)

        if (!rawTitle.isNullOrBlank()) {

            var artist =
                decodeHtml(
                    stripTags(rawTitle)
                )

            artist =
                artist.replace(
                    Regex(
                        """\s*\|\s*Paradiso.*$""",
                        RegexOption.IGNORE_CASE
                    ),
                    ""
                )

            artist =
                artist.replace(
                    Regex(
                        """\s*[-–—]\s*Paradiso.*$""",
                        RegexOption.IGNORE_CASE
                    ),
                    ""
                )

            artist =
                artist.trim()

            if (artist.isNotBlank()) {
                return artist
            }
        }

        val h1Regex =
            Regex(
                """<h1[^>]*>(.*?)</h1>""",
                setOf(
                    RegexOption.IGNORE_CASE,
                    RegexOption.DOT_MATCHES_ALL
                )
            )

        val h1 =
            h1Regex
                .find(html)
                ?.groupValues
                ?.getOrNull(1)
                ?: return ""

        return decodeHtml(
            stripTags(h1)
        ).trim()
    }

    private fun extractVenue(
        html: String
    ): String {

        val text =
            htmlToText(html)

        val venues =
            listOf(
                "Tolhuistuin",
                "Bitterzoet",
                "Cinetol",
                "Zonnehuis",
                "Vondelkerk",
                "De Duif",
                "Parallel",
                "Skatecafe"
            )

        venues.forEach { venue ->

            if (
                text.contains(
                    "In $venue",
                    ignoreCase = true
                )
            ) {
                return venue
            }
        }

        return "Paradiso"
    }

    private fun findBestDateCandidate(
        html: String,
        artist: String
    ): String? {

        val dateRegex =
            Regex(
                """20\d{2}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})"""
            )

        val candidates =
            dateRegex
                .findAll(html)
                .toList()

        if (candidates.isEmpty()) {
            return null
        }

        val artistPositions =
            mutableListOf<Int>()

        var startIndex = 0

        while (startIndex < html.length) {

            val position =
                html.indexOf(
                    string = artist,
                    startIndex = startIndex,
                    ignoreCase = true
                )

            if (position < 0) {
                break
            }

            artistPositions.add(position)

            startIndex =
                position +
                        artist.length.coerceAtLeast(1)
        }

        if (artistPositions.isNotEmpty()) {

            return candidates
                .minByOrNull { dateMatch ->

                    artistPositions.minOf { artistPosition ->

                        abs(
                            dateMatch.range.first -
                                    artistPosition
                        )
                    }
                }
                ?.value
        }

        return candidates
            .firstOrNull()
            ?.value
    }

    private fun extractVisibleDate(
        html: String
    ): String? {

        val text =
            htmlToText(html)

        val months =
            "januari|februari|maart|april|mei|juni|" +
                    "juli|augustus|september|oktober|november|december"

        val regex =
            Regex(
                """(?:maandag|dinsdag|woensdag|donderdag|vrijdag|zaterdag|zondag)?\s*(\d{1,2})\s+($months)""",
                RegexOption.IGNORE_CASE
            )

        val match =
            regex.find(text)
                ?: return null

        val day =
            match.groupValues[1]

        val month =
            match.groupValues[2]
                .lowercase()

        val current =
            LocalDate.now()

        val monthNumber =
            monthNumber(month)
                ?: return null

        var year =
            current.year

        val candidate =
            try {

                LocalDate.of(
                    year,
                    monthNumber,
                    day.toInt()
                )

            } catch (_: Exception) {

                return null
            }

        if (
            candidate.isBefore(
                current.minusDays(7)
            )
        ) {
            year++
        }

        return "$day $month $year"
    }

    private fun extractVisibleTime(
        html: String
    ): String {

        val text =
            htmlToText(html)

        val mainProgramRegex =
            Regex(
                """Hoofdprogramma\s*:\s*(\d{1,2}:\d{2})""",
                RegexOption.IGNORE_CASE
            )

        val mainProgram =
            mainProgramRegex
                .find(text)
                ?.groupValues
                ?.getOrNull(1)

        if (!mainProgram.isNullOrBlank()) {
            return mainProgram
        }

        val doorsRegex =
            Regex(
                """Zaal\s+open\s*:\s*(\d{1,2}:\d{2})""",
                RegexOption.IGNORE_CASE
            )

        val doors =
            doorsRegex
                .find(text)
                ?.groupValues
                ?.getOrNull(1)

        if (!doors.isNullOrBlank()) {
            return doors
        }

        val genericTimeRegex =
            Regex(
                """\b([01]?\d|2[0-3]):[0-5]\d\b"""
            )

        return genericTimeRegex
            .find(text)
            ?.value
            ?: ""
    }

    private fun parseDutchDate(
        date: String
    ): LocalDate? {

        return try {

            LocalDate.parse(
                date.lowercase(),
                DateTimeFormatter.ofPattern(
                    "d MMMM yyyy",
                    Locale.forLanguageTag(
                        "nl-NL"
                    )
                )
            )

        } catch (_: Exception) {

            null
        }
    }

    private fun monthNumber(
        month: String
    ): Int? {

        return when (month.lowercase()) {

            "januari" -> 1
            "februari" -> 2
            "maart" -> 3
            "april" -> 4
            "mei" -> 5
            "juni" -> 6
            "juli" -> 7
            "augustus" -> 8
            "september" -> 9
            "oktober" -> 10
            "november" -> 11
            "december" -> 12

            else -> null
        }
    }

    private fun htmlToText(
        html: String
    ): String {

        return decodeHtml(
            html
                .replace(
                    Regex(
                        """<script[^>]*>.*?</script>""",
                        setOf(
                            RegexOption.IGNORE_CASE,
                            RegexOption.DOT_MATCHES_ALL
                        )
                    ),
                    " "
                )
                .replace(
                    Regex(
                        """<style[^>]*>.*?</style>""",
                        setOf(
                            RegexOption.IGNORE_CASE,
                            RegexOption.DOT_MATCHES_ALL
                        )
                    ),
                    " "
                )
                .replace(
                    Regex("""<[^>]+>"""),
                    " "
                )
                .replace(
                    Regex("""\s+"""),
                    " "
                )
        )
    }

    private fun stripTags(
        text: String
    ): String {

        return text.replace(
            Regex("""<[^>]+>"""),
            ""
        )
    }

    private fun decodeHtml(
        text: String
    ): String {

        return text
            .replace("&amp;", "&")
            .replace("&quot;", "\"")
            .replace("&#39;", "'")
            .replace("&#x27;", "'")
            .replace("&apos;", "'")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
            .replace("&nbsp;", " ")
            .replace("&#x2F;", "/")
            .trim()
    }

    private fun normalizeUrl(
        url: String
    ): String {

        return url
            .trim()
            .trimEnd('/')
            .lowercase()
    }

    private fun downloadPage(
        address: String
    ): String {

        var lastException: Exception? = null

        repeat(3) { attempt ->

            try {

                val request =
                    Request.Builder()
                        .url(address)
                        .header(
                            "User-Agent",
                            "Mozilla/5.0 (Linux; Android 15) " +
                                    "AppleWebKit/537.36 " +
                                    "Chrome/153.0 Mobile Safari/537.36"
                        )
                        .header(
                            "Accept",
                            "text/html,application/xhtml+xml," +
                                    "application/xml;q=0.9,*/*;q=0.8"
                        )
                        .header(
                            "Accept-Language",
                            "nl-NL,nl;q=0.9,en;q=0.8"
                        )
                        .header(
                            "Cache-Control",
                            "no-cache"
                        )
                        .build()

                client
                    .newCall(request)
                    .execute()
                    .use { response ->

                        if (!response.isSuccessful) {

                            throw Exception(
                                "HTTP ${response.code} bij $address"
                            )
                        }

                        return response.body.string()
                    }

            } catch (e: Exception) {

                lastException = e

                if (attempt < 2) {

                    try {
                        Thread.sleep(1000L)
                    } catch (_: Exception) {
                    }
                }
            }
        }

        throw lastException
            ?: Exception(
                "Onbekende downloadfout"
            )
    }
}