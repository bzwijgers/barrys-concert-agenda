from .common import *

# ============================================================
# 013
# ============================================================

SOURCE013_URL = "https://www.013.nl/programma"
SOURCE013_BASE_URL = "https://www.013.nl"


class Source013Blocked(RuntimeError):
    """013 served its bot verification page rather than its programme."""


def source013_is_bot_verification(page):
    # Detection only: never try to solve, bypass or proxy 013's CAPTCHA.
    prefix = (page or "")[:12000].casefold()
    return ("bot verification" in prefix
            or "lsrecaptcha-form" in prefix
            or ("captcha" in prefix and len(page or "") < 10000
                and "/programma/" not in prefix))



def source013_find_program_urls(html):
    cleaned_html = html_module.unescape(
        html
        .replace("\\/", "/")
        .replace("\\u002F", "/")
        .replace("\\u002f", "/")
    )

    urls = []
    seen = set()

    # Normale href-links.
    href_regex = re.compile(
        r'''href\s*=\s*["']([^"']+)["']''',
        flags=re.IGNORECASE,
    )

    for match in href_regex.finditer(
        cleaned_html
    ):
        href = match.group(1).strip()

        url_match = re.search(
            r'/programma/\d+/[^/?#"\'\s<>]+',
            href,
            flags=re.IGNORECASE,
        )

        if not url_match:
            continue

        path = url_match.group(0)

        event_url = (
            SOURCE013_BASE_URL
            + path
        )

        key = normalize_url(
            event_url
        )

        if key in seen:
            continue

        seen.add(key)
        urls.append(event_url)

    # Fallback:
    # sommige pagina's stoppen URL's in JSON/script-data
    # in plaats van in een gewone href.
    fallback_regex = re.compile(
        r'(?:https?://(?:www\.)?013\.nl)?'
        r'/programma/\d+/[^"\'<>?#\s\\]+',
        flags=re.IGNORECASE,
    )

    for match in fallback_regex.finditer(
        cleaned_html
    ):
        event_url = match.group(0)

        if event_url.startswith("/"):
            event_url = (
                SOURCE013_BASE_URL
                + event_url
            )

        event_url = (
            event_url
            .split("?", 1)[0]
            .split("#", 1)[0]
            .rstrip("/")
        )

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

    # 013 gebruikt in de Event JSON-LD soms de zichtbare combinatie
    # "artiest + tourtitel" als name. De canonical programma-URL bevat
    # voor zulke pagina's de artiestslug. Gebruik die alleen wanneer
    # de volledige slug aan het begin van de JSON-LD naam staat.
    url_slug_match = re.search(
        r"/programma/\d+/([^/?#]+)",
        event_url,
        flags=re.IGNORECASE,
    )

    if url_slug_match:
        slug = url_slug_match.group(1).strip("-")
        normalized_artist = re.sub(
            r"[^a-z0-9]+",
            "-",
            artist.lower(),
        ).strip("-")

        if (
            slug
            and normalized_artist != slug
            and normalized_artist.startswith(slug + "-")
        ):
            slug_word_count = len(
                [word for word in slug.split("-") if word]
            )
            artist_words = artist.split()

            if slug_word_count <= len(artist_words):
                artist = " ".join(
                    artist_words[:slug_word_count]
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
        program_html = download_page_retry(
            SOURCE013_URL
        )

    except Exception as error:
        raise RuntimeError(
            "013 programma kon niet worden gedownload: "
            + str(error)
        )

    if source013_is_bot_verification(program_html):
        raise Source013Blocked("013 returned its bot-verification page")

    program_urls = source013_find_program_urls(program_html)

    # 013 levert incidenteel een lege agenda ondanks HTTP 200.
    # Probeer de ongefilterde agenda opnieuw met cache-busting.
    if len(program_urls) < 25:
        for suffix in ("?view=all", "?_concert_retry=1", "/?view=all"):
            try:
                retry_html = download_page_retry(SOURCE013_URL + suffix)
                if source013_is_bot_verification(retry_html):
                    raise Source013Blocked("013 returned bot verification on retry")
                retry_urls = source013_find_program_urls(retry_html)
                if len(retry_urls) > len(program_urls):
                    program_urls = retry_urls
                if len(program_urls) >= 25:
                    break
            except Source013Blocked:
                raise
            except Exception as error:
                print("013 agenda retry fout:", str(error))


    print(
        "Programma-links gevonden:",
        len(program_urls)
    )

    # Beveiliging tegen een ogenschijnlijk succesvolle,
    # maar inhoudelijk mislukte 013-scrape.
    if len(program_urls) < 25:
        raise RuntimeError(
            "013 scraper gestopt: slechts "
            f"{len(program_urls)} programma-links gevonden."
        )

    # A valid programme landing page can be followed by a CAPTCHA on
    # detail requests from GitHub runners. Detect this before scheduling
    # hundreds of detail requests or treating their absence as 0 concerts.
    probe_page = download_page_retry(program_urls[0], attempts=1)
    if source013_is_bot_verification(probe_page):
        raise Source013Blocked("013 served bot verification on event details")

    concerts = []
    blocked_details = 0
    detail_errors = 0
    no_event_data = 0

    total = len(
        program_urls
    )

    processed = 0

    def fetch_013(event_url):
        last_error = None

        for attempt in range(3):
            try:
                event_html = (
                    download_page(
                        event_url
                    )
                )
                if source013_is_bot_verification(event_html):
                    raise Source013Blocked("013 detail shows bot verification")

                return source013_parse_event(
                    event_html,
                    event_url
                )

            except Source013Blocked:
                raise
            except Exception as error:
                last_error = error

                if attempt < 2:
                    time.sleep(
                        2.0
                        * (attempt + 1)
                    )

        raise last_error

    with ThreadPoolExecutor(
        max_workers=3
    ) as executor:

        future_to_url = {
            executor.submit(
                fetch_013,
                event_url
            ): event_url

            for event_url in program_urls
        }

        for future in as_completed(
            future_to_url
        ):
            event_url = (
                future_to_url[
                    future
                ]
            )

            processed += 1

            try:
                concert = (
                    future.result()
                )

                if concert is not None:
                    concerts.append(
                        concert
                    )
                else:
                    no_event_data += 1

            except Source013Blocked:
                blocked_details += 1
            except Exception as error:
                detail_errors += 1

                print(
                    "013 detailpagina fout:",
                    event_url,
                    "-",
                    str(error)
                )

            if (
                processed % 25 == 0
                or processed == total
            ):
                print(
                    "013 verwerkt:",
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

    if blocked_details > 0 and (len(concerts) < 25 or blocked_details > total // 3):
        raise Source013Blocked(
            f"013 blocked {blocked_details}/{total} detail requests"
        )

    # Tweede beveiliging:
    # ook na het verwerken moet er een realistische
    # hoeveelheid 013-concerten overblijven.
    if len(concerts) < 25:
        raise RuntimeError(
            "013 scraper gestopt: slechts "
            f"{len(concerts)} concerten verwerkt."
        )

    return concerts
