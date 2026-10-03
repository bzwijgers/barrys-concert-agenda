package com.example.barrysconcertagenda

data class StoredConcert(
    val artist: String,
    val venue: String,
    val city: String,
    val country: String,
    val date: String,
    val time: String,
    val source: String,
    val url: String,
    val firstFound: Long,
    val isFavorite: Boolean = false,
    val isAttending: Boolean = false,
    val clubCard: Boolean = false
)