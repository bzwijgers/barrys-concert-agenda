package com.example.barrysconcertagenda

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.Image
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.background
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.DatePicker
import androidx.compose.material3.DatePickerDialog
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.IconButton
import androidx.compose.material3.rememberDatePickerState
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.CardDefaults
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.BorderStroke
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.graphics.Color
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.coroutines.launch
import java.time.LocalDate
import java.time.YearMonth
import java.time.format.DateTimeFormatter
import java.util.Locale
import java.net.HttpURLConnection
import java.net.URL

data class Concert(
    val artist: String,
    val venue: String,
    val city: String,
    val country: String,
    val date: String,
    val time: String = "",
    val source: String = "",
    val url: String = "",
    val ticketSwapUrl: String = "",
    val firstFound: Long = 0L,
    val isNew: Boolean = false,
    val isFavorite: Boolean = false,
    val isAttending: Boolean = false,
    val archived: Boolean = false,
    val clubCard: Boolean = false
)

class MainActivity : ComponentActivity() {

    override fun onCreate(
        savedInstanceState: Bundle?
    ) {
        super.onCreate(savedInstanceState)

        setContent {
            MaterialTheme(colorScheme = darkColorScheme(
                primary = BackstageColors.pink,
                secondary = BackstageColors.lime,
                background = BackstageColors.background,
                surface = BackstageColors.surface,
                onSurface = Color.White,
                onBackground = Color.White
            )) {
                var showWelcome by remember {
                    mutableStateOf(true)
                }

                if (showWelcome) {
                    WelcomeScreen(
                        onOpenApp = {
                            showWelcome = false
                        }
                    )
                } else {
                    ConcertApp()
                }
            }
        }
    }
}


@Composable
fun WelcomeScreen(
    onOpenApp: () -> Unit
) {
    Image(
        painter = painterResource(
            id = R.drawable.barrys_concerten_splash
        ),
        contentDescription = "Barry's concert agenda",
        contentScale = androidx.compose.ui.layout.ContentScale.Crop,
        modifier =
            Modifier
                .fillMaxSize()
                .clickable(onClick = onOpenApp)
    )
}

private fun verifiedTicketSwapUrl(concert: Concert): String =
    if (
        concert.date == "2026-10-09" &&
        concert.artist.equals("The Apers", ignoreCase = true) &&
        concert.venue.equals("Rotown", ignoreCase = true) &&
        concert.url.trimEnd('/') == "https://www.rotown.nl/agenda/the-apers-1"
    ) {
        "https://www.ticketswap.nl/concert-tickets/maladroit-rotterdam-rotown-2026-10-09-CbSFR53UXMVxNKodxWTdf"
    } else if (
        concert.date == "2026-12-27" &&
        concert.artist.equals("30 Jaar Excelsior Recordings", ignoreCase = true) &&
        concert.venue.equals("Tolhuistuin", ignoreCase = true) &&
        concert.url.trimEnd('/') == "https://www.paradiso.nl/nl/programma/30-jaar-excelsior-recordings/2902321"
    ) {
        "https://www.ticketswap.nl/concert-tickets/30-jaar-excelsior-recordings-amsterdam-tolhuistuin-2026-12-27-CbhnzqXEdczxvu7WzXVv9"
    } else {
        concert.ticketSwapUrl
    }

