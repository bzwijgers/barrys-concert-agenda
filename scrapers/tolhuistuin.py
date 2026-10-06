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

    event_urls = []
    seen_urls = set()

    for agenda_url in TOLHUISTUIN_AGENDA_URLS:
        try:
            agenda_html = download_page_retry(agenda_url)
        except Exception as error:
            print("Tolhuistuin overzicht fout:", agenda_url, "-", str(error))
            continue

        pages = [agenda_html]
        # De agenda laadt maar een eerste batch in de HTML. De site exposeert
        # vervolgpagina's via de "Laad meer"-links; volg die zolang ze bestaan.
        visited_pages = {normalize_url(agenda_url)}
        current_html = agenda_html
        while True:
            load_more = re.search(
                r'href=["\']([^"\']*(?:agenda|page|paged)[^"\']*)["\'][^>]*>[^<]*Laad meer',
                current_html,
                flags=re.IGNORECASE | re.DOTALL,
            )
            if not load_more:
                break
            href = html_module.unescape(load_more.group(1))
            next_url = href if href.startswith("http") else TOLHUISTUIN_BASE_URL.rstrip("/") + "/" + href.lstrip("/")
            key = normalize_url(next_url)
            if key in visited_pages:
                break
            visited_pages.add(key)
            try:
                current_html = download_page_retry(next_url)
            except Exception:
                break
            pages.append(current_html)

        for page_html in pages:
            for event_url in tolhuistuin_find_event_urls(page_html):
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
