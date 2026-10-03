package com.example.barrysconcertagenda

import android.util.Log
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONArray
import java.util.concurrent.TimeUnit

object EffenaarSource {

    private const val TAG = "EffenaarSource"

    private const val JSON_URL =
        "https://bzwijgers.github.io/barrys-concert-agenda/concerts.json"

    private val client = OkHttpClient.Builder()
        .connectTimeout(20, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .build()

    fun getConcerts(): List<SourceConcert> {

        Log.d(TAG, "Effenaar ophalen via GitHub Pages")

        val request = Request.Builder()
            .url(JSON_URL)
            .header(
                "User-Agent",
                "BarrysConcertAgenda/1.0"
            )
            .build()

        return try {

            client.newCall(request).execute().use { response ->

                Log.d(TAG, "HTTP status: ${response.code}")

                if (!response.isSuccessful) {
                    Log.e(TAG, "HTTP fout: ${response.code}")
                    return emptyList()
                }

                val jsonText = response.body.string()

                Log.d(TAG, "JSON ontvangen: ${jsonText.length} tekens")

                val array = JSONArray(jsonText)

                val concerts = mutableListOf<SourceConcert>()

                for (i in 0 until array.length()) {

                    val item = array.getJSONObject(i)

                    val artist = item.optString("artist").trim()
                    val venue = item.optString("venue").trim()
                    val city = item.optString("city").trim()
                    val country = item.optString("country").trim()
                    val date = item.optString("date").trim()
                    val time = item.optString("time").trim()
                    val source = item.optString("source").trim()
                    val url = item.optString("url").trim()

                    if (
                        artist.isBlank() ||
                        date.isBlank() ||
                        url.isBlank()
                    ) {
                        Log.w(
                            TAG,
                            "Concert overgeslagen: ontbrekende gegevens bij item $i"
                        )
                        continue
                    }

                    concerts.add(
                        SourceConcert(
                            artist = artist,
                            venue = if (venue.isNotBlank()) venue else "Effenaar",
                            city = if (city.isNotBlank()) city else "Eindhoven",
                            country = if (country.isNotBlank()) country else "NL",
                            date = date,
                            time = time,
                            source = if (source.isNotBlank()) source else "Effenaar",
                            url = url
                        )
                    )
                }

                val uniqueConcerts = concerts.distinctBy {
                    it.url
                        .trim()
                        .trimEnd('/')
                        .lowercase()
                }

                Log.d(
                    TAG,
                    "Effenaar gereed: ${uniqueConcerts.size} concerten"
                )

                uniqueConcerts
            }

        } catch (e: Exception) {

            Log.e(
                TAG,
                "Fout bij ophalen Effenaar via GitHub: ${e.message}",
                e
            )

            emptyList()
        }
    }
}