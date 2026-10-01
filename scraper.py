from urllib.request import Request, urlopen
from urllib.parse import urlsplit, urlunsplit, quote
from urllib.error import HTTPError, URLError
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
import re
import html as html_module
import json
import time


# ============================================================
# ALGEMEEN
# ============================================================

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/154.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,*/*;q=0.8"
    ),
    "Accept-Language": "nl-NL,nl;q=0.9,en;q=0.8",
    "Cache-Control": "no-cache",
}

MONTHS_SHORT = {
    "jan": 1,
    "feb": 2,
    "mrt": 3,
    "maa": 3,
    "apr": 4,
    "mei": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "okt": 10,
    "nov": 11,
    "dec": 12,
}

MONTHS_LONG = {
    "januari": 1,
    "februari": 2,
    "maart": 3,
    "april": 4,
    "mei": 5,
    "juni": 6,
    "juli": 7,
    "augustus": 8,
    "september": 9,
    "oktober": 10,
    "november": 11,
    "december": 12,
}


def encode_url(url):
    parts = urlsplit(url)

    encoded_path = quote(
        parts.path,
        safe="/%:@"
    )

    encoded_query = quote(
        parts.query,
        safe="=&%:@/?"
    )

    return urlunsplit(
        (
            parts.scheme,
            parts.netloc,
            encoded_path,
            encoded_query,
            parts.fragment,
        )
    )


def download_page(url):
    safe_url = encode_url(url)

    request = Request(
        safe_url,
        headers=HEADERS
    )

    with urlopen(
        request,
        timeout=30
    ) as response:

        return response.read().decode(
            "utf-8",
            errors="replace"
        )


def download_page_retry(
    url,
    attempts=3
):
    last_error = None

    for attempt in range(attempts):
        try:
            return download_page(url)

        except Exception as error:
            last_error = error

            if attempt < attempts - 1:
                time.sleep(1)

    raise last_error


def clean_text(value):
    value = re.sub(
        r"<[^>]+>",
        " ",
        value
    )

    value = html_module.unescape(
        value
    )

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value.strip()


def normalize_url(url):
    return (
        url
        .strip()
        .rstrip("/")
        .lower()
    )


def clean_json_text(text):
    return (
        text
        .replace("\\/", "/")
        .replace('\\"', '"')
        .replace("\\u0026", "&")
        .replace("\\u0027", "'")
        .replace("\\u2018", "‘")
        .replace("\\u2019", "’")
        .replace("\\u2013", "–")
        .replace("\\u2014", "—")
        .replace("&amp;", "&")
        .strip()
    )


def find_json_value(
    text,
    key
):
    regex = re.compile(
        r'"'
        + re.escape(key)
        + r'"\s*:\s*"((?:\\.|[^"\\])*)"',
        flags=re.IGNORECASE,
    )

    match = regex.search(text)

    if not match:
        return None

    return match.group(1)


# ============================================================
# EFFENAAR
# ============================================================

EFFENAAR_URL = "https://www.effenaar.nl/agenda"
EFFENAAR_BASE_URL = "https://www.effenaar.nl"


def effenaar_extract_text(
    card,
    class_name
):
    pattern = (
        r'<[^>]*class="[^"]*\b'
        + re.escape(class_name)
        + r'\b[^"]*"[^>]*>'
        + r'(.*?)'
        + r'</[^>]+>'
    )

    match = re.search(
        pattern,
        card,
        flags=re.IGNORECASE | re.DOTALL
    )

    if not match:
        return ""

    return clean_text(
        match.group(1)
    )


def effenaar_extract_location(card):
    match = re.search(
        r'<div\s+class="card-info-location"[^>]*>'
        r'(.*?)'
        r'</div>\s*</div>\s*</div>',
        card,
        flags=re.IGNORECASE | re.DOTALL,
    )

    if not match:
        return ""

    return clean_text(
        match.group(1)
    )


def effenaar_parse_date(value):
    parts = (
        value
        .lower()
        .strip()
        .split()
    )

    if len(parts) < 4:
        return None

    try:
        day = int(parts[1])

        month = MONTHS_SHORT.get(
            parts[2]
        )

        year = int(parts[3])

        if month is None:
            return None

        return (
            f"{year:04d}-"
            f"{month:02d}-"
            f"{day:02d}"
        )

    except (
        ValueError,
        IndexError
    ):
        return None


def effenaar_extract_start_time(page):
    start_date_matches = re.findall(
        r'"startDate"\s*:\s*"([^"]+)"',
        page,
        flags=re.IGNORECASE,
    )

    for value in start_date_matches:
        match = re.search(
            r'T(\d{2}):(\d{2})',
            value
        )

        if match:
            return (
                f"{match.group(1)}:"
                f"{match.group(2)}"
            )

    text = clean_text(page)

    patterns = [
        r'(?:aanvang|start)\s*:?\s*'
        r'(\d{1,2})[.:](\d{2})',

        r'(\d{1,2})[.:](\d{2})'
        r'\s*(?:uur)',
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE
        )

        if match:
            hour = int(
                match.group(1)
            )

            minute = int(
                match.group(2)
            )

            if (
                0 <= hour <= 23
                and
                0 <= minute <= 59
            ):
                return (
                    f"{hour:02d}:"
                    f"{minute:02d}"
                )

    return ""


def scrape_effenaar():
    print()
    print(
        "============================================================"
    )
    print("EFFENAAR")
    print(
        "============================================================"
    )

    try:
        page = download_page(
            EFFENAAR_URL
        )

    except Exception as error:
        print(
            "Effenaar agenda fout:",
            str(error)
        )
        return []

    card_pattern = re.compile(
        r'<a\s+class="agenda-card"\s+'
        r'href="(/agenda/[^"]+)"',
        flags=re.IGNORECASE,
    )

    matches = list(
        card_pattern.finditer(page)
    )

    print(
        "Agenda-kaarten gevonden:",
        len(matches)
    )

    concerts = []

    skipped_cancelled = 0
    skipped_no_title = 0
    skipped_no_date = 0
    skipped_bad_date = 0
    times_found = 0
    times_missing = 0
    detail_errors = 0

    for index, match in enumerate(matches):
        start = match.start()

        if index < len(matches) - 1:
            end = matches[index + 1].start()
        else:
            end = len(page)

        card = page[start:end]

        relative_url = match.group(1)

        detail_url = (
            EFFENAAR_BASE_URL
            + relative_url
        )

        title = effenaar_extract_text(
            card,
            "card-title"
        )

        date_text = effenaar_extract_text(
            card,
            "card-info-date"
        )

        location = effenaar_extract_location(
            card
        )

        status = (
            effenaar_extract_text(
                card,
                "card-status"
            )
            .lower()
        )

        if not title:
            skipped_no_title += 1
            continue

        if not date_text:
            skipped_no_date += 1
            continue

        if (
            "afgelast" in status
            or "geannuleerd" in status
            or "cancelled" in status
            or "canceled" in status
        ):
            skipped_cancelled += 1
            continue

        iso_date = effenaar_parse_date(
            date_text
        )

        if not iso_date:
            skipped_bad_date += 1
            continue

        start_time = ""

        try:
            detail_page = download_page(
                detail_url
            )

            start_time = (
                effenaar_extract_start_time(
                    detail_page
                )
            )

            if start_time:
                times_found += 1
            else:
                times_missing += 1

        except Exception as error:
            detail_errors += 1

            print(
                "Detailpagina fout:",
                title,
                "-",
                str(error)
            )

        concerts.append(
            {
                "artist": title,
                "venue":
                    location
                    if location
                    else "Effenaar",
                "city": "Eindhoven",
                "country": "NL",
                "date": iso_date,
                "time": start_time,
                "source": "Effenaar",
                "url": detail_url,
            }
        )

        time.sleep(0.10)

    unique = {}

    for concert in concerts:
        key = normalize_url(
            concert["url"]
        )
        unique[key] = concert

    concerts = list(
        unique.values()
    )

    print(
        "Concerten opgeslagen:",
        len(concerts)
    )
    print(
        "Afgelast/geannuleerd:",
        skipped_cancelled
    )
    print(
        "Zonder titel:",
        skipped_no_title
    )
    print(
        "Zonder datum:",
        skipped_no_date
    )
    print(
        "Ongeldige datum:",
        skipped_bad_date
    )
    print(
        "Tijden gevonden:",
        times_found
    )
    print(
        "Tijden niet gevonden:",
        times_missing
    )
    print(
        "Detailpagina fouten:",
        detail_errors
    )

    return concerts


# ============================================================
# ROTOWN
# ============================================================

ROTOWN_URL = "https://www.rotown.nl/"


def rotown_normalize_url(url):
    return (
        clean_json_text(url)
        .strip()
        .rstrip("/")
        .lower()
    )


def rotown_find_location(block):
    location_match = re.search(
        r'"location"',
        block,
        flags=re.IGNORECASE
    )

    if not location_match:
        return ""

    location_start = (
        location_match.start()
    )

    end = min(
        location_start + 1500,
        len(block)
    )

    location_block = block[
        location_start:end
    ]

    value = find_json_value(
        location_block,
        "name"
    )

    if not value:
        return ""

    return clean_json_text(value)


def rotown_find_concert_urls(html):
    event_regex = re.compile(
        r'<div\s+class=["\']'
        r'([^"\']*\bwp_theatre_event\b[^"\']*)'
        r'["\'][^>]*>',
        flags=re.IGNORECASE | re.DOTALL,
    )

    urls = []

    for match in event_regex.finditer(html):
        classes = match.group(1)

        is_concert_or_festival = re.search(
            r'(?:^|\s)(?:concert|festival)(?:\s|$)',
            classes,
            flags=re.IGNORECASE,
        )

        if not is_concert_or_festival:
            continue

        start = match.start()

        end = min(
            start + 10000,
            len(html)
        )

        section = html[start:end]

        url_match = re.search(
            r'href=["\']'
            r'(https://www\.rotown\.nl/'
            r'agenda/[^"\'?#]+/?)'
            r'["\']',
            section,
            flags=re.IGNORECASE,
        )

        if url_match:
            url = url_match.group(1)

            if url not in urls:
                urls.append(url)

    return urls


def rotown_find_structured_events(html):
    event_starts = [
        match.start()
        for match
        in re.finditer(
            r'"@type"\s*:\s*"Event"',
            html,
            flags=re.IGNORECASE,
        )
    ]

    events = []

    for start in event_starts:
        block_start = max(
            start - 300,
            0
        )

        block_end = min(
            start + 8000,
            len(html)
        )

        block = html[
            block_start:block_end
        ]

        name = find_json_value(
            block,
            "name"
        )

        event_url = find_json_value(
            block,
            "url"
        )

        start_date = find_json_value(
            block,
            "startDate"
        )

        location = rotown_find_location(
            block
        )

        if (
            name
            and event_url
            and start_date
        ):
            cleaned_url = clean_json_text(
                event_url
            )

            if (
                "rotown.nl/agenda/"
                not in cleaned_url.lower()
            ):
                continue

            events.append(
                {
                    "artist":
                        clean_json_text(name),
                    "startDate":
                        clean_json_text(
                            start_date
                        ),
                    "location":
                        location,
                    "url":
                        cleaned_url,
                }
            )

    return events


def scrape_rotown():
    print()
    print(
        "============================================================"
    )
    print("ROTOWN")
    print(
        "============================================================"
    )

    try:
        html = download_page(
            ROTOWN_URL
        )

    except Exception as error:
        print(
            "Rotown fout:",
            str(error)
        )
        return []

    concert_urls = (
        rotown_find_concert_urls(
            html
        )
    )

    structured_events = (
        rotown_find_structured_events(
            html
        )
    )

    print(
        "Concert/festival-links gevonden:",
        len(concert_urls)
    )

    print(
        "Structured events gevonden:",
        len(structured_events)
    )

    concert_url_set = {
        rotown_normalize_url(url)
        for url in concert_urls
    }

    concerts = []

    for event in structured_events:
        event_url = rotown_normalize_url(
            event["url"]
        )

        if event_url not in concert_url_set:
            continue

        start_date = event["startDate"]

        concert_date = (
            start_date
            .split("T")[0]
        )

        start_time = ""

        if "T" in start_date:
            time_part = (
                start_date
                .split("T", 1)[1]
            )

            time_match = re.match(
                r"(\d{2}):(\d{2})",
                time_part
            )

            if time_match:
                start_time = (
                    f"{time_match.group(1)}:"
                    f"{time_match.group(2)}"
                )

        concerts.append(
            {
                "artist":
                    event["artist"],
                "venue":
                    event["location"]
                    if event["location"]
                    else "Rotown",
                "city":
                    "Rotterdam",
                "country":
                    "NL",
                "date":
                    concert_date,
                "time":
                    start_time,
                "source":
                    "Rotown",
                "url":
                    event["url"],
            }
        )

    unique = {}

    for concert in concerts:
        key = rotown_normalize_url(
            concert["url"]
        )

        unique[key] = concert

    concerts = list(
        unique.values()
    )

    concerts.sort(
        key=lambda concert: (
            concert["date"],
            concert["artist"].lower()
        )
    )

    print(
        "Rotown concerten/festivals opgeslagen:",
        len(concerts)
    )

 return concerts

    # ============================================================
# 013
# ============================================================

SOURCE013_URL = "https://www.013.nl/programma"
SOURCE013_BASE_URL = "https://www.013.nl"


def source013_find_program_urls(html):
    event_regex = re.compile(
        r'href=["\']'
        r'([^"\']*/programma/[^"\'?#]+)'
        r'["\']',
        flags=re.IGNORECASE,
    )

    urls = []
    seen = set()

    for match in event_regex.finditer(html):
        event_url = (
            match.group(1)
            .strip()
            .rstrip("/")
        )

        if event_url.startswith("/"):
            event_url = (
                SOURCE013_BASE_URL
                + event_url
            )

        if not event_url.lower().startswith(
            "https://www.013.nl/programma/"
        ):
            continue

        key = normalize_url(
            event_url
        )

        if key in seen:
            continue

        seen.add(key)
        urls.append(event_url)

    return urls


