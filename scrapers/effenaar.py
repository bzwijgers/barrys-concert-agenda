from .common import *

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

    base_concerts = []

    skipped_cancelled = 0
    skipped_no_title = 0
    skipped_no_date = 0
    skipped_bad_date = 0

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

        title = effenaar_extract_text(
            card,
            "card-title"
        )

        date_text = effenaar_extract_text(
            card,
            "card-info-date"
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

        base_concerts.append(
            {
                "artist": title,
                "venue":
                    location
                    if location
                    else "Effenaar",
                "city": "Eindhoven",
                "country": "NL",
                "date": iso_date,
                "time": "",
                "source": "Effenaar",
                "url": detail_url,
            }
        )

    times_found = 0
    times_missing = 0
    detail_errors = 0

    def fetch_time(concert):
        detail_page = download_page(
            concert["url"]
        )

        return (
            effenaar_extract_start_time(
                detail_page
            )
        )

    with ThreadPoolExecutor(
        max_workers=8
    ) as executor:

        future_to_index = {
            executor.submit(
                fetch_time,
                concert
            ): index

            for index, concert
            in enumerate(base_concerts)
        }

        for future in as_completed(
            future_to_index
        ):
            index = future_to_index[
                future
            ]

            concert = base_concerts[
                index
            ]

            try:
                start_time = (
                    future.result()
                )

                concert["time"] = (
                    start_time
                )

                if start_time:
                    times_found += 1
                else:
                    times_missing += 1

            except Exception as error:
                detail_errors += 1

                print(
                    "Detailpagina fout:",
                    concert["artist"],
                    "-",
                    str(error)
                )

    unique = {}

    for concert in base_concerts:
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
