from .common import *

GEBOUW_T_AGENDA_URL = "https://gebouw-t.nl/agenda/"
GEBOUW_T_BASE_URL = "https://gebouw-t.nl"


def gebouw_t_find_event_urls(page):
    return find_site_event_urls(page, GEBOUW_T_BASE_URL, "/agenda/")


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
    if any(x in lower for x in reject):
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
        date_match = re.search(r"\\b(?:ma|di|wo|do|vr|za|zo)\\s+(\\d{1,2})\\s+(jan|feb|mrt|apr|mei|jun|jul|aug|sep|okt|nov|dec)[a-z]*\\s+[’']?(\\d{2}|20\\d{2})\\b", text, flags=re.I)
        if date_match:
            day = int(date_match.group(1))
            month = months[date_match.group(2).lower()[:3]]
            raw_year = int(date_match.group(3))
            year = raw_year if raw_year >= 2000 else 2000 + raw_year
            event_date = date(year, month, day).isoformat()
        time_match = re.search(r"(?:aanvang|tijd)\\s*:?\\s*(\\d{1,2}[:.]\\d{2})", text, flags=re.I)
        if time_match:
            event_time = time_match.group(1).replace(".", ":")
    if not event_date:
        return None

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
    agenda = download_page_retry(GEBOUW_T_AGENDA_URL)
    urls = gebouw_t_find_event_urls(agenda)
    today = date.today()
    concerts = []

    for url in urls:
        try:
            event = gebouw_t_parse_event(download_page_retry(url), url)
            if event and date.fromisoformat(event["date"]) >= today:
                concerts.append(event)
        except Exception as error:
            print("Gebouw-T event overgeslagen:", url, str(error))

    unique = {}
    for concert in concerts:
        key = (concert["artist"].lower(), concert["date"], concert["venue"].lower())
        unique[key] = concert

    result = sorted(unique.values(), key=lambda x: (x["date"], x["artist"].lower()))
    print("Gebouw-T concerten:", len(result))
    return result