def source013_find_location(block):
    location_match = re.search(
        r'"location"',
        block,
        flags=re.IGNORECASE
    )

    if not location_match:
        return "013"

    location_start = (
        location_match.start()
    )

    end = min(
        location_start + 2500,
        len(block)
    )

    location_block = block[
        location_start:end
    ]

    location_name = find_json_value(
        location_block,
        "name"
    )

    if not location_name:
        return "013"

    location_name = clean_json_text(
        location_name
    )

    return (
        location_name
        if location_name
        else "013"
    )


def source013_clean_artist_name(name):
    months = (
        "januari|"
        "februari|"
        "maart|"
        "april|"
        "mei|"
        "juni|"
        "juli|"
        "augustus|"
        "september|"
        "oktober|"
        "november|"
        "december"
    )

    date_at_end = re.compile(
        r"\s*[-–—|]\s*"
        r"\d{1,2}\s+"
        r"(?:" + months + r")"
        r"(?:\s+\d{4})?\s*$",
        flags=re.IGNORECASE,
    )

    return (
        date_at_end.sub(
            "",
            name
        )
        .strip()
    )


def source013_parse_event(
    html,
    event_url
):
    event_match = re.search(
        r'"@type"\s*:\s*"Event"',
        html,
        flags=re.IGNORECASE,
    )

    if not event_match:
        return None

    event_position = event_match.start()

    block_start = max(
        event_position - 1000,
        0
    )

    block_end = min(
        event_position + 12000,
        len(html)
    )

    block = html[
        block_start:block_end
    ]

    raw_name = find_json_value(
        block,
        "name"
    )

    if not raw_name:
        return None

    raw_start_date = find_json_value(
        block,
        "startDate"
    )

    if not raw_start_date:
        return None

    start_date = clean_json_text(
        raw_start_date
    )

    artist = (
        source013_clean_artist_name(
            clean_json_text(
                raw_name
            )
        )
    )

    if not artist:
        return None

    location = source013_find_location(
        block
    )

    concert_date = (
        start_date
        .split("T")[0]
    )

    start_time = ""

    if "T" in start_date:
        time_part = (
            start_date
            .split("T", 1)[1]
        )

        time_match = re.match(
            r"(\d{2}):(\d{2})",
            time_part
        )

        if time_match:
            start_time = (
                f"{time_match.group(1)}:"
                f"{time_match.group(2)}"
            )

    return {
        "artist": artist,
        "venue": location,
        "city": "Tilburg",
        "country": "NL",
        "date": concert_date,
        "time": start_time,
        "source": "013",
        "url": event_url,
    }


