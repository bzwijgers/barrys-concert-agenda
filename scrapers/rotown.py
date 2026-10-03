from .common import *

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

    location_start = location_match.start()

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
        for match in re.finditer(
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

    def has_clubcard(event_url):
        try:
            detail_html = download_page_retry(event_url)
        except Exception as error:
            print("Rotown Clubkaart controle fout:", event_url, str(error))
            return False

        detail_text = clean_text(detail_html).lower()

        if "mood-bored" in event_url.lower():
            for term in ("club", "kaart", "gratis", "free"):
                position = detail_html.lower().find(term)
                if position >= 0:
                    start = max(0, position - 250)
                    end = min(len(detail_html), position + 500)
                    print(
                        "ROTOWN CLUBKAART DEBUG",
                        term,
                        clean_text(detail_html[start:end])
                    )

        return bool(
            re.search(
                r"rotown\\s+clubkaart|clubkaart",
                detail_text,
                flags=re.IGNORECASE,
            )
        )

    clubcard_by_url = {}

    with ThreadPoolExecutor(max_workers=12) as executor:
        future_to_url = {
            executor.submit(
                has_clubcard,
                event["url"]
            ): event["url"]
            for event in structured_events
        }

        for future in as_completed(future_to_url):
            url = future_to_url[future]

            try:
                clubcard_by_url[
                    rotown_normalize_url(url)
                ] = future.result()
            except Exception as error:
                print(
                    "Rotown Clubkaart controle fout:",
                    url,
                    str(error)
                )

                clubcard_by_url[
                    rotown_normalize_url(url)
                ] = False

    print(
        "Rotown Clubkaart concerten gevonden:",
        sum(clubcard_by_url.values())
    )

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
                "city": "Rotterdam",
                "country": "NL",
                "date": concert_date,
                "time": start_time,
                "source": "Rotown",
                "url": event["url"],
                "clubCard": clubcard_by_url.get(
                    event_url,
                    False
                ),
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
