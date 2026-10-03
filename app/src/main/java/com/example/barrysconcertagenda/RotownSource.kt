package com.example.barrysconcertagenda

import java.net.HttpURLConnection
import java.net.URL

data class RotownConcert(
    val artist: String,
    val date: String,
    val time: String,
    val venue: String,
    val city: String = "Rotterdam",
    val country: String = "NL",
    val source: String = "Rotown",
    val url: String
)

object RotownSource {

    fun getConcerts(): List<RotownConcert> {

        return try {

            val url =
                URL("https://www.rotown.nl/")

            val connection =
                url.openConnection()
                        as HttpURLConnection

            connection.requestMethod = "GET"
            connection.connectTimeout = 10000
            connection.readTimeout = 10000

            connection.setRequestProperty(
                "User-Agent",
                "BarryConcertAgenda/1.0"
            )

            val responseCode =
                connection.responseCode

            if (responseCode !in 200..299) {

                connection.disconnect()

                return emptyList()
            }

            val html =
                connection.inputStream
                    .bufferedReader()
                    .use {
                        it.readText()
                    }

            connection.disconnect()

            val concertUrls =
                findConcertUrls(html)

            val structuredEvents =
                findStructuredEvents(html)

            structuredEvents
                .filter { event ->

                    concertUrls.any { concertUrl ->

                        normaliseUrl(concertUrl) ==
                                normaliseUrl(event.url)
                    }
                }
                .distinctBy {
                    normaliseUrl(it.url)
                }
                .sortedBy {
                    it.sortDate
                }
                .map {

                    RotownConcert(
                        artist =
                            it.artist,

                        date =
                            formatDate(
                                it.startDate
                            ),

                        time =
                            formatTime(
                                it.startDate
                            ),

                        venue =
                            it.location
                                .ifBlank {
                                    "Rotown"
                                },

                        url =
                            it.url
                    )
                }

        } catch (e: Exception) {

            emptyList()
        }
    }

    private fun findConcertUrls(
        html: String
    ): List<String> {

        val eventRegex =
            Regex(
                """<div\s+class=["']([^"']*\bwp_theatre_event\b[^"']*)["'][^>]*>""",
                setOf(
                    RegexOption.IGNORE_CASE,
                    RegexOption.DOT_MATCHES_ALL
                )
            )

        return eventRegex
            .findAll(html)
            .mapNotNull { match ->

                val classes =
                    match.groupValues[1]

                val isConcert =
                    Regex(
                        """(?:^|\s)concert(?:\s|$)""",
                        RegexOption.IGNORE_CASE
                    )
                        .containsMatchIn(
                            classes
                        )

                if (!isConcert) {
                    return@mapNotNull null
                }

                val start =
                    match.range.first

                val end =
                    (start + 10000)
                        .coerceAtMost(
                            html.length
                        )

                val section =
                    html.substring(
                        start,
                        end
                    )

                Regex(
                    """href=["'](https://www\.rotown\.nl/agenda/[^"'?#]+/?)["']""",
                    RegexOption.IGNORE_CASE
                )
                    .find(section)
                    ?.groupValues
                    ?.getOrNull(1)
            }
            .distinct()
            .toList()
    }

    private fun findStructuredEvents(
        html: String
    ): List<StructuredEvent> {

        val eventStarts =
            Regex(
                """"@type"\s*:\s*"Event"""",
                RegexOption.IGNORE_CASE
            )
                .findAll(html)
                .map {
                    it.range.first
                }
                .toList()

        val events =
            mutableListOf<StructuredEvent>()

        for (start in eventStarts) {

            val blockStart =
                (start - 300)
                    .coerceAtLeast(0)

            val blockEnd =
                (start + 8000)
                    .coerceAtMost(
                        html.length
                    )

            val block =
                html.substring(
                    blockStart,
                    blockEnd
                )

            val name =
                findJsonValue(
                    block,
                    "name"
                )

            val eventUrl =
                findJsonValue(
                    block,
                    "url"
                )

            val startDate =
                findJsonValue(
                    block,
                    "startDate"
                )

            val location =
                findLocation(block)

            if (
                !name.isNullOrBlank() &&
                !eventUrl.isNullOrBlank() &&
                !startDate.isNullOrBlank() &&
                eventUrl.contains(
                    "rotown.nl\\/agenda\\/",
                    ignoreCase = true
                )
            ) {

                events.add(
                    StructuredEvent(
                        artist =
                            cleanJsonText(
                                name
                            ),

                        startDate =
                            cleanJsonText(
                                startDate
                            ),

                        location =
                            location,

                        url =
                            cleanJsonText(
                                eventUrl
                            )
                    )
                )
            }
        }

        return events
    }

    private fun findLocation(
        block: String
    ): String {

        val locationStart =
            block.indexOf(
                "\"location\"",
                ignoreCase = true
            )

        if (locationStart < 0) {
            return ""
        }

        val end =
            (locationStart + 1500)
                .coerceAtMost(
                    block.length
                )

        val locationBlock =
            block.substring(
                locationStart,
                end
            )

        return findJsonValue(
            locationBlock,
            "name"
        )
            ?.let {
                cleanJsonText(it)
            }
            ?: ""
    }

    private fun findJsonValue(
        text: String,
        key: String
    ): String? {

        val regex =
            Regex(
                """"$key"\s*:\s*"((?:\\.|[^"\\])*)"""",
                RegexOption.IGNORE_CASE
            )

        return regex
            .find(text)
            ?.groupValues
            ?.getOrNull(1)
    }

    private fun cleanJsonText(
        text: String
    ): String {

        return text
            .replace("\\/", "/")
            .replace("\\\"", "\"")
            .replace("\\u0026", "&")
            .replace("\\u0027", "'")
            .replace("\\u2018", "‘")
            .replace("\\u2019", "’")
            .replace("\\u2013", "–")
            .replace("\\u2014", "—")
            .replace("&amp;", "&")
            .trim()
    }

    private fun normaliseUrl(
        url: String
    ): String {

        return cleanJsonText(url)
            .trim()
            .trimEnd('/')
            .lowercase()
    }

    private fun formatDate(
        date: String
    ): String {

        val datePart =
            date.substringBefore("T")

        val parts =
            datePart.split("-")

        if (parts.size != 3) {
            return datePart
        }

        val year =
            parts[0]

        val month =
            parts[1]

        val day =
            parts[2].toIntOrNull()
                ?: return datePart

        val monthName =
            when (month) {

                "01" -> "januari"
                "02" -> "februari"
                "03" -> "maart"
                "04" -> "april"
                "05" -> "mei"
                "06" -> "juni"
                "07" -> "juli"
                "08" -> "augustus"
                "09" -> "september"
                "10" -> "oktober"
                "11" -> "november"
                "12" -> "december"

                else -> month
            }

        return "$day $monthName $year"
    }

    private fun formatTime(
        date: String
    ): String {

        if (!date.contains("T")) {
            return ""
        }

        return date
            .substringAfter("T")
            .take(5)
    }

    private data class StructuredEvent(
        val artist: String,
        val startDate: String,
        val location: String,
        val url: String
    ) {

        val sortDate: String
            get() = startDate
    }
}