package com.example.barrysconcertagenda

import android.content.Context
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class ConcertStorageInstrumentedTest {
    @Test
    fun heartsAndTicketsStaySavedWithoutRewritingLargeConcertCache() {
        // Instrumentation package has its own preferences, isolated from V3.
        val ctx = InstrumentationRegistry.getInstrumentation().context
        ctx.getSharedPreferences("concert_storage", Context.MODE_PRIVATE).edit().clear().commit()
        ctx.getSharedPreferences("concert_user_state", Context.MODE_PRIVATE).edit().clear().commit()
        val url = "https://example.com/concert/test"
        val item = StoredConcert(
            artist = "Test Band", venue = "Rotown", city = "Rotterdam",
            country = "NL", date = "2026-11-29", time = "20:00",
            source = "Rotown", url = url, firstFound = 0L
        )
        ConcertStorage.saveConcerts(ctx, listOf(item))
        val cacheBefore = ctx.getSharedPreferences("concert_storage", Context.MODE_PRIVATE)
            .getString("concerts", "")
        ConcertStorage.setFavorite(ctx, url, true)
        ConcertStorage.setAttending(ctx, url, true)
        val cacheAfter = ctx.getSharedPreferences("concert_storage", Context.MODE_PRIVATE)
            .getString("concerts", "")
        assertEquals("A heart/ticket action may not rewrite the big feed", cacheBefore, cacheAfter)
        val saved = ConcertStorage.loadConcerts(ctx).single()
        assertTrue(saved.isFavorite)
        assertTrue(saved.isAttending)

        ConcertStorage.setFavorite(ctx, url, false)
        assertFalse(ConcertStorage.loadConcerts(ctx).single().isFavorite)
        assertTrue(ConcertStorage.loadConcerts(ctx).single().isAttending)
    }
}
