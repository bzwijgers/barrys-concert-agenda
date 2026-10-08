package com.example.barrysconcertagenda

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLDecoder
import java.net.URLEncoder
import java.util.Locale

/**
 * One bounded background lookup. No WebView, JavaScript, polling loop or UI-thread network IO.
 * Unknown/blocked responses produce null; never guess a TicketSwap homepage or wrong event.
 */
internal object TicketSwapSearch {
    private val linkPattern = Regex(
        """https?://(?:www\.)?ticketswap\.(?:com|nl)/concert-tickets/[a-zA-Z0-9._~%/-]+""",
        RegexOption.IGNORE_CASE
    )
    private val datePattern = Regex("""-20\d{2}-\d{2}-\d{2}-""")
    private val stopWords = setOf("the", "a", "and", "of", "in", "live", "tour", "show", "presents")

    private fun tokens(value: String): Set<String> =
        java.text.Normalizer.normalize(value, java.text.Normalizer.Form.NFD)
            .replace(Regex("""\p{Mn}+"""), "")
            .lowercase(Locale.ROOT)
            .split(Regex("[^a-z0-9]+"))
            .filter { it.length > 1 && it !in stopWords }
            .toSet()

    internal fun exactMatch(concert: Concert, candidate: String): Boolean {
        if (!candidate.startsWith("https://www.ticketswap.", ignoreCase = true) &&
            !candidate.startsWith("https://ticketswap.", ignoreCase = true)) return false
        if (!candidate.contains("/concert-tickets/")) return false
        if (!Regex("""20\d\d-\d\d-\d\d""").matches(concert.date)) return false
        if (!candidate.contains("-" + concert.date + "-", ignoreCase = true)) return false
        val slug = candidate.substringBefore("?").substringAfterLast("/")
        val words = tokens(slug)
        val artist = tokens(concert.artist)
        if (artist.isEmpty()) return false
        if (artist.intersect(words).size < maxOf(1, (artist.size + 1) / 2)) return false
        val cityAlternatives = when (concert.city.lowercase(Locale.ROOT)) {
            "den haag", "'s-gravenhage", "s-gravenhage" -> setOf("the", "hague")
            "antwerpen" -> setOf("antwerp")
            "brussel", "bruxelles" -> setOf("brussels")
            "gent" -> setOf("ghent")
            else -> emptySet()
        }
        return tokens(concert.city).intersect(words).isNotEmpty() ||
            cityAlternatives.intersect(words).isNotEmpty() ||
            tokens(concert.venue).intersect(words).isNotEmpty()
    }

    suspend fun find(concert: Concert): String? = withContext(Dispatchers.IO) {
        var connection: HttpURLConnection? = null
        try {
            val term = "${concert.artist} ${concert.city} ${concert.date} site:ticketswap.com/concert-tickets"
            val url = URL("https://www.google.com/search?q=" + URLEncoder.encode(term, "UTF-8"))
            connection = (url.openConnection() as HttpURLConnection).apply {
                connectTimeout = 7_000
                readTimeout = 7_000
                instanceFollowRedirects = true
                setRequestProperty("User-Agent", "Mozilla/5.0 (Linux; Android 15) AppleWebKit/537.36 Chrome/131.0 Mobile Safari/537.36")
            }
            if (connection.responseCode != 200) return@withContext null
            val page = connection.inputStream.bufferedReader().use { it.readText().take(1_000_000) }
            // Search results may contain HTML entities or percent-encoded destination links.
            val decoded = buildList {
                add(page.replace("&amp;", "&").replace("\\u0026", "&"))
                add(URLDecoder.decode(last(), "UTF-8"))
            }
            decoded.asSequence()
                .flatMap { linkPattern.findAll(it).map { match -> match.value } }
                .map { it.substringBefore("?").trimEnd('/', '.', ',', ')', ';') }
                .firstOrNull { exactMatch(concert, it) }
                ?.replace("https://www.ticketswap.com/", "https://www.ticketswap.nl/")
        } catch (_: Exception) {
            null // Search engines sometimes deny automation. Never crash a favorite action.
        } finally {
            connection?.disconnect()
        }
    }
}