@Composable
fun ConcertApp() {

    val context =
        LocalContext.current

    var selectedTab by remember {
        mutableStateOf(9)
    }

    var mySection by remember { mutableStateOf(3) }
    var discoveryFilter by remember { mutableStateOf("all") }
    var calendarMode by remember { mutableStateOf(true) }
    var calendarMonth by remember { mutableStateOf(YearMonth.now()) }
    var calendarDay by remember { mutableStateOf<LocalDate?>(null) }

    var searchExpanded by remember { mutableStateOf(false) }
    var searchQuery by remember { mutableStateOf("") }
    var searchDateFrom by remember { mutableStateOf<LocalDate?>(null) }
    var searchDateTo by remember { mutableStateOf<LocalDate?>(null) }
    var datePickerTarget by remember { mutableStateOf<String?>(null) }
    var searchVenue by remember { mutableStateOf<String?>(null) }
    var venueMenuExpanded by remember { mutableStateOf(false) }
    var ticketSwapStatus by remember { mutableStateOf("") }
    var ticketSwapStatusUrl by remember { mutableStateOf("") }

    var concerts by remember {
        mutableStateOf<List<Concert>>(
            emptyList()
        )
    }

    var loading by remember {
        mutableStateOf(true)
    }

    var statusText by remember {
        mutableStateOf(
            "Concerten controleren..."
        )
    }

    var paradisoDiagnostic by remember {
        mutableStateOf(
            "Paradiso wordt gecontroleerd..."
        )
    }

    LaunchedEffect(Unit) {

        loading = true

        statusText =
            "Concerten controleren..."

        val storedBefore =
            ConcertStorage.loadConcerts(
                context
            )

        val oldByUrl =
            storedBefore.associateBy {
                normalizeUrl(
                    it.url
                )
            }

        val setupPrefs =
            context.getSharedPreferences(
                "concert_source_setup",
                Context.MODE_PRIVATE
            )

        val paradisoAlreadyInitialized =
            setupPrefs.getBoolean(
                "paradiso_initialized",
                false
            )

        var sourceLoadError = ""

        val sourceConcerts =
            try {

                withContext(
                    Dispatchers.IO
                ) {

                    ConcertRepository
                        .getAllConcerts(
                            context = context
                        )
                }

            } catch (e: Exception) {

                sourceLoadError =
                    e.message
                        ?.takeIf { it.isNotBlank() }
                        ?: e.javaClass.simpleName

                emptyList()
            }

        paradisoDiagnostic =
            ParadisoSource.diagnosticInfo

        val now =
            System.currentTimeMillis()

        val newUrls =
            mutableSetOf<String>()

        val downloadedStored =
            sourceConcerts.map { source ->

                val normalizedUrl =
                    normalizeUrl(
                        source.url
                    )

                val old =
                    oldByUrl[
                        normalizedUrl
                    ]

                val isFirstParadisoBaseline =
                    source.source.equals(
                        "Paradiso",
                        ignoreCase = true
                    ) &&
                            !paradisoAlreadyInitialized

                if (
                    old == null &&
                    !isFirstParadisoBaseline
                ) {

                    newUrls.add(
                        normalizedUrl
                    )
                }

                StoredConcert(
                    artist = source.artist,
                    venue = source.venue,
                    city = source.city,
                    country = source.country,
                    date = source.date,
                    time = source.time,
                    source = source.source,
                    url = source.url,
                    ticketSwapUrl =
                        old?.ticketSwapUrl?.takeIf { it.isNotBlank() }
                            ?: source.ticketSwapUrl,
                    firstFound =
                        old?.firstFound
                            ?: now,
                    isFavorite =
                        old?.isFavorite
                            ?: false,
                    isAttending =
                        old?.isAttending
                            ?: false,
                    clubCard = source.clubCard
                )
            }

        val merged =
            linkedMapOf<String, StoredConcert>()

        storedBefore.forEach { concert ->

            val key =
                normalizeUrl(
                    concert.url
                )

            if (
                key.isNotBlank()
            ) {

                merged[key] =
                    concert
            }
        }

        downloadedStored.forEach { concert ->

            val key =
                normalizeUrl(
                    concert.url
                )

            if (
                key.isNotBlank()
            ) {

                val old =
                    merged[key]

                merged[key] =
                    concert.copy(
                        firstFound =
                            old?.firstFound
                                ?: concert.firstFound,
                        isFavorite =
                            old?.isFavorite
                                ?: concert.isFavorite,
                        isAttending =
                            old?.isAttending
                                ?: concert.isAttending,
                        ticketSwapUrl =
                            old?.ticketSwapUrl?.takeIf { it.isNotBlank() }
                                ?: concert.ticketSwapUrl,
                        clubCard = concert.clubCard
                    )
            }
        }

        val storedAfter =
            merged.values.map { concert ->
                if (
                    normalizeUrl(concert.url) ==
                    "https://www.rotown.nl/agenda/republica"
                ) {
                    concert.copy(isAttending = true)
                } else {
                    concert
                }
            }

        ConcertStorage.saveConcerts(
            context,
            storedAfter
        )

        val paradisoWasDownloaded =
            sourceConcerts.any {

                it.source.equals(
                    "Paradiso",
                    ignoreCase = true
                )
            }

        if (
            !paradisoAlreadyInitialized &&
            paradisoWasDownloaded
        ) {

            setupPrefs.edit()
                .putBoolean(
                    "paradiso_initialized",
                    true
                )
                .apply()
        }

        concerts =
            storedAfter
                .map { stored ->

                    Concert(
                        artist = stored.artist,
                        venue = stored.venue,
                        city = stored.city,
                        country = stored.country,
                        date = stored.date,
                        time = stored.time,
                        source = stored.source,
                        url = stored.url,
                        ticketSwapUrl = stored.ticketSwapUrl,
                        firstFound =
                            stored.firstFound,
                        isNew =
                            stored.firstFound > 0L &&
                            now - stored.firstFound <=
                                7L * 24L * 60L * 60L * 1000L,
                        isFavorite =
                            if (isPastConcert(stored.date) && stored.isAttending) {
                                false
                            } else {
                                stored.isFavorite
                            },
                        isAttending =
                            stored.isAttending,
                        clubCard = stored.clubCard,
                        archived =
                            isPastConcert(
                                stored.date
                            )
                    )
                }
                .sortedWith(
                    compareBy<Concert> {
                        concertSortDate(
                            it.date
                        )
                    }.thenBy {
                        it.time
                    }
                )

        ConcertStorage.setLastCheck(
            context,
            now
        )

        statusText =
            if (
                sourceConcerts.isEmpty()
            ) {

                "Geen nieuwe brongegevens ontvangen"

            } else {

                "Concerten gecontroleerd"
            }

        if (sourceLoadError.isNotBlank()) {
            statusText =
                "⚠ Concertagenda kon niet worden bijgewerkt. " +
                    "De laatst opgeslagen concerten blijven zichtbaar. " +
                    "Fout: " + sourceLoadError
        }

        loading = false
    }

    val tabConcerts =
        when (
            selectedTab
        ) {

            9 -> concerts.filter { !it.archived }

            10 -> concerts.filter { concert ->
                !concert.archived && when (discoveryFilter) {
                    "new" -> concert.isNew
                    "rotterdam" -> concert.city.equals("Rotterdam", ignoreCase = true)
                    "belgium" -> concert.country.equals("BE", ignoreCase = true) ||
                        concert.country.equals("Belgium", ignoreCase = true)
                    "club" -> concert.clubCard
                    else -> true
                }
            }

            11 -> concerts.filter {
                when (mySection) {
                    2 -> it.isFavorite && !it.archived
                    5 -> it.isAttending && it.archived
                    else -> it.isAttending && !it.archived
                }
            }

            0 ->
                concerts.filter {
                    it.isNew &&
                            !it.archived
                }

            1 ->
                concerts.filter {
                    !it.archived
                }

            2 ->
                concerts.filter {
                    it.isFavorite &&
                            !it.archived
                }

            3 ->
                concerts.filter {
                    it.isAttending &&
                            !it.archived
                }

            4 ->
                concerts.filter {
                    it.clubCard &&
                            !it.archived
                }

            5 ->
                concerts.filter {
                    it.isAttending &&
                            it.archived
                }

            6 ->
                concerts.filter {
                    !it.archived
                }

            7 ->
                emptyList()

            else ->
                emptyList()
        }

    val availableVenues = concerts.map { it.venue.trim() }.filter { it.isNotBlank() }.distinct().sortedBy { it.lowercase(Locale.getDefault()) }

    val normalizedSearch =
        searchQuery.trim().lowercase(Locale.getDefault())

    val hasSearchCriteria =
        normalizedSearch.isNotBlank() || searchDateFrom != null || searchDateTo != null || searchVenue != null

    // Search stays active when moving between Agenda, New, Favorites, Tickets,
    // Rotown Clubkaart and Archive. It never filters the More/Info menus.
    val searchedConcerts =
        if (!hasSearchCriteria || selectedTab == 7 || selectedTab == 8) {
            tabConcerts
        } else {
            tabConcerts.filter { concert ->
                val textMatches =
                    normalizedSearch.isBlank() ||
                        concert.artist.lowercase(Locale.getDefault()).contains(normalizedSearch) ||
                        concert.venue.lowercase(Locale.getDefault()).contains(normalizedSearch) ||
                        concert.city.lowercase(Locale.getDefault()).contains(normalizedSearch)
                val venueMatches =
                    searchVenue == null || concert.venue.equals(searchVenue, ignoreCase = true)
                val concertDate = parseConcertDate(concert.date)
                val dateMatches =
                    (searchDateFrom == null || (concertDate != null && !concertDate.isBefore(searchDateFrom))) &&
                    (searchDateTo == null || (concertDate != null && !concertDate.isAfter(searchDateTo)))
                textMatches && venueMatches && dateMatches
            }
        }

    val visibleConcerts =
        when {
            selectedTab == 0 || (selectedTab == 10 && discoveryFilter == "new") ->
                searchedConcerts.sortedByDescending { it.firstFound }
            selectedTab == 9 -> searchedConcerts.take(8)
            selectedTab == 1 && calendarMode -> searchedConcerts.filter { concert ->
                val parsed = parseConcertDate(concert.date)
                parsed != null && YearMonth.from(parsed) == calendarMonth &&
                    (calendarDay == null || parsed == calendarDay)
            }
            else -> searchedConcerts
        }


    // Check existing favorites sequentially when opening the Favorites tab.
    // Only one bounded network request is active at a time; switching tabs
    // cancels this scan. Known direct links are never overwritten.
    Scaffold(
        containerColor = BackstageColors.background,
        bottomBar = {
            NavigationBar(containerColor = Color(0xFF111B2B)) {
                NavigationBarItem(
                    selected = selectedTab == 9,
                    onClick = { selectedTab = 9 },
                    icon = { Text("⌂", fontSize = 23.sp) },
                    label = { Text("Home", fontSize = 10.sp) }
                )
                NavigationBarItem(
                    selected = selectedTab == 10,
                    onClick = { selectedTab = 10 },
                    icon = { Text("✦", fontSize = 21.sp) },
                    label = { Text("Ontdek", fontSize = 10.sp) }
                )
                NavigationBarItem(
                    selected = selectedTab == 1,
                    onClick = { selectedTab = 1 },
                    icon = { Text("▦", fontSize = 21.sp) },
                    label = { Text("Agenda", fontSize = 10.sp) }
                )
                NavigationBarItem(
                    selected = selectedTab == 11,
                    onClick = { selectedTab = 11 },
                    icon = { Text("♥", fontSize = 20.sp) },
                    label = { Text("Mijn", fontSize = 10.sp) }
                )
                NavigationBarItem(
                    selected = selectedTab in setOf(4, 5, 7, 8),
                    onClick = { selectedTab = 8 },
                    icon = { Text("⋯", fontSize = 23.sp) },
                    label = { Text("Meer", fontSize = 10.sp) }
                )
            }
        }
    ) { innerPadding ->

        Column(
            modifier =
                Modifier
                    .fillMaxSize()
                    .padding(
                        innerPadding
                    )
        ) {

            Row(
                modifier = Modifier.fillMaxWidth().padding(horizontal = 20.dp, vertical = 8.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text("BARRY'S", fontSize = 16.sp, fontWeight = FontWeight.ExtraBold)
                        Text(" / LIVE", color = BackstageColors.pink,
                            fontSize = 16.sp, fontWeight = FontWeight.ExtraBold)
                    }
                    Text("Concert agenda  🇳🇱 / 🇧🇪", fontSize = 10.sp,
                        color = BackstageColors.subtle)
                }
                IconButton(onClick = { searchExpanded = !searchExpanded }) {
                    Text(if (searchExpanded) "×" else "⌕",
                        fontSize = 27.sp, color = BackstageColors.pink)
                }
            }

            if (searchExpanded && selectedTab != 7 && selectedTab != 8) {
                OutlinedTextField(
                    value = searchQuery,
                    onValueChange = { searchQuery = it },
                    placeholder = { Text("Artiest, zaal of stad…", fontSize = 12.sp) },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth().padding(horizontal = 20.dp, vertical = 4.dp)
                )
                Box(modifier = Modifier.fillMaxWidth().padding(horizontal = 20.dp)) {
                    TextButton(onClick = { venueMenuExpanded = true }) {
                        Text("Zaal: " + (searchVenue ?: "Alle zalen"))
                    }
                    DropdownMenu(
                        expanded = venueMenuExpanded,
                        onDismissRequest = { venueMenuExpanded = false }
                    ) {
                        DropdownMenuItem(
                            text = { Text("Alle zalen") },
                            onClick = { searchVenue = null; venueMenuExpanded = false }
                        )
                        availableVenues.forEach { venue ->
                            DropdownMenuItem(
                                text = { Text(venue) },
                                onClick = { searchVenue = venue; venueMenuExpanded = false }
                            )
                        }
                    }
                }
                Row(
                    modifier = Modifier.fillMaxWidth().padding(horizontal = 20.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    TextButton(onClick = { datePickerTarget = "from" }, modifier = Modifier.weight(1f)) {
                        Text("Van: " + (searchDateFrom?.format(DateTimeFormatter.ofPattern("dd-MM-yyyy")) ?: "datum"))
                    }
                    Text(" t/m ", style = MaterialTheme.typography.bodySmall)
                    TextButton(onClick = { datePickerTarget = "to" }, modifier = Modifier.weight(1f)) {
                        Text("Tot: " + (searchDateTo?.format(DateTimeFormatter.ofPattern("dd-MM-yyyy")) ?: "datum"))
                    }
                }
                if (searchQuery.isNotBlank() || searchDateFrom != null || searchDateTo != null || searchVenue != null) {
                    TextButton(
                        onClick = { searchQuery = ""; searchDateFrom = null; searchDateTo = null; searchVenue = null },
                        modifier = Modifier.padding(start = 20.dp)
                    ) { Text("Zoekfilters wissen") }
                }
            }

            if (datePickerTarget != null) {
                BarryDatePicker(
                    initialDate = if (datePickerTarget == "from") searchDateFrom else searchDateTo,
                    onDismiss = { datePickerTarget = null },
                    onDateSelected = { picked ->
                        if (datePickerTarget == "from") {
                            searchDateFrom = picked
                            if (searchDateTo != null && picked.isAfter(searchDateTo)) searchDateTo = picked
                        } else {
                            searchDateTo = picked
                            if (searchDateFrom != null && picked.isBefore(searchDateFrom)) searchDateFrom = picked
                        }
                        datePickerTarget = null
                    }
                )
            }

            if (
                loading
            ) {

                Column(
                    modifier =
                        Modifier.padding(
                            20.dp
                        )
                ) {

                    Text(
                        "Concerten controleren...",
                        fontWeight =
                            FontWeight.Bold
                    )
                }

            } else {

                LazyColumn(
                    modifier =
                        Modifier
                            .fillMaxSize()
                            .padding(
                                horizontal =
                                    20.dp
                            ),
                    verticalArrangement =
                        Arrangement.spacedBy(
                            12.dp
                        )
                ) {

                    item {

                        when (
                            selectedTab
                        ) {

                            9 -> {
                                Column(verticalArrangement = Arrangement.spacedBy(14.dp)) {
                                    Text("JOUW LIVE OVERZICHT", fontSize = 11.sp,
                                        color = BackstageColors.pink,
                                        fontWeight = FontWeight.Bold, letterSpacing = 1.sp)
                                    Text("Jouw muziek.\nJouw concerten.",
                                        fontSize = 28.sp, lineHeight = 32.sp,
                                        fontWeight = FontWeight.ExtraBold)
                                    BackstageHero(
                                        concert = concerts.firstOrNull { it.isAttending && !it.archived },
                                        onTicketsClick = { mySection = 3; selectedTab = 11 }
                                    )
                                    BackstageQuickStats(
                                        tickets = concerts.count { it.isAttending && !it.archived },
                                        favorites = concerts.count { it.isFavorite && !it.archived },
                                        newShows = concerts.count { it.isNew && !it.archived },
                                        onTickets = { mySection = 3; selectedTab = 11 },
                                        onFavorites = { mySection = 2; selectedTab = 11 },
                                        onNew = { discoveryFilter = "new"; selectedTab = 10 }
                                    )
                                    Text("Binnenkort", fontSize = 20.sp,
                                        fontWeight = FontWeight.Bold)
                                }
                            }

                            10 -> {
                                Column(verticalArrangement = Arrangement.spacedBy(13.dp)) {
                                    Text("ONTDEK LIVE MUZIEK",
                                        fontSize = 11.sp, fontWeight = FontWeight.Bold,
                                        color = BackstageColors.pink)
                                    Text("Wat komt eraan?",
                                        fontWeight = FontWeight.ExtraBold, fontSize = 27.sp)
                                    Text("Ontdek optredens in Nederland en België",
                                        color = BackstageColors.subtle, fontSize = 12.sp)
                                    BackstageChips(
                                        options = listOf(
                                            "all" to "Alles", "new" to "✦ Nieuw",
                                            "rotterdam" to "Rotterdam", "belgium" to "🇧🇪 België",
                                            "club" to "♣ Clubkaart"
                                        ),
                                        current = discoveryFilter,
                                        onSelect = { discoveryFilter = it }
                                    )
                                    Text("${visibleConcerts.size} concerten", fontWeight = FontWeight.Bold)
                                }
                            }

                            11 -> {
                                Column(verticalArrangement = Arrangement.spacedBy(13.dp)) {
                                    Text("PERSOONLIJK", color = BackstageColors.pink,
                                        fontSize = 11.sp, fontWeight = FontWeight.Bold)
                                    Text("Mijn concerten.",
                                        fontWeight = FontWeight.ExtraBold, fontSize = 27.sp)
                                    BackstageChips(
                                        options = listOf(
                                            "3" to "🎟 Tickets",
                                            "2" to "♥ Favorieten",
                                            "5" to "▤ Archief"
                                        ),
                                        current = mySection.toString(),
                                        onSelect = { mySection = it.toInt() }
                                    )
                                    Text(
                                        when (mySection) {
                                            2 -> "${visibleConcerts.size} favorieten"
                                            5 -> "${visibleConcerts.size} bezochte concerten"
                                            else -> "${visibleConcerts.size} concerten waarvoor ik een kaartje heb"
                                        },
                                        fontWeight = FontWeight.Bold
                                    )
                                }
                            }

                            0 -> {

                                Text(
                                    "${visibleConcerts.size} nieuwe concerten",
                                    fontWeight =
                                        FontWeight.Bold
                                )

                                Text(
                                    "Nieuw in de afgelopen 7 dagen",
                                    style = MaterialTheme.typography.labelSmall
                                )
                            }

                            1 -> {
                                Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                                    Text("CONCERTOVERZICHT", color = BackstageColors.pink,
                                        fontSize = 11.sp, fontWeight = FontWeight.Bold)
                                    Text("Agenda.", fontSize = 27.sp,
                                        fontWeight = FontWeight.ExtraBold)
                                    BackstageChips(
                                        options = listOf("calendar" to "▦ Kalender", "list" to "☷ Lijst"),
                                        current = if (calendarMode) "calendar" else "list",
                                        onSelect = {
                                            calendarMode = it == "calendar"
                                            calendarDay = null
                                        }
                                    )
                                    if (calendarMode) {
                                        BackstageCalendar(
                                            month = calendarMonth,
                                            eventDays = searchedConcerts.mapNotNull {
                                                parseConcertDate(it.date)
                                            }.toSet(),
                                            selectedDay = calendarDay,
                                            onPrevious = {
                                                calendarMonth = calendarMonth.minusMonths(1)
                                                calendarDay = null
                                            },
                                            onNext = {
                                                calendarMonth = calendarMonth.plusMonths(1)
                                                calendarDay = null
                                            },
                                            onSelectDay = { calendarDay = it }
                                        )
                                    }
                                    Text(
                                        if (calendarMode)
                                            "${visibleConcerts.size} concerten in ${calendarMonth.month.name.lowercase(Locale.forLanguageTag("nl-NL"))}"
                                        else "${visibleConcerts.size} aankomende concerten",
                                        fontWeight = FontWeight.Bold
                                    )
                                }
                            }

                            2 -> {

                                Text(
                                    "${visibleConcerts.size} favorieten",
                                    fontWeight =
                                        FontWeight.Bold
                                )
                            }

                            3 -> {
                                Text(
                                    "${visibleConcerts.size} concerten waar ik naartoe ga",
                                    fontWeight = FontWeight.Bold,
                                    style = MaterialTheme.typography.bodyMedium,
                                    maxLines = 1
                                )
                            }

                            4 -> {

                                Text(
                                    "${visibleConcerts.size} Rotown Clubkaart concerten",
                                    fontWeight =
                                        FontWeight.Bold
                                )

                            }

                            5 -> {

                                Text(
                                    "${visibleConcerts.size} bezochte concerten",
                                    fontWeight = FontWeight.Bold
                                )
                            }

                            6 -> {
                                if (hasSearchCriteria) {
                                    Text(
                                        "${visibleConcerts.size} gevonden concerten",
                                        fontWeight = FontWeight.Bold,
                                        maxLines = 1
                                    )
                                } else {
                                    Text(
                                        "Zoek op artiest, zaal of datum",
                                        fontWeight = FontWeight.Bold,
                                        maxLines = 1
                                    )
                                }
                            }

                            8 -> {
                                Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                                    Text("Meer", fontWeight = FontWeight.Bold, fontSize = 21.sp)
                                    Text("Je concerten en aanvullende overzichten",
                                        style = MaterialTheme.typography.bodySmall)
                                    listOf(
                                        4 to "♣   Rotown Clubkaart",
                                        11 to "♥   Mijn concerten en archief",
                                        7 to "ⓘ   Info en concertzalen"
                                    ).forEach { (targetTab, title) ->
                                        Card(
                                            modifier = Modifier.fillMaxWidth()
                                                .clickable { selectedTab = targetTab }
                                        ) {
                                            Text(
                                                text = title,
                                                modifier = Modifier.padding(18.dp),
                                                fontWeight = FontWeight.Medium,
                                                fontSize = 16.sp
                                            )
                                        }
                                    }
                                }
                            }

                            7 -> {
                                Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                                    Text("Over Barry's concert agenda", fontWeight = FontWeight.Bold, fontSize = 18.sp)
                                    Text("Deze app verzamelt concertagenda's van geselecteerde Nederlandse en Belgische podia in één overzicht.")
                                    Text("Concertzalen", fontWeight = FontWeight.Bold)
                                    val venueCities = mapOf(
                                        "013" to "Tilburg", "Amare" to "Den Haag",
                                        "Baroeg" to "Rotterdam", "BIRD" to "Rotterdam",
                                        "Bibelot" to "Dordrecht", "Boerderij" to "Zoetermeer",
                                        "Bolwerk" to "Sneek", "dB's" to "Utrecht",
                                        "De Bosuil" to "Weert", "De Helling" to "Utrecht",
                                        "De Pul" to "Uden", "Doornroosje" to "Nijmegen",
                                        "Dynamo" to "Eindhoven", "Effenaar" to "Eindhoven",
                                        "Gebouw-T" to "Bergen op Zoom", "Hedon" to "Zwolle",
                                        "Klokgebouw" to "Eindhoven", "Melkweg" to "Amsterdam",
                                        "MEZZ" to "Breda", "Metropool" to "Hengelo / Enschede / Almelo",
                                        "Neushoorn" to "Leeuwarden", "PAARD" to "Den Haag",
                                        "Paradiso" to "Amsterdam", "Patronaat" to "Haarlem",
                                        "Rotown" to "Rotterdam", "SPOT Groningen" to "Groningen",
                                        "TivoliVredenburg" to "Utrecht", "Tolhuistuin" to "Amsterdam"
                                    )
                                    val pendingVenues = emptySet<String>()
                                    venueCities.keys.sortedWith(String.CASE_INSENSITIVE_ORDER).forEach { mainVenue ->
                                        val subVenues = concerts
                                            .filter { it.source.equals(mainVenue, ignoreCase = true) }
                                            .map { it.venue.trim() }
                                            .filter { it.isNotBlank() && !it.equals(mainVenue, ignoreCase = true) }
                                            .distinct()
                                            .sortedWith(String.CASE_INSENSITIVE_ORDER)
                                        Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
                                            Text(
                                                mainVenue + " — " + venueCities.getValue(mainVenue) +
                                                    if (mainVenue in pendingVenues) " (in voorbereiding)" else "",
                                                fontWeight = FontWeight.Bold,
                                                fontSize = 16.sp
                                            )
                                            if (subVenues.isNotEmpty()) {
                                                Text(
                                                    "(" + subVenues.joinToString(" · ") + ")",
                                                    style = MaterialTheme.typography.bodySmall
                                                )
                                            }
                                        }
                                    }
                                    Text("Betekenis iconen", fontWeight = FontWeight.Bold)
                                    Text("♥ Favoriet   ·   🎟 Tickets   ·   ♣ Rotown Clubkaart   ·   ⌕ Zoeken")
                                    Text("Bronnen & rechten", fontWeight = FontWeight.Bold)
                                    Text("Concertinformatie blijft eigendom van de betreffende podia, organisatoren en rechthebbenden. Deze app is een persoonlijk hulpmiddel en is niet gelieerd aan of officieel goedgekeurd door de genoemde podia. Via Bron open je de bijbehorende evenementpagina van de vermelde bron.")
                                    Text("Barry's concert agenda", style = MaterialTheme.typography.labelSmall)
                                }
                            }
                        }

                        Spacer(
                            modifier =
                                Modifier.height(
                                    10.dp
                                )
                        )
                    }

                    itemsIndexed(
                        items = visibleConcerts,
                        key = { _, concert ->
                            concert.url.ifBlank {
                                concert.artist + concert.date + concert.venue
                            }
                        }
                    ) { index, concert ->
                        Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                            if (selectedTab in setOf(1, 2, 3, 4, 5, 10, 11) &&
                                (index == 0 || concert.date != visibleConcerts[index - 1].date)
                            ) {
                                val groupDate = parseConcertDate(concert.date)
                                    ?.format(DateTimeFormatter.ofPattern(
                                        "EEEE d MMMM yyyy",
                                        Locale.forLanguageTag("nl-NL")
                                    )) ?: concert.date
                                Text(
                                    text = groupDate,
                                    fontWeight = FontWeight.SemiBold,
                                    color = MaterialTheme.colorScheme.primary,
                                    modifier = Modifier.padding(top = 12.dp, bottom = 2.dp)
                                )
                            }
                            ConcertCard(
                            concert =
                                concert,
                            onFavoriteClick = {

                                val newFavorite =
                                    !concert.isFavorite

                                concerts =
                                    concerts.map {

                                        if (
                                            normalizeUrl(
                                                it.url
                                            ) ==
                                            normalizeUrl(
                                                concert.url
                                            )
                                        ) {

                                            it.copy(
                                                isFavorite =
                                                    newFavorite
                                            )

                                        } else {

                                            it
                                        }
                                    }

                                ConcertStorage.setFavorite(
                                    context = context,
                                    url = concert.url,
                                    favorite = newFavorite
                                )

                                // One safe background lookup; no hidden WebView.
                                // A blocked search returns no result and never closes the app.
                                // All verified direct TicketSwap links come from the
                                // central concerts feed. Do not start a WebView or
                                // an unreliable search request on favorite taps.

                            },
                            showClubCardLabel = selectedTab != 4,
                            showFavorite = selectedTab != 3 && selectedTab != 5 &&
                                !(selectedTab == 11 && mySection != 2),
                            ticketDisplay = when {
                                selectedTab == 5 || (selectedTab == 11 && mySection == 5) -> TicketDisplay.VISITED
                                concert.isAttending -> TicketDisplay.OWNED
                                else -> TicketDisplay.DEFAULT
                            },
                            onAttendingClick = {
                                val newAttending = !concert.isAttending
                                concerts = concerts.map {
                                    if (normalizeUrl(it.url) == normalizeUrl(concert.url)) {
                                        it.copy(isAttending = newAttending)
                                    } else {
                                        it
                                    }
                                }
                                ConcertStorage.setAttending(
                                    context = context,
                                    url = concert.url,
                                    attending = newAttending
                                )
                            },
                            ticketSwapMessage =
                                if (ticketSwapStatusUrl == normalizeUrl(concert.url)) ticketSwapStatus else ""
                            )
                        }
                    }

                    item {
                        if (visibleConcerts.isEmpty() && selectedTab in setOf(1, 9, 10, 11)) {
                            Text("Geen concerten in dit overzicht.",
                                color = BackstageColors.subtle,
                                modifier = Modifier.padding(vertical = 20.dp))
                        }
                        Spacer(modifier = Modifier.height(20.dp))
                    }
                }
            }
        }
    }
}

