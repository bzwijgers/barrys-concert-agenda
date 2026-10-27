package com.example.barrysconcertagenda

/** Archive includes every retained past event, irrespective of ticket or favourite status. */
fun archiveConcerts(concerts: List<Concert>): List<Concert> =
    concerts.filter { it.archived }

/**
 * Never discard cached data after a failed/empty download. On a successful
 * refresh, retain removed past events for history and future events explicitly
 * saved by the user, but drop unmarked future events no longer published.
 */
fun retainedStoredConcerts(
    cached: List<StoredConcert>,
    incomingUrls: Set<String>,
    feedLoaded: Boolean
): List<StoredConcert> {
    if (!feedLoaded) return cached
    return cached.filter { item ->
        item.url.trim().trimEnd('/').lowercase() in incomingUrls ||
            item.isFavorite || item.isAttending || isPastConcert(item.date)
    }
}
