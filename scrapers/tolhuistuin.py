from .common import *
from .common import _detail_title, _detail_date_time

TOLHUISTUIN_AGENDA_URLS = (
    "https://tolhuistuin.nl/agenda/",
)
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

    # De agenda wordt client-side gevuld. Server-side pagina's geven wel
    # eventlinks en detailpagina's linken naar aanbevolen evenementen.
    seed_urls = ("https://tolhuistuin.nl/", "https://tolhuistuin.nl/zoeken")
    queue = []
    seen_urls = set()

    for seed_url in seed_urls:
        try:
            page = download_page_retry(seed_url)
        except Exception as error:
            print("Tolhuistuin startpagina fout:", seed_url, "-", str(error))
            continue
        for event_url in tolhuistuin_find_event_urls(page):
            key = normalize_url(event_url)
            if key not in seen_urls:
                seen_urls.add(key)
                queue.append(event_url)

    print("Eerste eventlinks gevonden:", len(queue))

    concerts = []
    today = date.today()
    processed = 0
    max_events = 500

    while queue and processed < max_events:
        event_url = queue.pop(0)
        processed += 1
        try:
            page = download_page_retry(event_url)
            for linked_url in tolhuistuin_find_event_urls(page):
                key = normalize_url(linked_url)
                if key not in seen_urls and len(seen_urls) < max_events:
                    seen_urls.add(key)
                    queue.append(linked_url)

            concert = tolhuistuin_parse_event(page, event_url)
            if concert is None:
                continue
            parsed_date = date.fromisoformat(concert["date"])
            if parsed_date >= today:
                concerts.append(concert)
        except Exception as error:
            print("Tolhuistuin detailpagina fout:", event_url, "-", str(error))

    print("Tolhuistuin eventlinks ontdekt:", len(seen_urls))
    print("Tolhuistuin detailpagina's verwerkt:", processed)

    unique = {}
    for concert in concerts:
        key = (concert["artist"].strip().lower(), concert["date"], concert["venue"].strip().lower())
        unique[key] = concert

    result = list(unique.values())
    result.sort(key=lambda concert: (concert["date"], concert["time"], concert["artist"].lower()))
    print("Tolhuistuin eigen muziekprogramma:", len(result))
    return result
