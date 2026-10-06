from .common import *

TOLHUISTUIN_AGENDA_URLS = (\n    "https://tolhuistuin.nl/agenda",\n    "https://tolhuistuin.nl/zoeken",\n    "https://tolhuistuin.nl/",\n)
TOLHUISTUIN_BASE_URL = "https://tolhuistuin.nl"


def tolhuistuin_find_event_urls(page):
    return find_site_event_urls(
        page,
        TOLHUISTUIN_BASE_URL,
        "/evenementen/"
    )


def tolhuistuin_parse_event(page, event_url):
    title = _detail_title(page).strip()
    if not title:
        return None

    text = clean_text(page)

    # Paradiso is leidend voor alle programma's die door Paradiso
    # in Tolhuistuin worden georganiseerd.
    if re.search(r"\bMet\s+huisgenoot\s+Paradiso\b", text, flags=re.IGNORECASE):
        return None

    # Alleen muziek/concerten. Tolhuistuin heeft daarnaast o.a. talks,
    # workshops, kunst, kinderprogramma en markten.
    music_signals = (
        "muziek", "concert", "band", "zanger", "zangeres", "songwriter",
        "live muziek", "livemuziek", "dj", "rock", "pop", "folk", "soul",
        "jazz", "hiphop", "hip-hop", "rap", "blues", "punk", "indie",
        "electronic", "elektronisch", "cumbia", "reggae", "dub "
    )
    lower_text = text.lower()
    if not any(signal in lower_text for signal in music_signals):
        return None

    concert_date, concert_time = _detail_date_time(page)
    if not concert_date:
        return None

    return {
        "artist": title,
        "venue": "Tolhuistuin",
        "city": "Amsterdam",
        "country": "NL",
        "date": concert_date,
        "time": concert_time or "",
        "source": "Tolhuistuin",
        "url": event_url.rstrip("/"),
    }


def scrape_tolhuistuin():
    print()
    print("=" * 60)
    print("TOLHUISTUIN")
    print("=" * 60)

    event_urls = []
    seen_urls = set()

    for agenda_url in TOLHUISTUIN_AGENDA_URLS:
        try:
            agenda_html = download_page_retry(agenda_url)
        except Exception as error:
            print("Tolhuistuin overzicht fout:", agenda_url, "-", str(error))
            continue

        for event_url in tolhuistuin_find_event_urls(agenda_html):
            key = normalize_url(event_url)
            if key not in seen_urls:
                seen_urls.add(key)
                event_urls.append(event_url)

    print("Eventlinks gevonden:", len(event_urls))

    concerts = []
    today = date.today()

    for event_url in event_urls:
        try:
            page = download_page_retry(event_url)
            concert = tolhuistuin_parse_event(page, event_url)
            if concert is None:
                continue
            parsed_date = date.fromisoformat(concert["date"])
            if parsed_date >= today:
                concerts.append(concert)
        except Exception as error:
            print("Tolhuistuin detailpagina fout:", event_url, "-", str(error))

    unique = {}
    for concert in concerts:
        key = (
            concert["artist"].strip().lower(),
            concert["date"],
            concert["venue"].strip().lower(),
        )
        unique[key] = concert

    result = list(unique.values())
    result.sort(key=lambda concert: (
        concert["date"],
        concert["time"],
        concert["artist"].lower(),
    ))

    print("Tolhuistuin eigen muziekprogramma:", len(result))
    return result
