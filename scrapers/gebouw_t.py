from .common import *
from .common import _detail_title, _detail_date_time
from html.parser import HTMLParser

GEBOUW_T_AGENDA_URL = "https://gebouw-t.nl/agenda/"
GEBOUW_T_BASE_URL = "https://gebouw-t.nl"


class _GebouwTLinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        href = dict(attrs).get("href", "")
        if href:
            self.urls.append(href)


def gebouw_t_find_event_urls(page):
    # The official site uses unquoted attributes:
    # <a href=https://gebouw-t.nl/agenda/marble-sounds/ ...>
    # The generic quoted-href regex silently returned zero events.
    parser = _GebouwTLinkParser()
    parser.feed(page)
    urls = []
    seen = set()
    for href in parser.urls:
        if href.startswith("/"):
            href = GEBOUW_T_BASE_URL + href
        if not href.startswith(GEBOUW_T_BASE_URL + "/agenda/"):
            continue
        event_url = href.split("?", 1)[0].split("#", 1)[0].rstrip("/")
        slug = event_url.split("/agenda/", 1)[-1].strip("/")
        if not slug or slug.startswith("page/") or slug == "feed":
            continue
        key = normalize_url(event_url)
        if key not in seen:
            urls.append(event_url)
            seen.add(key)
    return urls


def gebouw_t_parse_event(page, event_url):
    title = _detail_title(page).strip()
    if not title or title.lower() == "agenda":
        return None

    text = clean_text(page)
    lower = text.lower()
    if any(x in lower for x in ("dit evenement is afgelast", "dit evenement is geannuleerd")):
        return None

    # Barry's agenda is voor live muziek; geen quiz/comedy/algemene clubavonden.
    reject = (
        "comedynight", "muziekquiz", "themafeest", "quiz'm",
        "vroegzat", "80's verantwoord", "90's now"
    )
    normal_title = title.casefold().replace("’", "'").replace("‘", "'")
    if any(x in normal_title for x in reject):
        return None
    if re.search(r"\bgenre\s*:\s*themafeest\b", text[:1800], re.I):
        return None
    # A themed DJ party is not an artist playing a live concert.
    if "toppop yeah! the party" in normal_title:
        return None

    music_signals = (
        "concert", "live", "band", "zanger", "zangeres", "songwriter",
        "rock", "pop", "metal", "blues", "jazz", "indie", "soul",
        "punk", "reggae", "tribute", "gitaar", "muziek"
    )
    if not any(x in lower for x in music_signals):
        return None

    event_date, event_time = _detail_date_time(page)
    if not event_date:
        months = {
            "jan": 1, "feb": 2, "mrt": 3, "apr": 4, "mei": 5, "jun": 6,
            "jul": 7, "aug": 8, "sep": 9, "okt": 10, "nov": 11, "dec": 12,
        }
        date_match = re.search(r"\b(?:ma|di|wo|do|vr|za|zo)\s+(\d{1,2})\s+(jan|feb|mrt|apr|mei|jun|jul|aug|sep|okt|nov|dec)[a-z]*\s+[’']?(\d{2}|20\d{2})\b", text, flags=re.I)
        if date_match:
            day = int(date_match.group(1))
            month = months[date_match.group(2).lower()[:3]]
            raw_year = int(date_match.group(3))
            year = raw_year if raw_year >= 2000 else 2000 + raw_year
            event_date = date(year, month, day).isoformat()
        time_match = re.search(r"(?:aanvang|tijd)\s*:?\s*(\d{1,2}[:.]\d{2})", text, flags=re.I)
        if time_match:
            event_time = time_match.group(1).replace(".", ":")
    if not event_date:
        return None

    # A date-only schema.org startDate can prevent _detail_date_time()
    # from reading the actual show time. Read the official 'Aanvang' field
    # regardless of whether the structured date was present.
    official_start = re.search(
        r"\baanvang\s*:?\s*([01]?\d|2[0-3])[:.]([0-5]\d)\b",
        text, flags=re.I,
    )
    if official_start:
        event_time = f"{int(official_start.group(1)):02d}:{official_start.group(2)}"

    location = "Gebouw-T"
    city = "Bergen op Zoom"
    location_match = re.search(r"locatie:\s*([^•]+?)(?:datum:|zaal open:|aanvang:|einde:|genre:)", text, flags=re.I)
    if location_match:
        raw_location = location_match.group(1).strip()
        if "maagd" in raw_location.lower() or "theater de maagd" in lower[:1200]:
            location = "Theater De Maagd"
        elif raw_location and raw_location.lower() not in ("zaal", "grote zaal"):
            location = raw_location

    return {
        "artist": title,
        "venue": location,
        "city": city,
        "country": "NL",
        "date": event_date,
        "time": event_time or "",
        "source": "Gebouw-T",
        "url": event_url.rstrip("/"),
    }


def scrape_gebouw_t():
    print()
    print("=" * 60)
    print("GEBOUW-T")
    print("=" * 60)

    # The official agenda is paginated at /agenda/page/<n>/.
    # Reading only page one lost all concerts beyond October.
    discovered = []
    seen_urls = set()
    for page_no in range(1, 11):
        agenda_url = (
            GEBOUW_T_AGENDA_URL if page_no == 1
            else GEBOUW_T_AGENDA_URL + "page/" + str(page_no) + "/"
        )
        try:
            html = download_page_retry(agenda_url, attempts=2)
        except HTTPError as error:
            if error.code in (404, 410) and page_no > 1:
                break
            raise
        urls = gebouw_t_find_event_urls(html)
        added = 0
        for url in urls:
            key = normalize_url(url)
            if key not in seen_urls:
                discovered.append(url)
                seen_urls.add(key)
                added += 1
        print("Gebouw-T agenda page", page_no, "new links:", added, flush=True)
        if not urls or added == 0:
            break

    if not discovered:
        raise RuntimeError("Gebouw-T agenda has no event links")
    concerts = []
    failed = 0
    today = date.today()

    def parse_link(url):
        return gebouw_t_parse_event(download_page_retry(url, attempts=2), url)

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(parse_link, url): url for url in discovered}
        for future in as_completed(futures):
            try:
                event = future.result()
                if event and date.fromisoformat(event["date"]) >= today:
                    concerts.append(event)
            except Exception as error:
                failed += 1
                if failed <= 4:
                    print("Gebouw-T event error:", futures[future], str(error), flush=True)

    unique = {}
    for concert in concerts:
        unique[normalize_url(concert["url"])] = concert
    result = sorted(
        unique.values(), key=lambda x: (x["date"], x["artist"].lower())
    )
    print("Gebouw-T found:", len(discovered), "parsed:", len(result),
          "failed:", failed, flush=True)
    if not result:
        raise RuntimeError("Gebouw-T returned zero upcoming concerts")
    return result
