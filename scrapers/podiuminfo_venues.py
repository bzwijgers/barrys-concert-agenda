"""Fallback venue schedules from Podiuminfo MusicEvent metadata.

These two venues cannot currently be crawled directly from GitHub Actions:
Amare redirects automated requests to its CSQ challenge, and Het Bolwerk's
legacy site blocks them. Use only structured records linked to the exact venue.
"""
from .common import *
from zoneinfo import ZoneInfo

PODIUMINFO_VENUES = {
    "Dynamo": (
        "https://www.podiuminfo.nl/podium/187/concerten/Dynamo/Eindhoven/",
        "Dynamo",
        "Eindhoven",
    ),
    "Bolwerk": (
        "https://www.podiuminfo.nl/podium/44/concerten/Het-Bolwerk/Sneek/",
        "Het Bolwerk",
        "Sneek",
    ),
    "Amare": (
        "https://www.podiuminfo.nl/podium/5334/concerten/Amare/Den-Haag/",
        "Amare",
        "Den Haag",
    ),
}


def parse_podiuminfo_music_event(item, source, target_venue, city):
    if not isinstance(item, dict) or item.get("@type") not in ("MusicEvent", "Event"):
        return None
    actual_venue = item.get("location") or {}
    if not isinstance(actual_venue, dict):
        return None
    if actual_venue.get("name", "").strip().casefold() != target_venue.casefold():
        return None
    if str(item.get("eventStatus", "")).endswith("EventCancelled"):
        return None
    name = html_module.unescape(str(item.get("name", "")).strip())
    name = re.sub(r"\s+@\s+" + re.escape(target_venue) + r"\s*$",
                  "", name, flags=re.I).strip()
    url = str(item.get("url", "")).split("#", 1)[0].strip()
    if not name or not url.startswith("https://www.podiuminfo.nl/concert/"):
        return None
    unwanted = r"social dance|workshop|meet.?up|masterclass|college|stand.?up|cabaret|comedy|dance:?|party|feest|disco|open dag|lezing|rondleiding|ballet"
    if re.search(unwanted, name, flags=re.I):
        return None
    try:
        date_value = item.get("startDate", "")
        event_dt = datetime.fromisoformat(date_value.replace("Z", "+00:00"))
        if event_dt.tzinfo:
            event_dt = event_dt.astimezone(ZoneInfo("Europe/Amsterdam"))
        if event_dt.date() < date.today():
            return None
        event_date, event_time = event_dt.date().isoformat(), event_dt.strftime("%H:%M")
    except (TypeError, ValueError, AttributeError):
        return None
    return {
        "artist": name,
        "venue": target_venue,
        "city": city,
        "country": "NL",
        "date": event_date,
        "time": event_time,
        "source": source,
        "url": url.rstrip("/"),
    }


def scrape_podiuminfo_venues():
    combined = []
    for source, (url, venue, city) in PODIUMINFO_VENUES.items():
        try:
            html = download_page_retry(url, attempts=2)
            blobs = re.findall(
                r'''<script[^>]*type=["']application/ld\+json["'][^>]*>(.*?)</script>''',
                html, flags=re.I | re.S,
            )
            matching = {}
            for blob in blobs:
                try:
                    item = json.loads(html_module.unescape(blob))
                except (ValueError, TypeError):
                    continue
                event = parse_podiuminfo_music_event(item, source, venue, city)
                if event:
                    matching[normalize_url(event["url"])] = event
            print("Podiuminfo", source, "future music events:", len(matching), flush=True)
            if not matching:
                raise RuntimeError(source + " returned no matching event records")
            combined.extend(matching.values())
        except Exception as error:
            print("Podiuminfo", source, "ERROR:", str(error), flush=True)
    return combined
