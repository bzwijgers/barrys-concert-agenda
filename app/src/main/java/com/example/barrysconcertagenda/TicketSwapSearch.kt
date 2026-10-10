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
        val uri = try { java.net.URI(candidate.trim()) } catch (_: Exception) { return false }
        if (uri.scheme != "https" || uri.host?.lowercase(Locale.ROOT) !in setOf(
                "www.ticketswap.nl", "ticketswap.nl", "www.ticketswap.com", "ticketswap.com"
            )) return false
        val path = uri.path ?: return false
        if (!path.startsWith("/concert-tickets/")) return false
        val slug = path.removePrefix("/concert-tickets/")
        if (slug.isBlank() || slug.contains('/')) return false
        val date = Regex("""-(20\d{2}-\d{2}-\d{2})-[A-Za-z0-9]+$""")
            .find(slug)?.groupValues?.get(1) ?: return false
        if (date != concert.date) return false

        val candidateWords = tokens(slug)
        val artistWords = tokens(concert.artist)
        if (artistWords.isEmpty()) return false
        // Avoid a wrong artist at the same venue on the same night:
        // require all artist terms for short names, nearly all for long names.
        val required = if (artistWords.size <= 4) artistWords.size else artistWords.size - 1
        if ((artistWords intersect candidateWords).size < required) return false
        val cityAlternatives = when (concert.city.lowercase(Locale.ROOT)) {
            "den haag", "'s-gravenhage", "s-gravenhage" -> setOf("hague", "gravenhage")
            "antwerpen" -> setOf("antwerp")
            "brussel", "bruxelles" -> setOf("brussels")
            "gent" -> setOf("ghent")
            else -> emptySet()
        }
        return (tokens(concert.city) intersect candidateWords).isNotEmpty() ||
            (cityAlternatives intersect candidateWords).isNotEmpty() ||
            (tokens(concert.venue) intersect candidateWords).isNotEmpty()
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