def scrape_013():
    print()
    print(
        "============================================================"
    )
    print("013")
    print(
        "============================================================"
    )

    try:
        program_html = download_page(
            SOURCE013_URL
        )

    except Exception as error:
        print(
            "013 programma fout:",
            str(error)
        )
        return []

    program_urls = (
        source013_find_program_urls(
            program_html
        )
    )

    print(
        "Programma-links gevonden:",
        len(program_urls)
    )

    concerts = []
    detail_errors = 0
    no_event_data = 0

    total = len(program_urls)

    for index, event_url in enumerate(
        program_urls,
        start=1
    ):
        try:
            event_html = download_page(
                event_url
            )

            concert = source013_parse_event(
                event_html,
                event_url
            )

            if concert is not None:
                concerts.append(
                    concert
                )
            else:
                no_event_data += 1

        except Exception as error:
            detail_errors += 1

            print(
                "013 detailpagina fout:",
                event_url,
                "-",
                str(error)
            )

        if (
            index % 25 == 0
            or index == total
        ):
            print(
                "013 verwerkt:",
                f"{index}/{total}"
            )

        time.sleep(0.05)

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
        "013 concerten opgeslagen:",
        len(concerts)
    )

    print(
        "013 zonder Event-data:",
        no_event_data
    )

    print(
        "013 detailpagina fouten:",
        detail_errors
    )

    return concerts


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
        r"/nl/programma/"
        r"[A-Za-z0-9_%+.\-]+/\d+",
        flags=re.IGNORECASE,
    )

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
        if not event_url.lower().startswith(
            "https://www.paradiso.nl/nl/programma/"
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
    text = paradiso_html_to_text(
        html
    )

    venues = [
        "Tolhuistuin",
        "Bitterzoet",
        "Cinetol",
        "Zonnehuis",
        "Vondelkerk",
        "De Duif",
        "Parallel",
        "Skatecafe",
    ]

    for venue in venues:
        if re.search(
            r"\bIn\s+"
            + re.escape(venue)
            + r"\b",
            text,
            flags=re.IGNORECASE,
        ):
            return venue

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

        while start_index < len(search_html):
            position = search_html.find(
                search_artist,
                start_index
            )

            if position < 0:
                break

            artist_positions.append(
                position
            )

            start_index = (
                position
                + max(len(search_artist), 1)
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

    total = len(
        program_urls
    )

    today = date.today()

    for index, event_url in enumerate(
        program_urls,
        start=1
    ):
        try:
            event_html = (
                download_page_retry(
                    event_url
                )
            )

            concert = (
                paradiso_parse_event(
                    event_html,
                    event_url
                )
            )

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
            index % 10 == 0
            or index == total
        ):
            print(
                "Paradiso verwerkt:",
                f"{index}/{total}"
            )

        time.sleep(0.05)

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


# ============================================================
# CENTRALE DATABASE
# ============================================================

print(
    "Barry's Concert Agenda - centrale scraper"
)

print(
    "Start:",
    datetime.now().isoformat(
        timespec="seconds"
    )
)

all_concerts = []


# EFFENAAR

try:
    effenaar_concerts = (
        scrape_effenaar()
    )

    all_concerts.extend(
        effenaar_concerts
    )

except Exception as error:
    print(
        "ERNSTIGE EFFENAAR FOUT:",
        str(error)
    )


# ROTOWN

try:
    rotown_concerts = (
        scrape_rotown()
    )

    all_concerts.extend(
        rotown_concerts
    )

except Exception as error:
    print(
        "ERNSTIGE ROTOWN FOUT:",
        str(error)
    )


# 013

try:
    source013_concerts = (
        scrape_013()
    )

    all_concerts.extend(
        source013_concerts
    )

except Exception as error:
    print(
        "ERNSTIGE 013 FOUT:",
        str(error)
    )


# PARADISO

try:
    paradiso_concerts = (
        scrape_paradiso()
    )

    all_concerts.extend(
        paradiso_concerts
    )

except Exception as error:
    print(
        "ERNSTIGE PARADISO FOUT:",
        str(error)
    )


# ============================================================
# DUBBELEN VERWIJDEREN
# ============================================================

unique_concerts = {}

for concert in all_concerts:
    key = normalize_url(
        concert["url"]
    )

    if key:
        unique_concerts[key] = concert


all_concerts = list(
    unique_concerts.values()
)


# ============================================================
# SORTEREN
# ============================================================

all_concerts.sort(
    key=lambda concert: (
        concert["date"],
        concert["time"],
        concert["artist"].lower()
    )
)


# ============================================================
# JSON OPSLAAN
# ============================================================

with open(
    "concerts.json",
    "w",
    encoding="utf-8"
) as file:

    json.dump(
        all_concerts,
        file,
        ensure_ascii=False,
        indent=2
    )


# ============================================================
# RESULTAAT
# ============================================================

effenaar_count = len(
    [
        concert
        for concert in all_concerts
        if concert["source"] == "Effenaar"
    ]
)

rotown_count = len(
    [
        concert
        for concert in all_concerts
        if concert["source"] == "Rotown"
    ]
)

source013_count = len(
    [
        concert
        for concert in all_concerts
        if concert["source"] == "013"
    ]
)

paradiso_count = len(
    [
        concert
        for concert in all_concerts
        if concert["source"] == "Paradiso"
    ]
)


print()
print(
    "============================================================"
)
print("CENTRAAL RESULTAAT")
print(
    "============================================================"
)

print(
    "Effenaar:",
    effenaar_count
)

print(
    "Rotown:",
    rotown_count
)

print(
    "013:",
    source013_count
)

print(
    "Paradiso:",
    paradiso_count
)

print(
    "Totaal:",
    len(all_concerts)
)

print()
print(
    "Bestand gemaakt: concerts.json"
)

print(
    "Centrale scraper gereed."
)