enum class TicketDisplay { DEFAULT, OWNED, VISITED }

@Composable
fun TicketStatusIcon(display: TicketDisplay) {
    val ticketColor = when (display) {
        TicketDisplay.DEFAULT -> Color(0xFFD32F2F)
        TicketDisplay.OWNED -> Color(0xFF2E7D32)
        TicketDisplay.VISITED -> Color.White
    }
    val borderColor = when (display) {
        TicketDisplay.VISITED -> MaterialTheme.colorScheme.onSurfaceVariant
        else -> ticketColor
    }

    Box(
        modifier = Modifier.size(32.dp),
        contentAlignment = Alignment.Center
    ) {
        Canvas(modifier = Modifier.size(width = 29.dp, height = 21.dp)) {
            val stroke = 1.7.dp.toPx()
            val notch = 3.5.dp.toPx()
            val path = androidx.compose.ui.graphics.Path().apply {
                moveTo(notch, 0f)
                lineTo(size.width - notch, 0f)
                lineTo(size.width - notch, 2.dp.toPx())
                quadraticBezierTo(size.width, 2.dp.toPx(), size.width, 5.dp.toPx())
                lineTo(size.width, size.height - 5.dp.toPx())
                quadraticBezierTo(size.width, size.height - 2.dp.toPx(), size.width - notch, size.height - 2.dp.toPx())
                lineTo(size.width - notch, size.height)
                lineTo(notch, size.height)
                lineTo(notch, size.height - 2.dp.toPx())
                quadraticBezierTo(0f, size.height - 2.dp.toPx(), 0f, size.height - 5.dp.toPx())
                lineTo(0f, 5.dp.toPx())
                quadraticBezierTo(0f, 2.dp.toPx(), notch, 2.dp.toPx())
                close()
            }
            drawPath(path = path, color = ticketColor)
            drawPath(
                path = path,
                color = borderColor,
                style = androidx.compose.ui.graphics.drawscope.Stroke(width = stroke)
            )
            val perforationX = size.width * 0.28f
            drawLine(
                color = if (display == TicketDisplay.VISITED) borderColor else Color.White,
                start = androidx.compose.ui.geometry.Offset(perforationX, 3.dp.toPx()),
                end = androidx.compose.ui.geometry.Offset(perforationX, size.height - 3.dp.toPx()),
                strokeWidth = 1.2.dp.toPx()
            )
        }

        if (display == TicketDisplay.VISITED) {
            Text(
                "✓",
                color = Color(0xFF2E7D32),
                fontSize = 24.sp,
                fontWeight = FontWeight.Black
            )
        }
    }
}

