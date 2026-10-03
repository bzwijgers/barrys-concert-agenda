package com.example.barrysconcertagenda

import okhttp3.OkHttpClient
import okhttp3.Request
import java.time.LocalDate
import java.time.format.DateTimeFormatter
import java.util.Locale
import java.util.concurrent.TimeUnit

data class BaroegConcert(
    val artist: String,
    val date: String,
    val time: String,
    val venue: String = "Baroeg",
    val city: String = "Rotterdam",
    val country: String = "NL",
    val source: String = "Baroeg",
    val url: String
)

object BaroegSource {

    private const val AGENDA_URL =
        "https://baroeg.nl/agenda/"

    private val client =
        OkHttpClient.Builder()
            .connectTimeout(20, TimeUnit.SECONDS)
            .readTimeout(20, TimeUnit.SECONDS)
            .callTimeout(30, TimeUnit.SECONDS)
            .retryOnConnectionFailure(true)
            .build()

    fun getConcerts(): List<BaroegConcert> {

        return try {

            val agendaHtml =
                downloadPage(
                    AGENDA_URL
                )

            val eventUrls =
                findEventUrls(
                    agendaHtml
                )

            val concerts =
                mutableListOf<BaroegConcert>()

            eventUrls.forEach { eventUrl ->

                try {

                    val html =
                        downloadPage(
                            eventUrl
                        )

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

                            concerts.add(
                                concert
                            )
                        }
                    }

                } catch (_: Exception) {
                    // Eén mislukte pagina mag de rest
                    // van Baroeg niet blokkeren.
                }
            }

