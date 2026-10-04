from .common import *

DBS_CONCERT_URL = "https://dbstudio.nl/events/categorie/alles/concert/lijst/"
DBS_BASE_URL = "https://dbstudio.nl"


def scrape_dbs():
    print()
    print("=" * 60)
    print("dB's UTRECHT")
    print("=" * 60)

    page = download_page_retry(DBS_CONCERT_URL)
    urls = find_site_event_urls(page, DBS_BASE_URL, "/event/")
    today = date.today()
    concerts = []

    for url in urls:
        try:
            detail = download_page_retry(url)
            title = _detail_title(detail).strip()
            if not title:
                continue
            title = re.sub(r"^\*?\s*sold\s*out\s*\*?\s*", "", title, flags=re.I).strip()
            event_date, event_time = _detail_date_time(detail)
            if not event_date or date.fromisoformat(event_date) < today:
                continue
            text = clean_text(detail).lower()
            if "afgelast" in text or "geannuleerd" in text or "cancelled" in text:
                continue

            concerts.append({
                "artist": title,
                "venue": "dB's",
                "city": "Utrecht",
                "country": "NL",
                "date": event_date,
                "time": event_time or "",
                "source": "dB's",
                "url": url.rstrip("/"),
            })
        except Exception as error:
            print("dB's event overgeslagen:", url, str(error))

    unique = {}
    for concert in concerts:
        unique[(concert["artist"].lower(), concert["date"])] = concert
    result = sorted(unique.values(), key=lambda x: (x["date"], x["artist"].lower()))
    print("dB's concerten:", len(result))
    return result
