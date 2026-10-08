from .common import *

# ============================================================
# PARADISO
# ============================================================

PARADISO_AGENDA_URLS = (
    "https://www.paradiso.nl/landing/concertagenda-paradiso/2069817",
    "https://www.paradiso.nl/landing/programma-in-tolhuistuin/689946",
)

PARADISO_BASE_URL = "https://www.paradiso.nl"


def paradiso_find_program_urls(html):
    cleaned_html = (
        html
        .replace("\\/", "/")
        .replace("\\u002F", "/")
        .replace("\\u002f", "/")
        .replace("\\u0026", "&")
    )

    urls = []

    absolute_regex = re.compile(
        r"https://(?:www\.)?"
        r"paradiso\.nl/nl/programma/"
        r"[A-Za-z0-9_%+.\-]+/\d+",
        flags=re.IGNORECASE,
    )

    for match in absolute_regex.finditer(
        cleaned_html
    ):
        event_url = (
            match.group(0)
            .split("?", 1)[0]
            .split("#", 1)[0]
            .rstrip("/")
        )

        urls.append(event_url)

    relative_regex = re.compile(
        r"/(?:nl/)?programma/"
        r"[A-Za-z0-9_%+.\-]+/\d+",
        flags=re.IGNORECASE,
    )

    # De agenda levert programma-URLs ook JSON-geescaped aan,
    # niet alleen als normale hrefs. Pak daarom alle zichtbare
    # /programma/<slug>/<id>-patronen uit de volledige response.
    embedded_regex = re.compile(
        r"/(?:nl/)?programma/"
        r"[A-Za-z0-9_%+.\-]+/\d+",
        flags=re.IGNORECASE,
    )

    for match in embedded_regex.finditer(cleaned_html):
        event_url = PARADISO_BASE_URL + match.group(0)
        event_url = event_url.split("?", 1)[0].split("#", 1)[0].rstrip("/")
        urls.append(event_url)

    for match in relative_regex.finditer(
        cleaned_html
    ):
        event_url = (
            PARADISO_BASE_URL
            + match.group(0)
        )

        event_url = (
            event_url
            .split("?", 1)[0]
            .split("#", 1)[0]
            .rstrip("/")
        )

        urls.append(event_url)

    unique_urls = []
    seen = set()

    for event_url in urls:
        if not re.match(
            r"https://www\.paradiso\.nl/(?:nl/)?programma/",
            event_url,
            flags=re.IGNORECASE,
        ):
            continue

        key = normalize_url(
            event_url
        )

        if key in seen:
            continue

        seen.add(key)

        unique_urls.append(
            event_url
        )

    return unique_urls


def paradiso_strip_tags(text):
    return re.sub(
        r"<[^>]+>",
        "",
        text
    )


def paradiso_decode_html(text):
    return (
        html_module.unescape(text)
        .replace("\xa0", " ")
        .strip()
    )


