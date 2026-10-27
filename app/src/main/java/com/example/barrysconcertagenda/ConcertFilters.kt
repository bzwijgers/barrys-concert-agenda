package com.example.barrysconcertagenda

/** Archive includes every retained past event, irrespective of ticket or favourite status. */
fun archiveConcerts(concerts: List<Concert>): List<Concert> =
    concerts.filter { it.archived }
