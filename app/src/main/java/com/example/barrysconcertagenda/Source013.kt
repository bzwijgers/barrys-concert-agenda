package com.example.barrysconcertagenda

import java.net.HttpURLConnection
import java.net.URL

data class Concert013(
    val artist: String,
    val date: String,
    val time: String,
    val venue: String,
    val city: String = "Tilburg",
    val country: String = "NL",
    val source: String = "013",
    val url: String
)

object Source013 {

    fun getConcerts(
        knownUrls: Set<String> = emptySet()
    ): List<Concert013> {

        return try {

            val programHtml =
                downloadPage(
                    "https://www.013.nl/programma"
                )

            val programUrls =
                findProgramUrls(programHtml)

            val normalisedKnownUrls =
                knownUrls
                    .map { normaliseUrl(it) }
                    .toSet()

            /*
             * Alleen URL's die nog niet eerder
             * zijn opgeslagen hoeven we te openen.
             */
            val newUrls =
                programUrls.filter { eventUrl ->

                    normaliseUrl(eventUrl) !in
                            normalisedKnownUrls
                }

            val newConcerts =
                mutableListOf<Concert013>()

            for (eventUrl in newUrls) {

                try {

                    val eventHtml =
                        downloadPage(eventUrl)

                    val concert =
                        parseEvent(
                            eventHtml,
                            eventUrl
                        )

                    if (concert != null) {
                        newConcerts.add(concert)
                    }

                } catch (e: Exception) {
                    /*
                     * Als één detailpagina mislukt,
                     * gaan we gewoon verder.
                     */
                }
            }

            newConcerts
                .distinctBy {
                    normaliseUrl(it.url)
                }

        } catch (e: Exception) {

            emptyList()
        }
    }

    private fun findProgramUrls(
        html: String
    ): List<String> {

        val eventRegex =
            Regex(
                """href=["']([^"']*/programma/[^"'?#]+)["']""",
                RegexOption.IGNORE_CASE
            )

        return eventRegex
            .findAll(html)
            .map { match ->

                var eventUrl =
                    match.groupValues[1]

                if (eventUrl.startsWith("/")) {

                    eventUrl =
                        "https://www.013.nl$eventUrl"
                }

                eventUrl
                    .trim()
                    .trimEnd('/')
            }
            .filter { eventUrl ->

                eventUrl.startsWith(
                    "https://www.013.nl/programma/",
                    ignoreCase = true
                )
            }
            .distinctBy { eventUrl ->

                normaliseUrl(eventUrl)
            }
            .toList()
    }

    private fun parseEvent(
        html: String,
        eventUrl: String
    ): Concert013? {

        val eventPosition =
            Regex(
                """"@type"\s*:\s*"Event"""",
                RegexOption.IGNORE_CASE
            )
                .find(html)
                ?.range
                ?.first
                ?: return null

        val blockStart =
            (eventPosition - 1000)
                .coerceAtLeast(0)

        val blockEnd =
            (eventPosition + 12000)
                .coerceAtMost(html.length)

        val block =
            html.substring(
                blockStart,
                blockEnd
            )

        val rawName =
            findJsonValue(
                block,
                "name"
            ) ?: return null

        val rawStartDate =
            findJsonValue(
                block,
                "startDate"
            ) ?: return null

        val startDate =
            cleanJsonText(rawStartDate)

        val artist =
            cleanArtistName(
                cleanJsonText(rawName)
            )

        if (artist.isBlank()) {
            return null
        }

        val location =
            findLocation(block)

        return Concert013(
            artist = artist,
            date = formatDate(startDate),
            time = formatTime(startDate),
            venue = location.ifBlank { "013" },
            url = eventUrl
        )
    }

    private fun cleanArtistName(
        name: String
    ): String {

        val months =
            "januari|" +
                    "februari|" +
                    "maart|" +
                    "april|" +
                    "mei|" +
                    "juni|" +
                    "juli|" +
                    "augustus|" +
                    "september|" +
                    "oktober|" +
                    "november|" +
                    "december"

        val dateAtEnd =
            Regex(
                """\s*[-–—|]\s*\d{1,2}\s+(?:$months)(?:\s+\d{4})?\s*$""",
                RegexOption.IGNORE_CASE
            )

        return name
            .replace(
                dateAtEnd,
                ""
            )
            .trim()
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
            return "013"
        }

        val end =
            (locationStart + 2500)
                .coerceAtMost(block.length)

        val locationBlock =
            block.substring(
                locationStart,
                end
            )

        val locationName =
            findJsonValue(
                locationBlock,
                "name"
            )

        return locationName
            ?.let {
                cleanJsonText(it)
            }
            ?.ifBlank {
                "013"
            }
            ?: "013"
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
            parts[2]
                .toIntOrNull()
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

    private fun normaliseUrl(
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

        val url =
            URL(address)

        val connection =
            url.openConnection()
                    as HttpURLConnection

        connection.requestMethod =
            "GET"

        connection.connectTimeout =
            10000

        connection.readTimeout =
            10000

        connection.instanceFollowRedirects =
            true

        connection.setRequestProperty(
            "User-Agent",
            "Mozilla/5.0 BarryConcertAgenda/1.0"
        )

        connection.setRequestProperty(
            "Accept",
            "text/html,application/xhtml+xml"
        )

        val responseCode =
            connection.responseCode

        if (responseCode !in 200..299) {

            connection.disconnect()

            throw Exception(
                "HTTP $responseCode"
            )
        }

        val html =
            connection
                .inputStream
                .bufferedReader()
                .use { reader ->
                    reader.readText()
                }

        connection.disconnect()

        return html
    }
}