def paradiso_html_to_text(html):
    text = re.sub(
        r"<script[^>]*>.*?</script>",
        " ",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )

    text = re.sub(
        r"<style[^>]*>.*?</style>",
        " ",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    text = re.sub(
        r"<[^>]+>",
        " ",
        text
    )

    text = html_module.unescape(
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def paradiso_extract_artist(html):
    # De zichtbare H1 is de naam van het huidige programma en is
    # betrouwbaarder dan de browser-title, die soms locatie/SEO-tekst bevat.
    h1_match = re.search(
        r"<h1[^>]*>(.*?)</h1>",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if h1_match:
        artist = paradiso_decode_html(
            paradiso_strip_tags(h1_match.group(1))
        ).strip()
        if artist:
            return artist

    title_match = re.search(
        r"<title[^>]*>(.*?)</title>",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )

    if title_match:
        artist = (
            paradiso_decode_html(
                paradiso_strip_tags(
                    title_match.group(1)
                )
            )
        )

        artist = re.sub(
            r"\s*\|\s*Paradiso.*$",
            "",
            artist,
            flags=re.IGNORECASE,
        )

        artist = re.sub(
            r"\s*[-–—]\s*Paradiso.*$",
            "",
            artist,
            flags=re.IGNORECASE,
        )

        artist = artist.strip()

        if artist:
            return artist

    return ""


def paradiso_extract_venue(html):
    text = paradiso_html_to_text(html)

    # Pak de eerste eigen locatievermelding op de detailpagina. Aanbevolen
    # programma's onderaan kunnen andere locaties noemen en mogen de zaal
    # van het huidige evenement niet overschrijven.
    venue_match = re.search(
        r"\bIn\s+(Tolhuistuin|Paradiso|Bitterzoet|Cinetol|Zonnehuis|Vondelkerk|De Duif|Parallel|Skatecafe)\b",
        text,
        flags=re.IGNORECASE,
    )
    if venue_match:
        name = venue_match.group(1)
        canonical = {
            "tolhuistuin": "Tolhuistuin",
            "paradiso": "Paradiso",
            "bitterzoet": "Bitterzoet",
            "cinetol": "Cinetol",
            "zonnehuis": "Zonnehuis",
            "vondelkerk": "Vondelkerk",
            "de duif": "De Duif",
            "parallel": "Parallel",
            "skatecafe": "Skatecafe",
        }
        return canonical.get(name.lower(), name)

    return "Paradiso"

def paradiso_extract_primary_event_date_time(html):
    # Gebruik alleen het eerste zichtbare datum/tijdblok van de detailpagina.
    # Aanbevolen programma's komen later in de HTML en mogen nooit de datum
    # van het huidige evenement bepalen.
    text = paradiso_html_to_text(html)
    months = {
        "januari": 1, "februari": 2, "maart": 3, "april": 4,
        "mei": 5, "juni": 6, "juli": 7, "augustus": 8,
        "september": 9, "oktober": 10, "november": 11, "december": 12,
        "january": 1, "february": 2, "march": 3, "april": 4,
        "may": 5, "june": 6, "july": 7, "august": 8,
        "september": 9, "october": 10, "november": 11, "december": 12,
    }
    month_pattern = "|".join(months.keys())
    date_match = re.search(
        r"\b(?:maandag|dinsdag|woensdag|donderdag|vrijdag|zaterdag|zondag|"
        r"monday|tuesday|wednesday|thursday|friday|saturday|sunday)?\s*"
        r"(\d{1,2})\s+(" + month_pattern + r")(?:\s+(20\d{2}))?\b",
        text,
        flags=re.IGNORECASE,
    )
    if not date_match:
        return None

    day = int(date_match.group(1))
    month = months[date_match.group(2).lower()]
    explicit_year = date_match.group(3)
    today = date.today()
    year = int(explicit_year) if explicit_year else today.year
    candidate = date(year, month, day)
    if not explicit_year and candidate < today - timedelta(days=7):
        candidate = date(year + 1, month, day)

    # Zoek tijd alleen in het stuk direct na de gevonden hoofddatum.
    # Zo kan een aanbevolen concert verderop geen tijd leveren.
    after_date = text[date_match.end():date_match.end() + 1200]
    time_match = re.search(
        r"(?:Hoofdprogramma|Main program(?:me)?)\s*:\s*(\d{1,2}:\d{2})",
        after_date,
        flags=re.IGNORECASE,
    )
    if not time_match:
        time_match = re.search(
            r"(?:Zaal\s+open|Doors)\s*:\s*(\d{1,2}:\d{2})",
            after_date,
            flags=re.IGNORECASE,
        )

    return candidate.isoformat(), (time_match.group(1) if time_match else "")

def paradiso_find_best_date_candidate(
    html,
    artist
):
    date_regex = re.compile(
        r"20\d{2}-\d{2}-\d{2}"
        r"T\d{2}:\d{2}:\d{2}"
        r"(?:\.\d+)?"
        r"(?:Z|[+-]\d{2}:\d{2})"
    )

    candidates = list(
        date_regex.finditer(
            html
        )
    )

    if not candidates:
        return None

    artist_positions = []

    if artist:
        search_html = html.lower()
        search_artist = artist.lower()

        start_index = 0

        while start_index < len(
            search_html
        ):
            position = (
                search_html.find(
                    search_artist,
                    start_index
                )
            )

            if position < 0:
                break

            artist_positions.append(
                position
            )

            start_index = (
                position
                + max(
                    len(search_artist),
                    1
                )
            )

    if artist_positions:
        best_match = min(
            candidates,
            key=lambda date_match: min(
                abs(
                    date_match.start()
                    - artist_position
                )
                for artist_position
                in artist_positions
            )
        )

        return best_match.group(0)

    return candidates[0].group(0)


def paradiso_iso_to_local(
    iso_date
):
    try:
        parse_value = iso_date

        if parse_value.endswith("Z"):
            parse_value = (
                parse_value[:-1]
                + "+00:00"
            )

        parsed = datetime.fromisoformat(
            parse_value
        )

        if parsed.tzinfo is None:
            return None

        local = parsed.astimezone(
            ZoneInfo(
                "Europe/Amsterdam"
            )
        )

        return (
            local.date().isoformat(),
            local.strftime("%H:%M"),
        )

    except Exception:
        return None


def paradiso_extract_visible_date(html):
    text = paradiso_html_to_text(
        html
    )

    months = (
        "januari|februari|maart|april|mei|juni|"
        "juli|augustus|september|oktober|"
        "november|december"
    )

    regex = re.compile(
        r"(?:maandag|dinsdag|woensdag|"
        r"donderdag|vrijdag|zaterdag|zondag)?"
        r"\s*(\d{1,2})\s+"
        r"(" + months + r")",
        flags=re.IGNORECASE,
    )

    match = regex.search(text)

    if not match:
        return None

    day = int(
        match.group(1)
    )

    month_name = (
        match.group(2)
        .lower()
    )

    month_number = MONTHS_LONG.get(
        month_name
    )

    if month_number is None:
        return None

    today = date.today()
    year = today.year

    try:
        candidate = date(
            year,
            month_number,
            day
        )

    except ValueError:
        return None

    if candidate < (
        today - timedelta(days=7)
    ):
        year += 1

    try:
        candidate = date(
            year,
            month_number,
            day
        )

    except ValueError:
        return None

    return candidate.isoformat()


def paradiso_extract_visible_time(html):
    text = paradiso_html_to_text(
        html
    )

    main_program_match = re.search(
        r"(?:Hoofdprogramma|Main program(?:me)?)\s*:\s*"
        r"(\d{1,2}:\d{2})",
        text,
        flags=re.IGNORECASE,
    )

    if main_program_match:
        return main_program_match.group(1)

    doors_match = re.search(
        r"(?:Zaal\s+open|Doors)\s*:\s*"
        r"(\d{1,2}:\d{2})",
        text,
        flags=re.IGNORECASE,
    )

    if doors_match:
        return doors_match.group(1)

    generic_match = re.search(
        r"\b(?:[01]?\d|2[0-3]):"
        r"[0-5]\d\b",
        text
    )

    if generic_match:
        return generic_match.group(0)

    return ""


def paradiso_normalize_artist(artist):
    # Browser titles can contain Paradiso's location suffix.
    artist = re.sub(
        r"\s+in\s+(?:Tolhuistuin|Paradiso)(?:,\s*Amsterdam)?(?:\s+op\s+\d{1,2}\s+[A-Za-z]+)?\s*$",
        "",
        artist,
        flags=re.IGNORECASE,
    )
    return artist.strip()


def paradiso_parse_event(
    html,
    event_url
):
    artist = paradiso_normalize_artist(
        paradiso_extract_artist(html)
    )

    if not artist:
        return None

    primary_date_time = paradiso_extract_primary_event_date_time(html)
    if primary_date_time:
        concert_date, concert_time = primary_date_time
        venue = paradiso_extract_venue(html)
        return {
            "artist": artist,
            "venue": venue,
            "city": "Amsterdam",
            "country": "NL",
            "date": concert_date,
            "time": concert_time,
            "source": "Tolhuistuin" if venue == "Tolhuistuin" else "Paradiso",
            "url": event_url,
        }

    iso_date = (
        paradiso_find_best_date_candidate(
            html,
            artist
        )
    )

    if iso_date:
        local_result = (
            paradiso_iso_to_local(
                iso_date
            )
        )

        if local_result:
            concert_date, concert_time = (
                local_result
            )

            return {
                "artist": artist,
                "venue":
                    paradiso_extract_venue(
                        html
                    ),
                "city": "Amsterdam",
                "country": "NL",
                "date": concert_date,
                "time": concert_time,
                "source": "Tolhuistuin" if paradiso_extract_venue(html) == "Tolhuistuin" else "Paradiso",
                "url": event_url,
            }

    visible_date = (
        paradiso_extract_visible_date(
            html
        )
    )

    if not visible_date:
        return None

    visible_time = (
        paradiso_extract_visible_time(
            html
        )
    )

    return {
        "artist": artist,
        "venue":
            paradiso_extract_venue(
                html
            ),
        "city": "Amsterdam",
        "country": "NL",
        "date": visible_date,
        "time": visible_time,
        "source": "Tolhuistuin" if paradiso_extract_venue(html) == "Tolhuistuin" else "Paradiso",
        "url": event_url,
    }



def paradiso_find_recent_sitemap_program_urls(lookback_days=21):
    """Return all recently maintained Paradiso event pages from the official sitemap."""
    sitemap_index = download_page_retry("https://www.paradiso.nl/sitemap.xml")
    sitemap_urls = re.findall(
        r"<loc>\s*(https://www\.paradiso\.nl/sitemap/event_\d+\.xml)\s*</loc>",
        sitemap_index,
        flags=re.IGNORECASE,
    )
    if not sitemap_urls:
        raise RuntimeError("Paradiso sitemap-index bevat geen event-sitemaps")

    # Dagelijkse ontdekking: recent gewijzigde eventpagina's plus ALLE
    # toekomstige evenementen uit de vorige gepubliceerde feed (verderop).
    # Daardoor hoeven duizenden historische URL's niet dagelijks opnieuw
    # te worden gedownload. Ook alle sitemapitems zonder lastmod blijven
    # meegenomen: die kunnen we niet op ouderdom filteren.
    cutoff = (date.today() - timedelta(days=lookback_days)).isoformat()
    urls = []
    seen = set()

    # De sitemap-index bestaat uit tientallen kleine event-sitemaps.
    # Parallel ophalen voorkomt dat één trage sitemap de hele feed ophoudt.
    sitemap_xmls = []
    sitemap_errors = 0
    with ThreadPoolExecutor(max_workers=8) as sitemap_executor:
        futures = {
            sitemap_executor.submit(download_page_retry, url, attempts=2): url
            for url in sitemap_urls
        }
        for future in as_completed(futures):
            try:
                sitemap_xmls.append(future.result())
            except Exception as error:
                sitemap_errors += 1
                print("Paradiso sitemap tijdelijk onbereikbaar:", futures[future], str(error))
    print("Paradiso sitemaps opgehaald:", len(sitemap_xmls), "van", len(sitemap_urls),
          "(mislukt:", sitemap_errors, ")")

    for xml in sitemap_xmls:
        for block in re.findall(r"<url>(.*?)</url>", xml, flags=re.IGNORECASE | re.DOTALL):
            loc_match = re.search(r"<loc>\s*(.*?)\s*</loc>", block, flags=re.IGNORECASE | re.DOTALL)
            modified_match = re.search(r"<lastmod>\s*(.*?)\s*</lastmod>", block, flags=re.IGNORECASE | re.DOTALL)
            if not loc_match:
                continue

            event_url = paradiso_decode_html(loc_match.group(1).strip())
            if event_url.startswith("https://www.paradiso.nl/programma/"):
                event_url = event_url.replace(
                    "https://www.paradiso.nl/programma/",
                    "https://www.paradiso.nl/nl/programma/",
                    1,
                )
            modified = modified_match.group(1).strip() if modified_match else ""
            if "/programma/" not in event_url:
                continue
            # Dit filter geldt alleen voor nieuwe sitemap-discovery.
            # Oude toekomstige shows komen altijd alsnog via de vorige
            # feed terug, ongeacht hun lastmod.
            if modified and modified[:10] < cutoff:
                continue

            key = normalize_url(event_url)
            if key not in seen:
                seen.add(key)
                urls.append(event_url)

    print("Paradiso recente sitemaplinks:", len(urls), "sinds", cutoff)
    if len(urls) < 25:
        raise RuntimeError(
            "Paradiso sitemap levert onverwacht weinig recente programma's: "
            + str(len(urls))
        )

    return urls

PARADISO_RECOVERY_EVENTS = {
    "https://www.paradiso.nl/nl/programma/honey-im-home/2841259": "2026-12-30",
    "https://www.paradiso.nl/nl/programma/songhoy-blues/2884193": "2026-10-10",
    "https://www.paradiso.nl/nl/programma/lowdown-brass-band/2907014": "2026-10-13",
    "https://www.paradiso.nl/nl/programma/erotic-poetry-night-berlin-special/2924619": "2026-10-16",
    "https://www.paradiso.nl/nl/programma/suzan-freek/2942224": "2026-11-13",
    "https://www.paradiso.nl/nl/programma/tina-dico/2752660": "2026-11-13",
    "https://www.paradiso.nl/nl/programma/slift/2885768": "2026-11-23",
    "https://www.paradiso.nl/nl/programma/pongo/2896697": "2026-11-28",
    "https://www.paradiso.nl/nl/programma/mulaa-joans/2923337": "2026-12-03",
    "https://www.paradiso.nl/nl/programma/hermanos-gutierrez/2896806": "2026-12-13",
    "https://www.paradiso.nl/nl/programma/rikas/2900357": "2026-12-14",
    "https://www.paradiso.nl/nl/programma/camille/2900348": "2027-03-03",
    "https://www.paradiso.nl/nl/programma/sven-ross/2925145": "2027-03-05",
    "https://www.paradiso.nl/nl/programma/kalandra/2924600": "2027-03-27",
    "https://www.paradiso.nl/nl/programma/10-wie-niet-weg-is-is-gezien-10-jaar-smartlappen-karaoke-in-paradiso/2867814": "2027-04-04",
    "https://www.paradiso.nl/nl/programma/this-is-the-kit/2931706": "2027-05-07",
    "https://www.paradiso.nl/nl/programma/workshops-sdf-31-august/2894217": "2027-08-31",
}


def paradiso_event_key(url):
    """Match Dutch and English URLs for the same Paradiso event by numeric ID."""
    match = re.search(
        r"https?://(?:www\.)?paradiso\.nl/(?:nl/programma|en/program|programma)/[^/?#]+/(\d+)(?:[/?#]|$)",
        url or "",
        flags=re.IGNORECASE,
    )
    return "paradiso:" + match.group(1) if match else normalize_url(url)


def scrape_paradiso():
    print()
    print(
        "============================================================"
    )
    print("PARADISO")
    print(
        "============================================================"
    )

    # De zichtbare concertagenda is begrensd op 100 items. Gebruik daarom
    # Paradiso's officiële event-sitemaps als primaire ontdekking. Die bevatten
    # ook programma's verder in de toekomst. De landingspagina's blijven als
    # extra bron voor eventuele zojuist gepubliceerde items.
    program_urls = paradiso_find_recent_sitemap_program_urls()
    # Bekende toekomstige programma's die in de sitemap/detailverwerking
    # incidenteel ontbreken, blijven als regressiecontrole in de ontdekking.
    for required_url in (
        # Actueel bevestigd programma dat net na sitemappublicatie kan verschijnen.
        "https://www.paradiso.nl/nl/programma/this-is-the-kit/2931706",
    ):
        if paradiso_event_key(required_url) not in {paradiso_event_key(u) for u in program_urls}:
            program_urls.append(required_url)
    seen_program_urls = {paradiso_event_key(url) for url in program_urls}

    for agenda_url in PARADISO_AGENDA_URLS:
        try:
            agenda_html = download_page_retry(agenda_url)
            for event_url in paradiso_find_program_urls(agenda_html):
                key = paradiso_event_key(event_url)
                if key not in seen_program_urls:
                    seen_program_urls.add(key)
                    program_urls.append(event_url)
        except Exception as error:
            print("Paradiso aanvullende agenda fout:", agenda_url, "-", str(error))

    # Save discoveries before we append retained/previous-feed URLs.
    # Recently changed sitemap entries and visible agenda links must be
    # checked live; long-known distant events can use their last good data.
    freshly_discovered_keys = {paradiso_event_key(url) for url in program_urls}

    # De vorige feed is een tweede discoverybron. Een tijdelijke 403, 429,
    # lege HTML-response of onvolledige sitemap mag bekende toekomstige
    # concerten niet stil laten verdwijnen.
    previous_paradiso = {}
    today_string = date.today().isoformat()
    try:
        with open("concerts.json", "r", encoding="utf-8") as previous_file:
            previous_items = json.load(previous_file)
        for item in previous_items:
            if not isinstance(item, dict):
                continue
            url = item.get("url", "")
            if (
                item.get("source") in ("Paradiso", "Tolhuistuin")
                and item.get("date", "") >= today_string
                and url.startswith("https://www.paradiso.nl/")
            ):
                previous_paradiso[paradiso_event_key(url)] = item
    except (OSError, ValueError, TypeError) as error:
        print("Paradiso vorige feed niet beschikbaar:", error)

    # Herstelbestand met de 16 concrete concerten die op 8 oktober 2026
    # door onvolledige scrapes uit de feed verdwenen. Live verwerking wint
    # altijd; deze gegevens worden alleen als laatste redmiddel gebruikt.
    try:
        with open("scrapers/paradiso_recovery.json", "r", encoding="utf-8") as history_file:
            historic_events = json.load(history_file)
        for item in historic_events:
            if (
                isinstance(item, dict)
                and item.get("date", "") >= today_string
                and item.get("source") in ("Paradiso", "Tolhuistuin")
                and item.get("url", "").startswith("https://www.paradiso.nl/")
            ):
                previous_paradiso.setdefault(paradiso_event_key(item["url"]), item)
    except (OSError, ValueError, TypeError) as error:
        print("Paradiso historisch herstelbestand niet beschikbaar:", error)

    # Eenmalig herstel voor concerten die vóór deze beveiliging uit de
    # gepubliceerde feed verdwenen. Datums verlopen automatisch.
    for recovered_url, recovered_date in PARADISO_RECOVERY_EVENTS.items():
        if recovered_date >= today_string:
            key = paradiso_event_key(recovered_url)
            if key not in seen_program_urls:
                seen_program_urls.add(key)
                program_urls.append(recovered_url)

    for key, old_item in previous_paradiso.items():
        if key not in seen_program_urls:
            seen_program_urls.add(key)
            program_urls.append(old_item["url"])
    # A daily re-download of every known future detail page generates
    # hundreds of expensive requests, throttling and long cancelled runs.
    # Refresh recently modified/discovered URLs, recovery regressions,
    # and concerts happening soon. Reuse last published records for the
    # other distant events. Each source remains discoverable from the sitemap.
    soon_date = (date.today() + timedelta(days=21)).isoformat()
    mandatory_keys = {
        paradiso_event_key(url) for url, when in PARADISO_RECOVERY_EVENTS.items()
        if when >= today_string
    }
    cached_unmodified = {}
    for key, old_item in previous_paradiso.items():
        if (
            old_item.get("date", "") > soon_date
            and key not in freshly_discovered_keys
            and key not in mandatory_keys
        ):
            cached_unmodified[key] = old_item
    program_urls = [
        url for url in program_urls
        if paradiso_event_key(url) not in cached_unmodified
    ]
    print(
        "Paradiso ongewijzigde toekomstige shows uit cache:",
        len(cached_unmodified),
    )
    print("Paradiso vorige-feed URLs bewaakt:", len(previous_paradiso))

    print(
        "Concertlinks gevonden:",
        len(program_urls)
    )

    concerts = []

    success_count = 0
    failed_count = 0
    past_count = 0
    processed = 0

    total = len(
        program_urls
    )

    today = date.today()

    def fetch_paradiso(event_url):
        last_error = None

        for attempt in range(2):
            try:
                event_html = (
                    download_page_retry(
                        event_url, attempts=2
                    )
                )

                concert = paradiso_parse_event(
                    event_html,
                    event_url
                )
                if concert is None:
                    # Een incidenteel onvolledige Paradiso-response mag een
                    # geldig concert niet stil uit de feed laten verdwijnen.
                    if attempt < 1:
                        time.sleep(2.0 * (attempt + 1))
                        continue
                    print("Paradiso niet parseerbaar:", event_url, "HTML lengte:", len(event_html))
                    last_error = ValueError("Paradiso HTML niet parseerbaar: " + event_url)
                    break

                venue = paradiso_extract_venue(event_html)
                concert["venue"] = venue
                concert["source"] = "Tolhuistuin" if venue == "Tolhuistuin" else "Paradiso"
                return concert

            except Exception as error:
                last_error = error

                if attempt < 1:
                    time.sleep(
                        2.0 * (attempt + 1)
                    )

        # Some official Dutch programme URLs intermittently return 404 or
        # empty HTML while the English event URL is still fully available.
        # Recover the event and use the working English link in the feed.
        if "/nl/programma/" in event_url:
            english_url = event_url.replace("/nl/programma/", "/en/program/", 1)
            try:
                english_html = download_page_retry(english_url, attempts=2)
                recovered = paradiso_parse_event(english_html, english_url)
                if recovered is not None:
                    print("Paradiso Engelse detailfallback:", english_url)
                    return recovered
            except Exception as english_error:
                print("Paradiso Engelse fallback niet beschikbaar:", english_url, str(english_error))

        raise last_error

    with ThreadPoolExecutor(
        max_workers=12
    ) as executor:

        future_to_url = {
            executor.submit(
                fetch_paradiso,
                event_url
            ): event_url

            for event_url in program_urls
        }

        for future in as_completed(
            future_to_url
        ):
            event_url = future_to_url[
                future
            ]

            processed += 1

            try:
                concert = future.result()

                if concert is None:
                    failed_count += 1

                else:
                    try:
                        parsed_date = (
                            date.fromisoformat(
                                concert["date"]
                            )
                        )

                    except Exception:
                        parsed_date = None

                    if (
                        parsed_date is None
                        or parsed_date >= today
                    ):
                        concerts.append(
                            concert
                        )

                        success_count += 1

                    else:
                        past_count += 1

            except Exception as error:
                failed_count += 1

                print(
                    "Paradiso detailpagina fout:",
                    event_url,
                    "-",
                    str(error)
                )

            if (
                processed % 10 == 0
                or processed == total
            ):
                print(
                    "Paradiso verwerkt:",
                    f"{processed}/{total}"
                )

    unique = dict(cached_unmodified)

    for concert in concerts:
        key = paradiso_event_key(
            concert["url"]
        )

        unique[key] = concert

    # Controleer in een rustige tweede ronde wat wél in de vorige feed
    # stond maar niet in de nieuwe respons. Verwerk echte gewijzigde
    # data opnieuw; behoud bij tijdelijke netwerk-/parsefouten de
    # laatst bekende versie (niet bij HTTP 404/410).
    disappeared = [
        (key, item) for key, item in previous_paradiso.items()
        if key not in unique
    ]
    print("Paradiso vorige concerten onverwacht verdwenen:", len(disappeared))
    recovered_count = 0
    retained_count = 0
    for key, old_item in disappeared:
        url = old_item["url"]
        try:
            recovered = fetch_paradiso(url)
            if recovered is not None:
                if date.fromisoformat(recovered["date"]) >= today:
                    unique[key] = recovered
                    recovered_count += 1
                # Een aantoonbaar verstreken datum niet behouden.
            else:
                unique[key] = old_item
                retained_count += 1
        except HTTPError as error:
            if error.code in (404, 410):
                print("Paradiso definitief verwijderd:", url, error.code)
            else:
                unique[key] = old_item
                retained_count += 1
        except Exception as error:
            print("Paradiso laatste bekende versie bewaard:", url, error)
            unique[key] = old_item
            retained_count += 1

    print("Paradiso hersteld via tweede controle:", recovered_count)
    print("Paradiso tijdelijk behouden uit vorige feed:", retained_count)

    concerts = list(
        unique.values()
    )

    concerts.sort(
        key=lambda concert: (
            concert["date"],
            concert["time"],
            concert["artist"].lower()
        )
    )

    print(
        "Paradiso gelukt:",
        success_count
    )

    print(
        "Paradiso mislukt:",
        failed_count
    )
    if failed_count > 0:
        print("Paradiso WAARSCHUWING: niet alle programmapagina's konden worden verwerkt")

    print(
        "Paradiso voorbij:",
        past_count
    )

    print(
        "Paradiso unieke concerten:",
        len(concerts)
    )

    return concerts
