package com.example.barrysconcertagenda

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.webkit.WebView
import android.webkit.WebViewClient
import android.webkit.CookieManager
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
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.viewinterop.AndroidView
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.graphics.Color
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.coroutines.launch
import java.time.LocalDate
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
            MaterialTheme {
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

@Composable
private fun TicketSwapLookupWebView(
    concert: Concert?,
    onResult: (String) -> Unit
) {
    val context = LocalContext.current
    val webView = remember {
        WebView(context).apply {
            settings.javaScriptEnabled = true
            settings.domStorageEnabled = true
            CookieManager.getInstance().setAcceptCookie(true)
        }
    }

    DisposableEffect(Unit) {
        onDispose { webView.destroy() }
    }

    LaunchedEffect(concert?.url) {
        val target = concert ?: return@LaunchedEffect
        val date = parseConcertDate(target.date)?.toString().orEmpty()
        val artistParts = ticketSwapSlugPartWeb(target.artist)
            .split("-").filter { it.length >= 2 }
        val city = ticketSwapSlugPartWeb(target.city)
        val venue = ticketSwapSlugPartWeb(target.venue)
        val query = listOf(target.artist, target.city, target.venue)
            .filter { it.isNotBlank() }.joinToString(" ")
        val jsQuery = org.json.JSONObject.quote(query)
        var searchSubmitted = false

        fun inspectResults(view: WebView, attempt: Int) {
            view.evaluateJavascript(
                """(function(){
                  const links=[...document.querySelectorAll('a')].map(a=>a.href).filter(Boolean);
                  return JSON.stringify(links);
                })();"""
            ) { raw ->
                val decoded = raw
                    .removeSurrounding("\"")
                    .replace("\\\\", "\\")
                    .replace("\\\"", "\"")
                    .replace("\\\\/", "/")
                val candidates = Regex("""https://www\\.ticketswap\\.nl/concert-tickets/[^"\\\\]+""")
                    .findAll(decoded).map { it.value }.distinct().toList()
                val exact = candidates.firstOrNull { candidate ->
                    val lower = candidate.lowercase(Locale.ROOT)
                    date.isNotBlank() && date in lower &&
                        artistParts.count { it in lower } >= maxOf(1, artistParts.size / 2) &&
                        (city.isBlank() || city in lower || venue in lower)
                }
                if (exact != null) {
                    onResult(exact)
                } else if (attempt < 6) {
                    view.postDelayed({ inspectResults(view, attempt + 1) }, 1200)
                } else {
                    onResult("ERROR:GEEN EXACTE MATCH · links ${candidates.size}")
                }
            }
        }

        webView.webViewClient = object : WebViewClient() {
            override fun onPageFinished(view: WebView, url: String) {
                if (url.contains("403") || view.title?.contains("403") == true) {
                    onResult("ERROR:HTTP 403")
                    return
                }

                if (!searchSubmitted) {
                    view.postDelayed({
                        view.evaluateJavascript(
                            """(function(){
                              const inputs=[...document.querySelectorAll('input')];
                              const input=inputs.find(i =>
                                (i.type||'').toLowerCase()==='search' ||
                                (i.placeholder||'').toLowerCase().includes('zoek') ||
                                (i.placeholder||'').toLowerCase().includes('search') ||
                                (i.getAttribute('aria-label')||'').toLowerCase().includes('zoek') ||
                                (i.getAttribute('aria-label')||'').toLowerCase().includes('search')
                              );
                              if(!input) return 'NO_SEARCH_INPUT';
                              input.focus();
                              const setter=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set;
                              setter.call(input,$jsQuery);
                              input.dispatchEvent(new Event('input',{bubbles:true}));
                              input.dispatchEvent(new Event('change',{bubbles:true}));
                              const form=input.closest('form');
                              if(form){ if(form.requestSubmit) form.requestSubmit(); else form.submit(); return 'FORM_SUBMITTED'; }
                              input.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',code:'Enter',keyCode:13,which:13,bubbles:true}));
                              input.dispatchEvent(new KeyboardEvent('keyup',{key:'Enter',code:'Enter',keyCode:13,which:13,bubbles:true}));
                              return 'ENTER_SENT';
                            })();"""
                        ) { result ->
                            if (result.contains("NO_SEARCH_INPUT")) {
                                onResult("ERROR:GEEN ZOEKVELD OP TICKETSWAP")
                            } else {
                                searchSubmitted = true
                                view.postDelayed({ inspectResults(view, 1) }, 1500)
                            }
                        }
                    }, 1500)
                } else {
                    view.postDelayed({ inspectResults(view, 1) }, 1200)
                }
            }
        }

        webView.loadUrl("https://www.ticketswap.nl/")
    }

    AndroidView(
        factory = { webView },
        modifier = Modifier.size(1.dp)
    )
}

private fun ticketSwapSlugPartWeb(value: String): String =
    java.text.Normalizer.normalize(value, java.text.Normalizer.Form.NFD)
        .replace(Regex("\\p{Mn}+"), "")
        .lowercase(Locale.ROOT)
        .replace("&", " ")
        .replace(Regex("[^a-z0-9]+"), "-")
        .trim('-')

@Composable
fun ConcertApp() {

    val context =
        LocalContext.current

    var selectedTab by remember {
        mutableStateOf(1)
    }

    var searchQuery by remember { mutableStateOf("") }
    var searchDateFrom by remember { mutableStateOf<LocalDate?>(null) }
    var searchDateTo by remember { mutableStateOf<LocalDate?>(null) }
    var datePickerTarget by remember { mutableStateOf<String?>(null) }
    var searchVenue by remember { mutableStateOf<String?>(null) }
    var venueMenuExpanded by remember { mutableStateOf(false) }
    var ticketSwapStatus by remember { mutableStateOf("") }
    var ticketSwapStatusUrl by remember { mutableStateOf("") }
    var ticketSwapLookupConcert by remember { mutableStateOf<Concert?>(null) }
    val coroutineScope = rememberCoroutineScope()

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

            } catch (_: Exception) {

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

        loading = false
    }

    val tabConcerts =
        when (
            selectedTab
        ) {

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

    val searchedConcerts =
        if (selectedTab != 6) {
            tabConcerts
        } else if (!hasSearchCriteria) {
            emptyList()
        } else {
            tabConcerts.filter { concert ->
                val textMatches =
                    normalizedSearch.isBlank() ||
                        concert.artist.lowercase(Locale.getDefault()).contains(normalizedSearch) ||
                        concert.venue.lowercase(Locale.getDefault()).contains(normalizedSearch)
                val venueMatches = searchVenue == null || concert.venue.equals(searchVenue, ignoreCase = true)
                val concertDate = parseConcertDate(concert.date)
                val dateMatches =
                    concertDate != null &&
                        (searchDateFrom == null || !concertDate.isBefore(searchDateFrom)) &&
                        (searchDateTo == null || !concertDate.isAfter(searchDateTo))
                textMatches && venueMatches && dateMatches
            }
        }

    val visibleConcerts =
        if (selectedTab == 0) {
            searchedConcerts.sortedByDescending { it.firstFound }
        } else {
            searchedConcerts
        }

    TicketSwapLookupWebView(
        concert = ticketSwapLookupConcert,
        onResult = { result ->
            val lookupConcert = ticketSwapLookupConcert ?: return@TicketSwapLookupWebView
            if (!result.startsWith("ERROR:")) {
                concerts = concerts.map {
                    if (normalizeUrl(it.url) == normalizeUrl(lookupConcert.url)) {
                        it.copy(ticketSwapUrl = result)
                    } else it
                }
                ConcertStorage.setTicketSwapUrl(context, lookupConcert.url, result)
                ticketSwapStatus = "TicketSwap gevonden"
            } else {
                ticketSwapStatus = "Nog niet gevonden op TicketSwap"
            }
            ticketSwapLookupConcert = null
        }
    )

    Scaffold(
        bottomBar = {

            NavigationBar {

                NavigationBarItem(
                    selected =
                        selectedTab == 0,
                    onClick = {
                        selectedTab = 0
                    },
                    icon = {
                        Text("✦", fontSize = 20.sp)
                    },
                )

                NavigationBarItem(
                    selected =
                        selectedTab == 1,
                    onClick = {
                        selectedTab = 1
                    },
                    icon = {
                        Text("☷", fontSize = 20.sp)
                    },
                )

                NavigationBarItem(
                    selected =
                        selectedTab == 2,
                    onClick = {
                        selectedTab = 2
                    },
                    icon = {
                        Text("♥", fontSize = 20.sp)
                    },
                )

                NavigationBarItem(
                    selected =
                        selectedTab == 4,
                    onClick = {
                        selectedTab = 4
                    },
                    icon = {
                        Text("♣", fontSize = 20.sp)
                    },
                )

                NavigationBarItem(
                    selected = selectedTab == 3,
                    onClick = { selectedTab = 3 },
                    icon = { Text("🎟", fontSize = 20.sp, color = Color(0xFF2E7D32)) }
                )

                NavigationBarItem(
                    selected = selectedTab == 5,
                    onClick = { selectedTab = 5 },
                    icon = { Text("▤", fontSize = 20.sp) }
                )

                NavigationBarItem(
                    selected = selectedTab == 6,
                    onClick = { selectedTab = 6 },
                    icon = { Text("⌕", fontSize = 20.sp) }
                )

                NavigationBarItem(
                    selected = selectedTab == 7,
                    onClick = { selectedTab = 7 },
                    icon = { Text("ⓘ", fontSize = 20.sp) }
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
                Text(
                    text = "Barry's concert agenda",
                    fontSize = 18.sp,
                    fontWeight = FontWeight.Bold,
                    maxLines = 1
                )
                Spacer(Modifier.width(5.dp))
                NetherlandsFlag()
                Spacer(Modifier.width(3.dp))
                BelgiumFlag()
            }

            if (selectedTab == 6) {
                OutlinedTextField(
                    value = searchQuery,
                    onValueChange = { searchQuery = it },
                    placeholder = { Text("Artiest of zaal…", fontSize = 12.sp) },
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

                                Text(
                                    "${visibleConcerts.size} aankomende concerten",
                                    fontWeight = FontWeight.Bold,
                                    maxLines = 1
                                )


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

                            7 -> {
                                Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                                    Text("Over Barry's concert agenda", fontWeight = FontWeight.Bold, fontSize = 18.sp)
                                    Text("Deze app verzamelt concertagenda's van geselecteerde Nederlandse en Belgische podia in één overzicht.")
                                    Text("Opgenomen zalen", fontWeight = FontWeight.Bold)
                                    val mainVenues = listOf("013", "Baroeg", "Boerderij", "dB's", "Effenaar", "Gebouw-T", "Melkweg", "MEZZ", "Paard", "Paradiso", "Patronaat", "Rotown", "TivoliVredenburg", "Tolhuistuin")
                                    mainVenues.forEach { mainVenue ->
                                        val subVenues = if (mainVenue == "013") emptyList() else concerts
                                            .filter { it.source.equals(mainVenue, ignoreCase = true) }
                                            .map { it.venue.trim() }
                                            .filter { it.isNotBlank() && !it.equals(mainVenue, ignoreCase = true) }
                                            .distinct()
                                            .sortedBy { it.lowercase(Locale.getDefault()) }
                                        Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
                                            Text(mainVenue, fontWeight = FontWeight.Bold, fontSize = 16.sp)
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
                                    if (ticketSwapStatus.isNotBlank()) {
                                        Text(ticketSwapStatus, style = MaterialTheme.typography.bodySmall)
                                    }
                                    Text("Bronnen & rechten", fontWeight = FontWeight.Bold)
                                    Text("Concertinformatie blijft eigendom van de betreffende podia, organisatoren en rechthebbenden. Deze app is een persoonlijk hulpmiddel en is niet gelieerd aan of officieel goedgekeurd door de genoemde podia. Via Bron open je altijd de oorspronkelijke concertpagina.")
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

                    items(
                        items =
                            visibleConcerts,
                        key = { concert ->

                            concert.url.ifBlank {

                                concert.artist +
                                        concert.date +
                                        concert.venue
                            }
                        }
                    ) { concert ->

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

                                if (newFavorite && concert.ticketSwapUrl.isBlank()) {
                                    ticketSwapStatusUrl = normalizeUrl(concert.url)
                                    ticketSwapStatus = "TicketSwap zoekt..."
                                    ticketSwapLookupConcert = concert
                                }
                            },
                            showClubCardLabel = selectedTab != 4,
                            showFavorite = selectedTab != 3 && selectedTab != 5,
                            ticketDisplay = when {
                                selectedTab == 5 -> TicketDisplay.VISITED
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

                    item {

                        Spacer(
                            modifier =
                                Modifier.height(
                                    20.dp
                                )
                        )
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
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(horizontal = 14.dp, vertical = 10.dp)) {
            Text(concert.artist, fontWeight = FontWeight.Bold, style = MaterialTheme.typography.titleMedium, maxLines = 1)
            Text(buildString { append(concert.venue); if (concert.country.isNotBlank()) append(" " + countryFlag(concert.country)) }, style = MaterialTheme.typography.bodyMedium)
            val displayDate = parseConcertDate(concert.date)?.format(DateTimeFormatter.ofPattern("d MMMM yyyy", Locale.forLanguageTag("nl-NL"))) ?: concert.date
            Text(if (concert.time.isBlank()) displayDate else "$displayDate · ${concert.time}", style = MaterialTheme.typography.bodyMedium)
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
            if (concert.isFavorite && concert.ticketSwapUrl.isBlank() && ticketSwapMessage.isNotBlank()) {
                Text(
                    text = ticketSwapMessage,
                    fontSize = 10.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(top = 2.dp)
                )
            }
            if (concert.isFavorite && !concert.isAttending && concert.ticketSwapUrl.isNotBlank()) {
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
                                Intent(Intent.ACTION_VIEW, Uri.parse(concert.ticketSwapUrl))
                            )
                        }
                )
            }
        }
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