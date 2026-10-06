from .common import *

# ============================================================
# PARADISO
# ============================================================

PARADISO_AGENDA_URL = (
    "https://www.paradiso.nl/"
    "landing/concertagenda-paradiso/2069817"
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

    h1_match = re.search(
        r"<h1[^>]*>(.*?)</h1>",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )

    if not h1_match:
        return ""

    return (
        paradiso_decode_html(
            paradiso_strip_tags(
                h1_match.group(1)
            )
        )
        .strip()
    )


def paradiso_extract_venue(html):
    text = paradiso_html_to_text(html)

    venues = [
        "Tolhuistuin",
        "Bitterzoet",
        "Cinetol",
        "Zonnehuis",
        "Vondelkerk",
        "De Duif",
        "Parallel",
        "Skatecafe",
        "Paradiso",
    ]

    # De eigen locatie staat bovenaan de eventpagina. Aanbevolen programma's
    # verderop bevatten ook "In <locatie>". Kies daarom de vroegste match,
    # niet de eerste zaal uit onze voorkeurslijst die ergens op de pagina staat.
    matches = []
    for venue in venues:
        match = re.search(
            r"\bIn\s+" + re.escape(venue) + r"\b",
            text,
            flags=re.IGNORECASE,
        )
        if match:
            matches.append((match.start(), venue))

    if matches:
        return min(matches, key=lambda item: item[0])[1]

    return "Paradiso"

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
        r"Hoofdprogramma\s*:\s*"
        r"(\d{1,2}:\d{2})",
        text,
        flags=re.IGNORECASE,
    )

    if main_program_match:
        return main_program_match.group(1)

    doors_match = re.search(
        r"Zaal\s+open\s*:\s*"
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


def paradiso_parse_event(
    html,
    event_url
):
    artist = paradiso_extract_artist(
        html
    )

    if not artist:
        return None

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
                "source": "Paradiso",
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
        "source": "Paradiso",
        "url": event_url,
    }


def scrape_paradiso():
    print()
    print(
        "============================================================"
    )
    print("PARADISO")
    print(
        "============================================================"
    )

    try:
        agenda_html = (
            download_page_retry(
                PARADISO_AGENDA_URL
            )
        )

    except Exception as error:
        print(
            "Paradiso concertagenda fout:",
            str(error)
        )
        return []

    program_urls = (
        paradiso_find_program_urls(
            agenda_html
        )
    )

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

        for attempt in range(3):
            try:
                event_html = (
                    download_page_retry(
                        event_url
                    )
                )

                return paradiso_parse_event(
                    event_html,
                    event_url
                )

            except Exception as error:
                last_error = error

                if attempt < 2:
                    time.sleep(
                        2.0 * (attempt + 1)
                    )

        raise last_error

    with ThreadPoolExecutor(
        max_workers=3
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

    unique = {}

    for concert in concerts:
        key = normalize_url(
            concert["url"]
        )

        unique[key] = concert

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

    print(
        "Paradiso voorbij:",
        past_count
    )

    print(
        "Paradiso unieke concerten:",
        len(concerts)
    )

    return concerts
