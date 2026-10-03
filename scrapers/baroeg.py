from .common import *

# ============================================================
# BAROEG
# ============================================================

BAROEG_AGENDA_URL = "https://baroeg.nl/agenda/"
BAROEG_BASE_URL = "https://baroeg.nl"


def baroeg_find_event_urls(html):
    cleaned_html = (
        html
        .replace("\\/", "/")
        .replace("\\u002F", "/")
        .replace("\\u002f", "/")
    )

    urls = []

    absolute_regex = re.compile(
        r"""https?://(?:www\.)?baroeg\.nl/productie/[^"'<>?\s]+""",
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
            + "/"
        )

        # WordPress feed-URL is geen concert.
        if "/feed/" in event_url.lower():
            continue

        urls.append(event_url)

    relative_regex = re.compile(
        r"""(?:href\s*=\s*["'])?(/productie/[^"'<>?\s]+)""",
        flags=re.IGNORECASE,
    )

    for match in relative_regex.finditer(
        cleaned_html
    ):
        path = (
            match.group(1)
            .split("?", 1)[0]
            .split("#", 1)[0]
            .rstrip("/")
        )

        if "/feed/" in path.lower():
            continue

        urls.append(
            BAROEG_BASE_URL
            + path
            + "/"
        )

    unique_urls = []
    seen = set()

    for event_url in urls:
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


def baroeg_strip_tags(text):
    return re.sub(
        r"<[^>]+>",
        "",
        text
    )


def baroeg_decode_html(text):
    return (
        html_module.unescape(text)
        .replace("\xa0", " ")
        .strip()
    )


def baroeg_html_to_text(html):
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


def baroeg_clean_artist_title(title):
    title = re.sub(
        r"\s*[–—-]\s*Poppodium\s+Baroeg\s+Rotterdam\s*$",
        "",
        title,
        flags=re.IGNORECASE,
    )

    title = re.sub(
        r"\s*[–—-]\s*Poppodium\s+Baroeg\s*$",
        "",
        title,
        flags=re.IGNORECASE,
    )

    title = re.sub(
        r"\s*[–—-]\s*Baroeg\s+Rotterdam\s*$",
        "",
        title,
        flags=re.IGNORECASE,
    )

    title = re.sub(
        r"\s+",
        " ",
        title
    )

    return title.strip()


def baroeg_extract_artist(html):
    h1_match = re.search(
        r"<h1[^>]*>(.*?)</h1>",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )

    if h1_match:
        artist = (
            baroeg_clean_artist_title(
                baroeg_decode_html(
                    baroeg_strip_tags(
                        h1_match.group(1)
                    )
                )
            )
        )

        if artist:
            return artist

    title_match = re.search(
        r"<title[^>]*>(.*?)</title>",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )

    if not title_match:
        return ""

    return baroeg_clean_artist_title(
        baroeg_decode_html(
            baroeg_strip_tags(
                title_match.group(1)
            )
        )
    )


def baroeg_extract_event_date(text):
    months = (
        "januari|februari|maart|april|mei|juni|"
        "juli|augustus|september|oktober|"
        "november|december"
    )

    date_regex = re.compile(
        r"\b(" + months + r")\s+"
        r"(\d{1,2}),\s*"
        r"(20\d{2})\b",
        flags=re.IGNORECASE,
    )

    candidates = []

    for match in date_regex.finditer(
        text
    ):
        month_name = (
            match.group(1)
            .lower()
        )

        month_number = MONTHS_LONG.get(
            month_name
        )

        if month_number is None:
            continue

        try:
            candidate = date(
                int(match.group(3)),
                month_number,
                int(match.group(2))
            )

            candidates.append(
                candidate
            )

        except Exception:
            continue

    today = date.today()

    future_dates = [
        candidate
        for candidate in candidates
        if candidate >= today
    ]

    if not future_dates:
        return None

    event_date = min(
        future_dates
    )

    return event_date.isoformat()


def baroeg_extract_event_time(
    text,
    event_date
):
    try:
        parsed_date = date.fromisoformat(
            event_date
        )

    except Exception:
        return ""

    month_names = {
        1: "januari",
        2: "februari",
        3: "maart",
        4: "april",
        5: "mei",
        6: "juni",
        7: "juli",
        8: "augustus",
        9: "september",
        10: "oktober",
        11: "november",
        12: "december",
    }

    month_name = month_names.get(
        parsed_date.month,
        ""
    )

    date_marker = (
        f"{month_name} "
        f"{parsed_date.day}, "
        f"{parsed_date.year}"
    )

    date_position = text.lower().find(
        date_marker.lower()
    )

    if date_position >= 0:
        relevant_text = text[
            date_position:
            min(
                len(text),
                date_position + 250
            )
        ]

    else:
        relevant_text = text

    time_match = re.search(
        r"\b(?:[01]?\d|2[0-3]):[0-5]\d\b",
        relevant_text
    )

    if not time_match:
        return ""

    return time_match.group(0)


def baroeg_parse_event(
    html,
    event_url
):
    artist = baroeg_extract_artist(
        html
    )

    if not artist:
        return None

    text = baroeg_html_to_text(
        html
    )

    event_date = (
        baroeg_extract_event_date(
            text
        )
    )

    if not event_date:
        return None

    event_time = (
        baroeg_extract_event_time(
            text,
            event_date
        )
    )

    return {
        "artist": artist,
        "venue": "Baroeg",
        "city": "Rotterdam",
        "country": "NL",
        "date": event_date,
        "time": event_time,
        "source": "Baroeg",
        "url": event_url,
    }


def scrape_baroeg():
    print()
    print(
        "============================================================"
    )
    print("BAROEG")
    print(
        "============================================================"
    )

    try:
        agenda_html = download_page(
            BAROEG_AGENDA_URL
        )

    except Exception as error:
        print(
            "Baroeg agenda fout:",
            str(error)
        )
        return []

    event_urls = (
        baroeg_find_event_urls(
            agenda_html
        )
    )

    print(
        "Baroeg eventlinks gevonden:",
        len(event_urls)
    )

    concerts = []
    failed_count = 0
    processed = 0
    total = len(event_urls)

    def fetch_baroeg(event_url):
        event_html = download_page(
            event_url
        )

        return baroeg_parse_event(
            event_html,
            event_url
        )

    with ThreadPoolExecutor(
        max_workers=8
    ) as executor:

        future_to_url = {
            executor.submit(
                fetch_baroeg,
                event_url
            ): event_url

            for event_url in event_urls
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

                if concert is not None:
                    concerts.append(
                        concert
                    )
                else:
                    failed_count += 1

            except Exception as error:
                failed_count += 1

                print(
                    "Baroeg detailpagina fout:",
                    event_url,
                    "-",
                    str(error)
                )

            if (
                processed % 10 == 0
                or processed == total
            ):
                print(
                    "Baroeg verwerkt:",
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
        "Baroeg concerten opgeslagen:",
        len(concerts)
    )

    print(
        "Baroeg mislukt/overgeslagen:",
        failed_count
    )

    return concerts