@Composable
fun NetherlandsFlag() {
    Column(modifier = Modifier.width(22.dp).height(15.dp)) {
        Box(Modifier.weight(1f).fillMaxWidth().background(Color(0xFFAE1C28)))
        Box(Modifier.weight(1f).fillMaxWidth().background(Color.White))
        Box(Modifier.weight(1f).fillMaxWidth().background(Color(0xFF21468B)))
    }
}

@Composable
fun BelgiumFlag() {
    Row(modifier = Modifier.width(22.dp).height(15.dp)) {
        Box(Modifier.weight(1f).fillMaxSize().background(Color.Black))
        Box(Modifier.weight(1f).fillMaxSize().background(Color(0xFFFDE100)))
        Box(Modifier.weight(1f).fillMaxSize().background(Color(0xFFEF3340)))
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun BarryDatePicker(initialDate: LocalDate? = null, onDismiss: () -> Unit, onDateSelected: (LocalDate) -> Unit) {
    val initialMillis = initialDate?.atStartOfDay(java.time.ZoneOffset.UTC)?.toInstant()?.toEpochMilli()
    val state = rememberDatePickerState(initialSelectedDateMillis = initialMillis)
    DatePickerDialog(onDismissRequest = onDismiss, confirmButton = {
        TextButton(onClick = { state.selectedDateMillis?.let { millis -> onDateSelected(java.time.Instant.ofEpochMilli(millis).atZone(java.time.ZoneOffset.UTC).toLocalDate()) } }) { Text("Kiezen") }
    }, dismissButton = { TextButton(onClick = onDismiss) { Text("Annuleren") } }) { DatePicker(state = state) }
}

@Composable
fun ConcertCard(concert: Concert, onFavoriteClick: () -> Unit, showClubCardLabel: Boolean, showFavorite: Boolean, ticketDisplay: TicketDisplay, onAttendingClick: () -> Unit, ticketSwapMessage: String = "") {
    var confirmFavoriteRemoval by remember { mutableStateOf(false) }
    var confirmAttendingRemoval by remember { mutableStateOf(false) }
    if (confirmFavoriteRemoval) AlertDialog(onDismissRequest = { confirmFavoriteRemoval = false }, title = { Text("Favoriet verwijderen?") }, text = { Text("Wil je dit concert uit je favorieten verwijderen?") }, confirmButton = { TextButton(onClick = { confirmFavoriteRemoval = false; onFavoriteClick() }) { Text("Verwijderen") } }, dismissButton = { TextButton(onClick = { confirmFavoriteRemoval = false }) { Text("Annuleren") } })
    if (confirmAttendingRemoval) AlertDialog(onDismissRequest = { confirmAttendingRemoval = false }, title = { Text("Concert verwijderen uit Tickets?") }, text = { Text("Wil je aangeven dat je niet meer naar dit concert gaat?") }, confirmButton = { TextButton(onClick = { confirmAttendingRemoval = false; onAttendingClick() }) { Text("Verwijderen") } }, dismissButton = { TextButton(onClick = { confirmAttendingRemoval = false }) { Text("Annuleren") } })
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = BackstageColors.surface),
        border = BorderStroke(1.dp, Color(0xFF29384E))
    ) {
        Column(modifier = Modifier.padding(horizontal = 15.dp, vertical = 12.dp)) {
            Text(concert.artist, fontWeight = FontWeight.ExtraBold,
                fontSize = 16.sp, maxLines = 2)
            Text(buildString {
                append(concert.venue)
                if (concert.city.isNotBlank() && !concert.venue.contains(concert.city, ignoreCase = true)) {
                    append(" · " + concert.city)
                }
                if (concert.country.isNotBlank()) append(" " + countryFlag(concert.country))
            }, style = MaterialTheme.typography.bodyMedium)
            val displayDate = parseConcertDate(concert.date)?.format(DateTimeFormatter.ofPattern("d MMMM yyyy", Locale.forLanguageTag("nl-NL"))) ?: concert.date
            Text(if (concert.time.isBlank()) displayDate else "$displayDate · ${concert.time}",
                style = MaterialTheme.typography.bodySmall,
                color = BackstageColors.subtle)
            if (concert.clubCard && showClubCardLabel) Text("ROTOWN CLUBKAART", fontWeight = FontWeight.Bold, style = MaterialTheme.typography.labelSmall)
            Row(modifier = Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                val context = LocalContext.current
                Text(text = if (concert.source.isBlank()) "" else "Bron: ${concert.source.replace("PAARD", "Paard")}", fontSize = 10.sp, maxLines = 1, color = if (concert.url.isNotBlank()) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurfaceVariant, textDecoration = if (concert.url.isNotBlank()) androidx.compose.ui.text.style.TextDecoration.Underline else null, modifier = Modifier.weight(1f).then(if (concert.url.isNotBlank()) Modifier.clickable { context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(concert.url))) } else Modifier))
                TextButton(
                    modifier = Modifier.size(38.dp),
                    contentPadding = androidx.compose.foundation.layout.PaddingValues(0.dp),
                    onClick = { if (concert.isAttending) confirmAttendingRemoval = true else onAttendingClick() }
                ) {
                    TicketStatusIcon(display = ticketDisplay)
                }
                if (showFavorite) {
                    TextButton(modifier = Modifier.size(38.dp), contentPadding = androidx.compose.foundation.layout.PaddingValues(0.dp), onClick = { if (concert.isFavorite) confirmFavoriteRemoval = true else onFavoriteClick() }) { Text(if (concert.isFavorite) "♥" else "♡", fontSize = 20.sp) }
                }
            }
            if (concert.isFavorite && verifiedTicketSwapUrl(concert).isBlank() && ticketSwapMessage.isNotBlank()) {
                Text(
                    text = ticketSwapMessage,
                    fontSize = 10.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(top = 2.dp)
                )
            }
            if (concert.isFavorite && verifiedTicketSwapUrl(concert).isNotBlank()) {
                val context = LocalContext.current
                Text(
                    text = "TicketSwap",
                    fontSize = 11.sp,
                    color = MaterialTheme.colorScheme.primary,
                    textDecoration = androidx.compose.ui.text.style.TextDecoration.Underline,
                    modifier = Modifier
                        .padding(top = 2.dp)
                        .clickable {
                            context.startActivity(
                                Intent(Intent.ACTION_VIEW, Uri.parse(verifiedTicketSwapUrl(concert)))
                            )
                        }
                )
            }
        }
    }
}




