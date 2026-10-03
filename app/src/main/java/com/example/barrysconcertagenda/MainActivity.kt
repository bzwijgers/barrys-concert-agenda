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
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
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
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.time.LocalDate
import java.time.format.DateTimeFormatter
import java.util.Locale

data class Concert(
    val artist: String,
    val venue: String,
    val city: String,
    val country: String,
    val date: String,
    val time: String = "",
    val source: String = "",
    val url: String = "",
    val firstFound: Long = 0L,
    val isNew: Boolean = false,
    val isFavorite: Boolean = false,
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
            id = R.drawable.barrys_concert_agenda_logo
        ),
        contentDescription = "Barry's concert agenda",
        contentScale = androidx.compose.ui.layout.ContentScale.Fit,
        modifier =
            Modifier
                .fillMaxSize()
                .clickable(onClick = onOpenApp)
    )
}

@Composable
fun ConcertApp() {

    val context =
        LocalContext.current

    var selectedTab by remember {
        mutableStateOf(1)
    }

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
                    firstFound =
                        old?.firstFound
                            ?: now,
                    isFavorite =
                        old?.isFavorite
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
                        clubCard = concert.clubCard
                    )
            }
        }

        val storedAfter =
            merged.values.toList()

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
                        firstFound =
                            stored.firstFound,
                        isNew =
                            normalizeUrl(
                                stored.url
                            ) in newUrls,
                        isFavorite =
                            stored.isFavorite,
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

    val visibleConcerts =
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
                    it.archived
                }

            4 ->
                concerts.filter {
                    it.clubCard &&
                            !it.archived
                }

            else ->
                emptyList()
        }

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
                        Text("●")
                    },
                    label = {
                        Text("Nieuw")
                    }
                )

                NavigationBarItem(
                    selected =
                        selectedTab == 1,
                    onClick = {
                        selectedTab = 1
                    },
                    icon = {
                        Text("≡")
                    },
                    label = {
                        Text("Concerten")
                    }
                )

                NavigationBarItem(
                    selected =
                        selectedTab == 2,
                    onClick = {
                        selectedTab = 2
                    },
                    icon = {
                        Text("♥")
                    },
                    label = {
                        Text("Favorieten")
                    }
                )

                NavigationBarItem(
                    selected =
                        selectedTab == 4,
                    onClick = {
                        selectedTab = 4
                    },
                    icon = {
                        Text("♣")
                    },
                    label = {
                        Text("Clubkaart")
                    }
                )

                NavigationBarItem(
                    selected =
                        selectedTab == 3,
                    onClick = {
                        selectedTab = 3
                    },
                    icon = {
                        Text("▣")
                    },
                    label = {
                        Text("Archief")
                    }
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

            Column(
                modifier =
                    Modifier
                        .fillMaxWidth()
                        .padding(
                            horizontal = 20.dp,
                            vertical = 18.dp
                        )
            ) {

                Text(
                    text =
                        "Barry's concert agenda",
                    style =
                        MaterialTheme
                            .typography
                            .headlineMedium,
                    fontWeight =
                        FontWeight.Bold,
                    maxLines = 1
                )

                Text(
                    text =
                        "Nederland & België",
                    style =
                        MaterialTheme
                            .typography
                            .titleLarge
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
                                    "Nieuw sinds deze controle"
                                )
                            }

                            1 -> {

                                Text(
                                    "${visibleConcerts.size} komende concerten",
                                    fontWeight =
                                        FontWeight.Bold
                                )

                                Text(
                                    "Rotown + 013 + Paradiso + Baroeg + Effenaar"
                                )
                            }

                            2 -> {

                                Text(
                                    "${visibleConcerts.size} favorieten",
                                    fontWeight =
                                        FontWeight.Bold
                                )
                            }

                            4 -> {

                                Text(
                                    "${visibleConcerts.size} Rotown Clubkaart concerten",
                                    fontWeight =
                                        FontWeight.Bold
                                )

                                Text(
                                    "Gratis toegankelijk met de Rotown Clubkaart"
                                )
                            }

                            3 -> {

                                Text(
                                    "${visibleConcerts.size} concerten in archief",
                                    fontWeight =
                                        FontWeight.Bold
                                )

                                Text(
                                    "Concerten waarvan de datum is verstreken"
                                )
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
                                    context =
                                        context,
                                    url =
                                        concert.url,
                                    favorite =
                                        newFavorite
                                )
                            }
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

