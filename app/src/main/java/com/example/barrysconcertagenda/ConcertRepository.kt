package com.example.barrysconcertagenda

import android.content.Context
import org.json.JSONArray
import java.net.HttpURLConnection
import java.net.URL

data class SourceConcert(
    val artist: String,
    val venue: String,
    val city: String,
    val country: String,
    val date: String,
    val time: String = "",
    val source: String,
    val url: String
)

object ConcertRepository {

    private const val CENTRAL_JSON_URL =
        "https://bzwijgers.github.io/barrys-concert-agenda/concerts.json"

    fun getAllConcerts(
        context: Context
    ): List<SourceConcert> {

        val connection =
            URL(CENTRAL_JSON_URL)
                .openConnection() as HttpURLConnection

        return try {

            connection.requestMethod = "GET"
            connection.connectTimeout = 10_000
            connection.readTimeout = 15_000
            connection.setRequestProperty(
                "User-Agent",
                "BarrysConcertAgenda/1.0"
            )
            connection.setRequestProperty(
                "Cache-Control",
                "no-cache"
            )

            if (connection.responseCode !in 200..299) {
                throw Exception(
                    "HTTP ${connection.responseCode}"
                )
            }

            val json =
                connection.inputStream
                    .bufferedReader()
                    .use {
                        it.readText()
                    }

            parseConcerts(json)

        } finally {

            connection.disconnect()
        }
    }

    private fun parseConcerts(
        json: String
    ): List<SourceConcert> {

        val array =
            JSONArray(json)

        val concerts =
            mutableListOf<SourceConcert>()

        for (index in 0 until array.length()) {

            val item =
                array.getJSONObject(index)

            val concert =
                SourceConcert(
                    artist =
                        item.optString(
                            "artist",
                            ""
                        ),
                    venue =
                        item.optString(
                            "venue",
                            ""
                        ),
                    city =
                        item.optString(
                            "city",
                            ""
                        ),
                    country =
                        item.optString(
                            "country",
                            ""
                        ),
                    date =
                        item.optString(
                            "date",
                            ""
                        ),
                    time =
                        item.optString(
                            "time",
                            ""
                        ),
                    source =
                        item.optString(
                            "source",
                            ""
                        ),
                    url =
                        item.optString(
                            "url",
                            ""
                        )
                )

            if (
                concert.artist.isNotBlank() &&
                concert.url.isNotBlank()
            ) {
                concerts.add(
                    concert
                )
            }
        }

        return concerts
            .distinctBy {
                normalizeUrl(
                    it.url
                )
            }
    }

    private fun normalizeUrl(
        url: String
    ): String {

        return url
            .trim()
            .trimEnd('/')
            .lowercase()
    }
}