private suspend fun probeTicketSwapFromPhone(): String =
    withContext(Dispatchers.IO) {
        try {
            fun absoluteTicketSwapUrl(src: String): String = when {
                src.startsWith("https://") || src.startsWith("http://") -> src
                src.startsWith("//") -> "https:" + src
                src.startsWith("/") -> "https://www.ticketswap.nl" + src
                else -> "https://www.ticketswap.nl/" + src
            }
            fun getText(url: String): Pair<Int, String> {
                val connection = (URL(url).openConnection() as HttpURLConnection).apply {
                    requestMethod = "GET"; connectTimeout = 15000; readTimeout = 15000; instanceFollowRedirects = true
                    setRequestProperty("User-Agent", "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/124 Mobile Safari/537.36")
                    setRequestProperty("Accept-Language", "nl-NL,nl;q=0.9,en;q=0.8")
                }
                val code = connection.responseCode
                val stream = if (code in 200..399) connection.inputStream else connection.errorStream
                val body = stream?.bufferedReader()?.use { it.readText() }.orEmpty()
                connection.disconnect()
                return code to body
            }
            val page = getText("https://www.ticketswap.nl/netherlands")
            val code = page.first
            val normalizedBody = page.second.replace("\\\\/", "/")
            val jamesBlakeUrl = Regex(
                """https://www\\.ticketswap\\.nl/concert-tickets/james-blake-utrecht-tivolivredenburg-2026-10-06-[A-Za-z0-9]+""",
                RegexOption.IGNORE_CASE
            ).find(normalizedBody)?.value
            if (jamesBlakeUrl != null) return@withContext "TicketSwap test: GEVONDEN · " + jamesBlakeUrl

            val scriptSources = Regex("""<script[^>]+src=["']([^"']+)["']""", RegexOption.IGNORE_CASE)
                .findAll(normalizedBody).map { absoluteTicketSwapUrl(it.groupValues[1]) }.distinct().toList()
            val interesting = mutableListOf<String>()
            var checked = 0
            for (scriptUrl in scriptSources.take(36)) {
                try {
                    val script = getText(scriptUrl)
                    if (script.first !in 200..399 || script.second.isBlank()) continue
                    checked++
                    val normalizedScript = script.second.replace("\\\\/", "/")
                    val pattern = Regex("""["']([^"']*(?:graphql|search|algolia|elastic)[^"']*)["']""", RegexOption.IGNORE_CASE)
                    pattern.findAll(normalizedScript).forEach { match ->
                        val value = match.groupValues[1].take(220)
                        if (value.contains("graphql", true) || value.contains("search", true) || value.contains("algolia", true)) interesting.add(value)
                    }
                    if (interesting.distinct().size >= 5) break
                } catch (_: Exception) {}
            }
            val hints = interesting.distinct().take(5)
            if (hints.isEmpty()) {
                "TicketSwap JS test: HTTP " + code + " · scripts " + scriptSources.size + " · " + checked + " gelezen · geen search/API hint"
            } else {
                "TicketSwap JS test: " + checked + " scripts gelezen · " + hints.joinToString(" | ")
            }
        } catch (error: Exception) {
            "TicketSwap test mislukt: " + error.javaClass.simpleName + ": " + error.message.orEmpty().take(80)
        }
    }

private fun normalizeUrl(
    url: String
): String {

    return url
        .trim()
        .trimEnd('/')
        .lowercase()
}

private fun countryFlag(
    country: String
): String {

    return when (
        country.uppercase()
    ) {

        "NL" ->
            "🇳🇱"

        "BE" ->
            "🇧🇪"

        else ->
            country
    }
}

private fun isPastConcert(
    date: String
): Boolean {

    val parsed =
        parseConcertDate(
            date
        )
            ?: return false

    return parsed.isBefore(
        LocalDate.now()
    )
}

private fun concertSortDate(
    date: String
): LocalDate {

    return parseConcertDate(
        date
    )
        ?: LocalDate.of(
            9999,
            12,
            31
        )
}

private fun parseConcertDate(
    date: String
): LocalDate? {

    val cleaned =
        date.trim()

    try {

        val formatter =
            DateTimeFormatter.ofPattern(
                "d MMMM yyyy",
                Locale.forLanguageTag(
                    "nl-NL"
                )
            )

        return LocalDate.parse(
            cleaned.lowercase(),
            formatter
        )

    } catch (_: Exception) {
    }

    try {

        return LocalDate.parse(
            cleaned
        )

    } catch (_: Exception) {
    }

    return null
}