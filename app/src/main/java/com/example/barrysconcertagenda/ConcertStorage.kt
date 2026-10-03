package com.example.barrysconcertagenda

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject

object ConcertStorage {

    private const val PREFS_NAME = "concert_storage"
    private const val KEY_CONCERTS = "concerts"
    private const val KEY_LAST_CHECK = "last_check"

    fun loadConcerts(context: Context): List<StoredConcert> {

        val prefs = context.getSharedPreferences(
            PREFS_NAME,
            Context.MODE_PRIVATE
        )

        val json = prefs.getString(
            KEY_CONCERTS,
            null
        ) ?: return emptyList()

        return try {

            val array = JSONArray(json)
            val concerts = mutableListOf<StoredConcert>()

            for (i in 0 until array.length()) {

                val item = array.getJSONObject(i)

                concerts.add(
                    StoredConcert(
                        artist = item.optString("artist", ""),
                        venue = item.optString("venue", ""),
                        city = item.optString("city", ""),
                        country = item.optString("country", ""),
                        date = item.optString("date", ""),
                        time = item.optString("time", ""),
                        source = item.optString("source", ""),
                        url = item.optString("url", ""),
                        firstFound = item.optLong("firstFound", 0L),
                        isFavorite = item.optBoolean("isFavorite", false)
                    )
                )
            }

            concerts

        } catch (_: Exception) {

            emptyList()
        }
    }

    fun saveConcerts(
        context: Context,
        concerts: List<StoredConcert>
    ) {

        val array = JSONArray()

        concerts.forEach { concert ->

            val item = JSONObject()

            item.put("artist", concert.artist)
            item.put("venue", concert.venue)
            item.put("city", concert.city)
            item.put("country", concert.country)
            item.put("date", concert.date)
            item.put("time", concert.time)
            item.put("source", concert.source)
            item.put("url", concert.url)
            item.put("firstFound", concert.firstFound)
            item.put("isFavorite", concert.isFavorite)

            array.put(item)
        }

        val prefs = context.getSharedPreferences(
            PREFS_NAME,
            Context.MODE_PRIVATE
        )

        prefs.edit()
            .putString(
                KEY_CONCERTS,
                array.toString()
            )
            .apply()
    }

    fun setFavorite(
        context: Context,
        url: String,
        favorite: Boolean
    ) {

        val concerts = loadConcerts(context)

        val normalizedTarget = normalizeUrl(url)

        val updated = concerts.map { concert ->

            if (
                normalizeUrl(concert.url) ==
                normalizedTarget
            ) {

                concert.copy(
                    isFavorite = favorite
                )

            } else {

                concert
            }
        }

        saveConcerts(
            context,
            updated
        )
    }

    fun getLastCheck(context: Context): Long {

        val prefs = context.getSharedPreferences(
            PREFS_NAME,
            Context.MODE_PRIVATE
        )

        return prefs.getLong(
            KEY_LAST_CHECK,
            0L
        )
    }

    fun setLastCheck(
        context: Context,
        timestamp: Long
    ) {

        val prefs = context.getSharedPreferences(
            PREFS_NAME,
            Context.MODE_PRIVATE
        )

        prefs.edit()
            .putLong(
                KEY_LAST_CHECK,
                timestamp
            )
            .apply()
    }

    private fun normalizeUrl(url: String): String {

        return url
            .trim()
            .trimEnd('/')
            .lowercase()
    }
}