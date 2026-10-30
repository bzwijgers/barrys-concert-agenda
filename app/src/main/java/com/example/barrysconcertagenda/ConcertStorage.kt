package com.example.barrysconcertagenda

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject

object ConcertStorage {

    private const val PREFS_NAME = "concert_storage"
    // Keep a small separate journal of user actions. Never rewrite thousands
    // of concert records synchronously just to toggle one heart or ticket.
    private const val USER_STATE_PREFS = "concert_user_state"
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
            val userPrefs = context.getSharedPreferences(USER_STATE_PREFS, Context.MODE_PRIVATE)
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
                        ticketSwapUrl = item.optString("ticketSwapUrl", ""),
                        firstFound = item.optLong("firstFound", 0L),
                        isFavorite = userPrefs.getBoolean(
                            "favorite:" + normalizeUrl(item.optString("url", "")),
                            item.optBoolean("isFavorite", false)
                        ),
                        isAttending = userPrefs.getBoolean(
                            "attending:" + normalizeUrl(item.optString("url", "")),
                            item.optBoolean("isAttending", false)
                        ),
                        clubCard = item.optBoolean("clubCard", false)
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
            item.put("ticketSwapUrl", concert.ticketSwapUrl)
            item.put("firstFound", concert.firstFound)
            item.put("isFavorite", concert.isFavorite)
            item.put("isAttending", concert.isAttending)
            item.put("clubCard", concert.clubCard)

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

    fun setFavorite(context: Context, url: String, favorite: Boolean) {
        context.getSharedPreferences(USER_STATE_PREFS, Context.MODE_PRIVATE)
            .edit().putBoolean("favorite:" + normalizeUrl(url), favorite).apply()
    }

    fun setAttending(context: Context, url: String, attending: Boolean) {
        context.getSharedPreferences(USER_STATE_PREFS, Context.MODE_PRIVATE)
            .edit().putBoolean("attending:" + normalizeUrl(url), attending).apply()
    }

    // Existing flags embedded in concert_storage remain readable. The small
    // user-state journal takes precedence after the first user action.

    fun setTicketSwapUrl(
        context: Context,
        url: String,
        ticketSwapUrl: String
    ) {
        val normalizedTarget = normalizeUrl(url)
        val updated = loadConcerts(context).map { concert ->
            if (normalizeUrl(concert.url) == normalizedTarget) {
                concert.copy(ticketSwapUrl = ticketSwapUrl)
            } else {
                concert
            }
        }
        saveConcerts(context, updated)
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