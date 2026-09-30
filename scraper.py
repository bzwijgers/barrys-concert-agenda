from urllib.request import Request, urlopen
from datetime import datetime
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
    "Accept-Language": "nl-NL,nl;q=0.9,en;q=0.8",
}

MONTHS = {
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


def download_page(url):
    request = Request(
        url,
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
        flags=
            re.IGNORECASE |
            re.DOTALL
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
        flags=
            re.IGNORECASE |
            re.DOTALL,
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

        month = MONTHS.get(
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
        card_pattern.finditer(
            page
        )
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

    for index, match in enumerate(
        matches
    ):
        start = match.start()

        if index < len(matches) - 1:
            end = (
                matches[index + 1]
                .start()
            )
        else:
            end = len(page)

        card = page[start:end]

        relative_url = (
            match.group(1)
        )

        detail_url = (
            EFFENAAR_BASE_URL
            + relative_url
        )

        title = (
            effenaar_extract_text(
                card,
                "card-title"
            )
        )

        date_text = (
            effenaar_extract_text(
                card,
                "card-info-date"
            )
        )

        location = (
            effenaar_extract_location(
                card
            )
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
            or
            "geannuleerd" in status
            or
            "cancelled" in status
            or
            "canceled" in status
        ):
            skipped_cancelled += 1
            continue

        iso_date = (
            effenaar_parse_date(
                date_text
            )
        )

        if not iso_date:
            skipped_bad_date += 1
            continue

        start_time = ""

        try:
            detail_page = (
                download_page(
                    detail_url
                )
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
        clean_json_text(
            url
        )
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

    location_block = (
        block[
            location_start:end
        ]
    )

    value = (
        find_json_value(
            location_block,
            "name"
        )
    )

    if not value:
        return ""

    return clean_json_text(
        value
    )


def rotown_find_concert_urls(html):
    event_regex = re.compile(
        r'<div\s+class=["\']'
        r'([^"\']*\bwp_theatre_event\b[^"\']*)'
        r'["\'][^>]*>',
        flags=
            re.IGNORECASE |
            re.DOTALL,
    )

    urls = []

    for match in event_regex.finditer(
        html
    ):
        classes = (
            match.group(1)
        )

        is_concert = re.search(
            r'(?:^|\s)concert(?:\s|$)',
            classes,
            flags=re.IGNORECASE,
        )

        if not is_concert:
            continue

        start = match.start()

        end = min(
            start + 10000,
            len(html)
        )

        section = html[
            start:end
        ]

        url_match = re.search(
            r'href=["\']'
            r'(https://www\.rotown\.nl/'
            r'agenda/[^"\'?#]+/?)'
            r'["\']',
            section,
            flags=re.IGNORECASE,
        )

        if url_match:
            url = (
                url_match.group(1)
            )

            if url not in urls:
                urls.append(url)

    return urls


def rotown_find_structured_events(
    html
):
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

        name = (
            find_json_value(
                block,
                "name"
            )
        )

        event_url = (
            find_json_value(
                block,
                "url"
            )
        )

        start_date = (
            find_json_value(
                block,
                "startDate"
            )
        )

        location = (
            rotown_find_location(
                block
            )
        )

        if (
            name
            and
            event_url
            and
            start_date
        ):
            cleaned_url = (
                clean_json_text(
                    event_url
                )
            )

            if (
                "rotown.nl/agenda/"
                not in cleaned_url.lower()
            ):
                continue

            events.append(
                {
                    "artist":
                        clean_json_text(
                            name
                        ),
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
        "Concert-links gevonden:",
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
        event_url = (
            rotown_normalize_url(
                event["url"]
            )
        )

        if (
            event_url
            not in concert_url_set
        ):
            continue

        start_date = (
            event["startDate"]
        )

        date = (
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
                    date,
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
        key = (
            rotown_normalize_url(
                concert["url"]
            )
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
        "Rotown concerten opgeslagen:",
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

    for match in event_regex.finditer(
        html
    ):
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

    location_block = (
        block[
            location_start:end
        ]
    )

    location_name = (
        find_json_value(
            location_block,
            "name"
        )
    )

    if not location_name:
        return "013"

    location_name = (
        clean_json_text(
            location_name
        )
    )

    return (
        location_name
        if location_name
        else "013"
    )


def source013_clean_artist_name(
    name
):
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

    event_position = (
        event_match.start()
    )

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

    raw_name = (
        find_json_value(
            block,
            "name"
        )
    )

    if not raw_name:
        return None

    raw_start_date = (
        find_json_value(
            block,
            "startDate"
        )
    )

    if not raw_start_date:
        return None

    start_date = (
        clean_json_text(
            raw_start_date
        )
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

    location = (
        source013_find_location(
            block
        )
    )

    date = (
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
        "date": date,
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
        program_html = (
            download_page(
                SOURCE013_URL
            )
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

    total = len(
        program_urls
    )

    for index, event_url in enumerate(
        program_urls,
        start=1
    ):
        try:
            event_html = (
                download_page(
                    event_url
                )
            )

            concert = (
                source013_parse_event(
                    event_html,
                    event_url
                )
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
            or
            index == total
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


# Effenaar
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


# Rotown
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
        if concert["source"]
        == "Effenaar"
    ]
)

rotown_count = len(
    [
        concert
        for concert in all_concerts
        if concert["source"]
        == "Rotown"
    ]
)

source013_count = len(
    [
        concert
        for concert in all_concerts
        if concert["source"]
        == "013"
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
