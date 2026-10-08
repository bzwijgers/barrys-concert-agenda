from .common import *

# The Events Calendar exposes the same structured events as the official
# dB's site. The HTML list is JavaScript-rendered and has no event <a> URLs.
DBS_EVENTS_API = "https://dbstudio.nl/wp-json/tribe/events/v1/events/"


def parse_dbs_api_event(item):
    """Parse an event without guessing the title, date or start time."""
    try:
        raw_date = item.get("start_date", "")
        concert_date = datetime.fromisoformat(raw_date).date()
        if concert_date < date.today() or item.get("status") != "publish":
            return None
        title = html_module.unescape(item.get("title", "")).strip()
        title = re.sub(r"^\s*\*?\s*(?:sold\s*out|uitverkocht)\s*\*?\s*", "", title, flags=re.I).strip()
        url = item.get("url", "").split("?", 1)[0]
        if not title or not url.startswith("https://dbstudio.nl/event/"):
            return None
        venue = item.get("venue") or {}
        # The direct API is restricted to the concert category. Check that
        # the event really takes place at dB's and not an external venue.
        venue_name = html_module.unescape(str(venue.get("venue", "dB's")))
        if venue.get("city", "Utrecht").lower() != "utrecht":
            return None
        event_time = datetime.fromisoformat(raw_date).strftime("%H:%M")
        return {
            "artist": title,
            "venue": "dB's",
            "city": "Utrecht",
            "country": "NL",
            "date": concert_date.isoformat(),
            "time": event_time,
            "source": "dB's",
            "url": url.rstrip("/"),
        }
    except (ValueError, TypeError, AttributeError) as error:
        print("dB's API event not parsed:", item.get("id"), str(error))
        return None


def scrape_dbs():
    print()
    print("=" * 60)
    print("dB's UTRECHT (official events API)")
    print("=" * 60)

    concerts = {}
    total_pages = 1
    for page_no in range(1, 21):
        # The API specifies 10 events by default. Explicit pagination
        # prevents quietly losing concerts after the first page.
        api_url = DBS_EVENTS_API + "?categories=concert&per_page=50&page=" + str(page_no)
        response = json.loads(download_page_retry(api_url, attempts=3))
        if not isinstance(response, dict) or not isinstance(response.get("events"), list):
            raise RuntimeError("dB's API returned an invalid event list")
        total_pages = int(response.get("total_pages") or 1)
        for entry in response["events"]:
            concert = parse_dbs_api_event(entry)
            if concert:
                concerts[normalize_url(concert["url"])] = concert
        print("dB's API page", page_no, "/", total_pages,
              "events:", len(response["events"]), flush=True)
        if page_no >= total_pages:
            break
    else:
        raise RuntimeError("dB's API pagination exceeds 20 pages")

    if not concerts:
        raise RuntimeError("dB's: zero future concerts from the official API")
    result = sorted(concerts.values(), key=lambda x: (x["date"], x["artist"].lower()))
    print("dB's concerten:", len(result))
    return result
