package com.example.barrysconcertagenda

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import java.time.LocalDate
import java.time.YearMonth
import java.time.format.DateTimeFormatter
import java.util.Locale

object BackstageColors {
    val background = Color(0xFF0C111D)
    val surface = Color(0xFF151F30)
    val raised = Color(0xFF26354D)
    val pink = Color(0xFFFF719D)
    val lime = Color(0xFFD5F378)
    val subtle = Color(0xFFA9B8D0)
    // Soft slate-blue for date dividers; no fluorescent green against pink titles.
    val date = Color(0xFFB5C4DB)
    // Legible labels over the faded light photo; concert cards stay dark.
    val pageText = Color(0xFF263543)
    val pageMuted = Color(0xFF526272)
    val pageDate = Color(0xFF526274)
    val pageAccent = Color(0xFF9E365A)
    val resultCount = Color(0xFF485868)
}

@Composable
fun BackstageHero(concert: Concert?, onTicketsClick: () -> Unit) {
    val gradient = Brush.linearGradient(
        listOf(Color(0xFF823E5F), Color(0xFF442C60), Color(0xFF222E54))
    )
    Card(
        modifier = Modifier.fillMaxWidth().clickable { onTicketsClick() },
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(containerColor = Color.Transparent),
        border = BorderStroke(1.dp, Color(0xFF734F78))
    ) {
        Column(
            modifier = Modifier.background(gradient).padding(22.dp),
            verticalArrangement = Arrangement.spacedBy(9.dp)
        ) {
            Text("JOUW VOLGENDE CONCERT", fontSize = 11.sp,
                color = Color(0xFFFFC2DA), fontWeight = FontWeight.Bold,
                letterSpacing = 1.2.sp)
            Spacer(Modifier.height(8.dp))
            Text(concert?.artist ?: "Nog niets gepland",
                fontWeight = FontWeight.ExtraBold, fontSize = 26.sp,
                color = Color.White, lineHeight = 29.sp, maxLines = 2)
            Text(
                if (concert == null) "Markeer een concert waarvoor je een kaartje hebt"
                else buildString {
                    append(concert.date)
                    if (concert.city.isNotBlank()) append(" · " + concert.city)
                    if (concert.time.isNotBlank()) append(" · " + concert.time)
                },
                fontSize = 12.sp, color = Color(0xFFF7DDE9)
            )
            Spacer(Modifier.height(12.dp))
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box(
                    modifier = Modifier.clip(RoundedCornerShape(7.dp))
                        .background(BackstageColors.lime)
                        .padding(horizontal = 11.dp, vertical = 8.dp)
                ) {
                    Text("🎟  MIJN TICKETS", color = Color(0xFF1B2730),
                        fontWeight = FontWeight.Bold, fontSize = 11.sp)
                }
                Spacer(Modifier.weight(1f))
                Text("↗", color = Color.White, fontSize = 24.sp)
            }
        }
    }
}

@Composable
fun BackstageQuickStats(tickets: Int, favorites: Int, newShows: Int,
                        onTickets: () -> Unit, onFavorites: () -> Unit, onNew: () -> Unit) {
    Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
        listOf(
            Triple(tickets, "Tickets", onTickets),
            Triple(favorites, "Favorieten", onFavorites),
            Triple(newShows, "Nieuw", onNew)
        ).forEach { (number, label, action) ->
            Box(
                modifier = Modifier.weight(1f)
                    .clip(RoundedCornerShape(11.dp))
                    .background(BackstageColors.surface)
                    .clickable { action() }
                    .padding(vertical = 13.dp),
                contentAlignment = Alignment.Center
            ) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Text(number.toString(), fontSize = 19.sp, fontWeight = FontWeight.ExtraBold,
                        color = BackstageColors.lime)
                    Text(label, fontSize = 10.sp, color = BackstageColors.subtle)
                }
            }
        }
    }
}

@Composable
fun BackstageChips(options: List<Pair<String, String>>, current: String,
                   onSelect: (String) -> Unit) {
    Row(
        modifier = Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),
        horizontalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        options.forEach { (id, label) ->
            val active = id == current
            Box(
                modifier = Modifier.clip(RoundedCornerShape(50))
                    .background(if (active) BackstageColors.lime else BackstageColors.raised)
                    .clickable { onSelect(id) }
                    .padding(horizontal = 15.dp, vertical = 10.dp)
            ) {
                Text(label, fontSize = 12.sp, fontWeight = FontWeight.Medium,
                    color = if (active) Color(0xFF1A2632) else Color.White)
            }
        }
    }
}

@Composable
fun BackstageCalendar(
    month: YearMonth,
    eventDays: Set<LocalDate>,
    selectedDay: LocalDate?,
    onPrevious: () -> Unit,
    onNext: () -> Unit,
    onSelectDay: (LocalDate?) -> Unit
) {
    Column(verticalArrangement = Arrangement.spacedBy(5.dp)) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically
        ) {
            TextButton(onClick = onPrevious) { Text("‹", fontSize = 26.sp) }
            Spacer(Modifier.weight(1f))
            Text(
                month.atDay(1).format(DateTimeFormatter.ofPattern("MMMM yyyy",
                    Locale.forLanguageTag("nl-NL"))).replaceFirstChar { it.uppercase() },
                fontWeight = FontWeight.Bold, fontSize = 17.sp
            )
            Spacer(Modifier.weight(1f))
            TextButton(onClick = onNext) { Text("›", fontSize = 26.sp) }
        }
        Row(modifier = Modifier.fillMaxWidth()) {
            listOf("MA", "DI", "WO", "DO", "VR", "ZA", "ZO").forEach { day ->
                Box(Modifier.weight(1f), contentAlignment = Alignment.Center) {
                    Text(day, fontSize = 10.sp, color = BackstageColors.pageMuted)
                }
            }
        }
        val offset = month.atDay(1).dayOfWeek.value - 1
        (0 until 6).forEach { week ->
            Row(modifier = Modifier.fillMaxWidth()) {
                (0 until 7).forEach { weekday ->
                    val number = week * 7 + weekday - offset + 1
                    val valid = number in 1..month.lengthOfMonth()
                    val date = if (valid) month.atDay(number) else null
                    val chosen = date != null && date == selectedDay
                    val hasEvents = date != null && date in eventDays
                    val background = when {
                        chosen -> BackstageColors.lime
                        hasEvents -> BackstageColors.raised
                        else -> Color.Transparent
                    }
                    Box(
                        modifier = Modifier.weight(1f).padding(2.dp).height(43.dp)
                            .clip(RoundedCornerShape(9.dp))
                            .background(background)
                            .clickable(enabled = valid) {
                                onSelectDay(if (chosen) null else date)
                            },
                        contentAlignment = Alignment.Center
                    ) {
                        if (valid) {
                            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                                Text(number.toString(), fontSize = 13.sp,
                                    color = when {
                                        chosen -> Color(0xFF192633)
                                        hasEvents -> Color.White
                                        else -> BackstageColors.pageText
                                    },
                                    fontWeight = if (chosen) FontWeight.Bold else FontWeight.Normal)
                                if (hasEvents) Text("•", fontSize = 10.sp, lineHeight = 10.sp,
                                    color = if (chosen) Color(0xFF192633) else BackstageColors.pink)
                            }
                        }
                    }
                }
            }
        }
    }
}