@Composable
fun ConcertCard(
    concert: Concert,
    onFavoriteClick: () -> Unit
) {

    Card(
        modifier =
            Modifier.fillMaxWidth()
    ) {

        Column(
            modifier =
                Modifier.padding(
                    16.dp
                )
        ) {

            Row(
                modifier =
                    Modifier.fillMaxWidth(),
                horizontalArrangement =
                    Arrangement.SpaceBetween
            ) {

                Text(
                    text =
                        concert.artist,
                    modifier =
                        Modifier.weight(
                            1f
                        ),
                    fontWeight =
                        FontWeight.Bold,
                    style =
                        MaterialTheme
                            .typography
                            .titleLarge
                )

                TextButton(
                    onClick =
                        onFavoriteClick
                ) {

                    Text(
                        if (
                            concert.isFavorite
                        ) {
                            "♥"
                        } else {
                            "♡"
                        }
                    )
                }
            }

            if (
                concert.isNew
            ) {

                Text(
                    "NIEUW",
                    fontWeight =
                        FontWeight.Bold
                )

                Spacer(
                    modifier =
                        Modifier.height(
                            4.dp
                        )
                )
            }

            val displayDate =
                parseConcertDate(
                    concert.date
                )?.format(
                    DateTimeFormatter.ofPattern(
                        "d MMMM yyyy",
                        Locale.forLanguageTag(
                            "nl-NL"
                        )
                    )
                )
                    ?: concert.date

            val dateAndTime =
                if (
                    concert.time.isBlank()
                ) {

                    displayDate

                } else {

                    "$displayDate · ${concert.time}"
                }

            Text(
                dateAndTime
            )

            Spacer(
                modifier =
                    Modifier.height(
                        4.dp
                    )
            )

            Text(
                buildString {

                    append(
                        concert.venue
                    )

                    if (
                        concert.city.isNotBlank()
                    ) {

                        append(
                            " · ${concert.city}"
                        )
                    }

                    if (
                        concert.country.isNotBlank()
                    ) {

                        append(
                            " ${countryFlag(concert.country)}"
                        )
                    }
                }
            )

            if (
                concert.clubCard
            ) {
                Spacer(
                    modifier = Modifier.height(6.dp)
                )

                Text(
                    "ROTOWN CLUBKAART",
                    fontWeight = FontWeight.Bold
                )
            }

            if (
                concert.source.isNotBlank()
            ) {

                Spacer(
                    modifier =
                        Modifier.height(
                            6.dp
                        )
                )

                val context = LocalContext.current

                Text(
                    text = "Bron: ${concert.source}",
                    style =
                        MaterialTheme
                            .typography
                            .bodySmall,
                    color =
                        if (concert.url.isNotBlank()) {
                            MaterialTheme.colorScheme.primary
                        } else {
                            MaterialTheme.colorScheme.onSurfaceVariant
                        },
                    textDecoration =
                        if (concert.url.isNotBlank()) {
                            androidx.compose.ui.text.style.TextDecoration.Underline
                        } else {
                            null
                        },
                    modifier =
                        if (concert.url.isNotBlank()) {
                            Modifier.clickable {
                                context.startActivity(
                                    Intent(
                                        Intent.ACTION_VIEW,
                                        Uri.parse(concert.url)
                                    )
                                )
                            }
                        } else {
                            Modifier
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