            concerts
                .distinctBy {
                    normalizeUrl(
                        it.url
                    )
                }

        } catch (_: Exception) {

            emptyList()
        }
    }

    private fun findEventUrls(
        html: String
    ): List<String> {

        val cleanedHtml =
            html
                .replace("\\/", "/")
                .replace("\\u002F", "/")
                .replace("\\u002f", "/")

        val urls =
            mutableListOf<String>()

        val absoluteRegex =
            Regex(
                """https?://(?:www\.)?baroeg\.nl/productie/[^"'<>?\s]+""",
                RegexOption.IGNORE_CASE
            )

        absoluteRegex
            .findAll(
                cleanedHtml
            )
            .forEach { match ->

                urls.add(
                    match.value
                        .substringBefore("?")
                        .substringBefore("#")
                        .trimEnd('/') + "/"
                )
            }

        val relativeRegex =
            Regex(
                """(?:href\s*=\s*["'])?(/productie/[^"'<>?\s]+)""",
                RegexOption.IGNORE_CASE
            )

        relativeRegex
            .findAll(
                cleanedHtml
            )
            .forEach { match ->

                val path =
                    match.groupValues[1]
                        .substringBefore("?")
                        .substringBefore("#")
                        .trimEnd('/')

                urls.add(
                    "https://baroeg.nl$path/"
                )
            }

        return urls
            .distinct()
    }

    private fun parseEvent(
        html: String,
        eventUrl: String
    ): BaroegConcert? {

        val artist =
            extractArtist(
                html
            )

        if (
            artist.isBlank()
        ) {
            return null
        }

        val text =
            htmlToText(
                html
            )

        val date =
            extractEventDate(
                text
            )
                ?: return null

        val time =
            extractEventTime(
                text,
                date
            )

        return BaroegConcert(
            artist = artist,
            date = date,
            time = time,
            venue = "Baroeg",
            city = "Rotterdam",
            country = "NL",
            source = "Baroeg",
            url = eventUrl
        )
    }

    private fun extractArtist(
        html: String
    ): String {

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

        if (
            !h1.isNullOrBlank()
        ) {

            val artist =
                cleanArtistTitle(
                    decodeHtml(
                        stripTags(
                            h1
                        )
                    )
                )

            if (
                artist.isNotBlank()
            ) {
                return artist
            }
        }

        val titleRegex =
            Regex(
                """<title[^>]*>(.*?)</title>""",
                setOf(
                    RegexOption.IGNORE_CASE,
                    RegexOption.DOT_MATCHES_ALL
                )
            )

        val title =
            titleRegex
                .find(html)
                ?.groupValues
                ?.getOrNull(1)
                ?: return ""

        return cleanArtistTitle(
            decodeHtml(
                stripTags(
                    title
                )
            )
        )
    }

    private fun cleanArtistTitle(
        title: String
    ): String {

        return title
            .replace(
                Regex(
                    """\s*[–—-]\s*Poppodium\s+Baroeg\s+Rotterdam\s*$""",
                    RegexOption.IGNORE_CASE
                ),
                ""
            )
            .replace(
                Regex(
                    """\s*[–—-]\s*Poppodium\s+Baroeg\s*$""",
                    RegexOption.IGNORE_CASE
                ),
                ""
            )
            .replace(
                Regex(
                    """\s*[–—-]\s*Baroeg\s+Rotterdam\s*$""",
                    RegexOption.IGNORE_CASE
                ),
                ""
            )
            .replace(
                Regex(
                    """\s+"""
                ),
                " "
            )
            .trim()
    }

    private fun extractEventDate(
        text: String
    ): String? {

        val months =
            "januari|februari|maart|april|mei|juni|" +
                    "juli|augustus|september|oktober|" +
                    "november|december"

        val monthFirstRegex =
            Regex(
                """\b($months)\s+(\d{1,2}),\s*(20\d{2})\b""",
                RegexOption.IGNORE_CASE
            )

        val candidates =
            monthFirstRegex
                .findAll(
                    text
                )
                .mapNotNull { match ->

                    val month =
                        monthNumber(
                            match.groupValues[1]
                        )
                            ?: return@mapNotNull null

                    val day =
                        match.groupValues[2]
                            .toIntOrNull()
                            ?: return@mapNotNull null

                    val year =
                        match.groupValues[3]
                            .toIntOrNull()
                            ?: return@mapNotNull null

                    try {

                        LocalDate.of(
                            year,
                            month,
                            day
                        )

                    } catch (_: Exception) {

                        null
                    }
                }
                .toList()

        val today =
            LocalDate.now()

        val eventDate =
            candidates
                .filter {
                    !it.isBefore(
                        today
                    )
                }
                .minOrNull()
                ?: return null

        val formatter =
            DateTimeFormatter.ofPattern(
                "d MMMM yyyy",
                Locale.forLanguageTag(
                    "nl-NL"
                )
            )

        return eventDate.format(
            formatter
        )
    }

    private fun extractEventTime(
        text: String,
        date: String
    ): String {

        val parsedDate =
            parseDutchDate(
                date
            )
                ?: return ""

        val month =
            when (
                parsedDate.monthValue
            ) {

                1 -> "januari"
                2 -> "februari"
                3 -> "maart"
                4 -> "april"
                5 -> "mei"
                6 -> "juni"
                7 -> "juli"
                8 -> "augustus"
                9 -> "september"
                10 -> "oktober"
                11 -> "november"
                12 -> "december"

                else -> ""
            }

        val dateMarker =
            "$month ${parsedDate.dayOfMonth}, ${parsedDate.year}"

        val datePosition =
            text.indexOf(
                dateMarker,
                ignoreCase = true
            )

        val relevantText =
            if (
                datePosition >= 0
            ) {

                text.substring(
                    datePosition,
                    minOf(
                        text.length,
                        datePosition + 250
                    )
                )

            } else {

                text
            }

        val timeRegex =
            Regex(
                """\b([01]?\d|2[0-3]):[0-5]\d\b"""
            )

        return timeRegex
            .find(
                relevantText
            )
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

        return when (
            month.lowercase()
        ) {

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
                    Regex(
                        """<[^>]+>"""
                    ),
                    " "
                )
                .replace(
                    Regex(
                        """\s+"""
                    ),
                    " "
                )
        )
    }

    private fun stripTags(
        text: String
    ): String {

        return text.replace(
            Regex(
                """<[^>]+>"""
            ),
            ""
        )
    }

    private fun decodeHtml(
        text: String
    ): String {

        return text
            .replace("&#8211;", "–")
            .replace("&#x2013;", "–", ignoreCase = true)
            .replace("&#8212;", "—")
            .replace("&#x2014;", "—", ignoreCase = true)
            .replace("&ndash;", "–")
            .replace("&mdash;", "—")
            .replace("&amp;", "&")
            .replace("&quot;", "\"")
            .replace("&#39;", "'")
            .replace("&#x27;", "'", ignoreCase = true)
            .replace("&apos;", "'")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
            .replace("&nbsp;", " ")
            .replace("&#x2F;", "/", ignoreCase = true)
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

        var lastException: Exception? =
            null

        repeat(3) { attempt ->

            try {

                val request =
                    Request.Builder()
                        .url(
                            address
                        )
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
                    .newCall(
                        request
                    )
                    .execute()
                    .use { response ->

                        if (
                            !response.isSuccessful
                        ) {

                            throw Exception(
                                "HTTP ${response.code} bij $address"
                            )
                        }

                        return response
                            .body
                            .string()
                    }

            } catch (e: Exception) {

                lastException =
                    e

                if (
                    attempt < 2
                ) {

                    try {

                        Thread.sleep(
                            750L
                        )

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