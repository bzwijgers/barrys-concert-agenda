"""Ticketmaster Netherlands music & festival events via the *official* Discovery API.

Never scrape ticketmaster.nl web pages. Supply TICKETMASTER_API_KEY as a
GitHub Actions secret. A missing key disables this optional source without
interrupting the existing independent venue feeds.

Discovery API documentation: https://developer.ticketmaster.com/products-and-docs/apis/discovery/
"""
from __future__ import annotations

from datetime import datetime, date, timedelta
from difflib import SequenceMatcher
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen
from collections import Counter
import json
import os
import re
import time
import unicodedata

DISCOVERY_URL = "https://app.ticketmaster.com/discovery/v2/events.json"
MUSIC_SEGMENT = "KZFzniwnSyZfZ7v7nJ"
FESTIVALS = ("pinkpop", "lowlands", "bospop")
# Extra ticket products, parking and loge seats are NOT additional concerts.
TICKET_PRODUCT = re.compile(
    r"\b(?:premium seats?|platinum tickets?|vip(?:-| )?(?:tickets?|package|arrangement)?|"
    r"loge|meet\s*(?:&|and)\s*greet|hospitality|parking|parkeer(?:ticket|kaart|plek)|"
    r"upgrades?|lockers?|fast\s*lane|early\s*entry|rolstoelplaats|"
    r"membership|lidmaatschap|club\s*card|jaarkaart)\b",
    re.I,
)
CANCELLED = {"cancelled", "canceled", "postponed", "rescheduled"}
GENERIC_NAME = {"", "concert", "muziek", "unknown"}


def _norm(value):
    value = unicodedata.normalize("NFKD", (value or "").replace("&", " and "))
    value = "".join(c for c in value if not unicodedata.combining(c))
    value = re.sub(r"[^a-z0-9]+", " ", value.casefold())
    return " ".join(value.split())


def _venue_name(value):
    name = _norm(value).replace("poppodium ", "").strip()
    # Ahoy has several mutually equivalent marketed labels.
    if "ahoy" in name or name.startswith("rtm stage"):
        return "rotterdam ahoy"
    if name.startswith("afas live"):
        return "afas live"
    if name.startswith("ziggo dome"):
        return "ziggo dome"
    if name.startswith("tivolivredenburg"):
        return "tivolivredenburg"
    if name.startswith("spot de oosterpoort") or name == "de oosterpoort":
        return "de oosterpoort"
    return name


def _concert_title(name):
    name = (name or "").strip()
    # Drop only clear marketing blurbs rather than genuine support acts.
    name = re.split(r"\s+(?:\||[-–—])\s+(?:premium seats?|platinum|vip|loge)\b", name, maxsplit=1, flags=re.I)[0]
    name = re.split(r"\s+[-–—]\s+(?:world|europe(?:an)?|live|rise|the)\b.+\btour\b", name, maxsplit=1, flags=re.I)[0]
    return name.strip()


def _same_performance(a, b):
    if a.get("date") != b.get("date"):
        return False
    if _norm(a.get("city")) != _norm(b.get("city")):
        return False
    if _venue_name(a.get("venue")) != _venue_name(b.get("venue")):
        return False
    x = _norm(_concert_title(a.get("artist")))
    y = _norm(_concert_title(b.get("artist")))
    if not x or not y:
        return False
    if x == y:
        return True
    # Ticketmaster often adds "The [Tour name]" to the same headliner.
    # Require a meaningful complete artist name, not one common word.
    if min(len(x), len(y)) >= 8 and (x.startswith(y + " ") or y.startswith(x + " ")):
        return True
    return SequenceMatcher(None, x, y).ratio() >= 0.92


def merge_ticketmaster(existing, incoming):
    """Keep the official venue's event URL as the single canonical listing.

    Only new Ticketmaster records are evaluated here; existing venue events
    are never merged with each other. Separate days/locations remain separate.
    """
    added, repeats = [], 0
    by_day_city = {}
    for show in existing:
        by_day_city.setdefault((show.get("date"), _norm(show.get("city"))), []).append(show)
    for show in incoming:
        key = show.get("date"), _norm(show.get("city"))
        siblings = by_day_city.get(key, ())
        if any(_same_performance(show, other) for other in siblings):
            repeats += 1
            continue
        added.append(show)
        by_day_city.setdefault(key, []).append(show)
    return added, repeats


def _festival_identity(name):
    title = _norm(name)
    for festival in FESTIVALS:
        if title == festival or title.startswith(festival + " "):
            return festival
    return None


def _music_classification(event):
    classifications = event.get("classifications") or []
    if not classifications:
        return False
    for c in classifications:
        name = _norm((c.get("segment") or {}).get("name"))
        sid = (c.get("segment") or {}).get("id")
        if name == "music" or sid == MUSIC_SEGMENT:
            return True
    return False


def event_to_concert(event, today=None):
    """Validate event-level time, country and location; reject ticket products."""
    if event.get("type") not in ("event", None):
        return None
    status = ((event.get("dates") or {}).get("status") or {}).get("code", "").lower()
    if status in CANCELLED:
        return None
    raw_name = (event.get("name") or "").strip()
    # Some festival admissions are categorized under Festivals, not Music.
    # Their unmistakable festival title is enough to include the event,
    # but only after the NL venue and date checks below.
    if not _music_classification(event) and _festival_identity(raw_name) is None:
        return None
    if not raw_name or TICKET_PRODUCT.search(raw_name):
        return None
    url = (event.get("url") or "").strip()
    domain = (urlsplit(url).hostname or "").lower().removeprefix("www.")
    if domain != "ticketmaster.nl" or urlsplit(url).scheme != "https":
        return None
    venues = ((event.get("_embedded") or {}).get("venues") or [])
    if not venues:
        return None
    v = venues[0]
    country = (v.get("country") or {}).get("countryCode")
    if country != "NL":
        return None
    venue = (v.get("name") or "").strip()
    city = ((v.get("city") or {}).get("name") or "").strip()
    if not venue or not city:
        return None
    start = ((event.get("dates") or {}).get("start") or {})
    day = start.get("localDate") or ""
    if not re.fullmatch(r"20\d\d-\d\d-\d\d", day):
        return None
    try:
        date.fromisoformat(day)
    except ValueError:
        return None
    if day < (today or date.today().isoformat()):
        return None
    show_time = start.get("localTime") or ""
    tm = re.fullmatch(r"([01]\d|2[0-3]):([0-5]\d)(?::\d\d)?", show_time)
    start_time = f"{tm.group(1)}:{tm.group(2)}" if tm else ""
    artist = _concert_title(raw_name)
    if _norm(artist) in GENERIC_NAME:
        return None
    return dict(artist=artist, venue=venue, city=city, country="NL",
                date=day, time=start_time, source="Ticketmaster NL", url=url)


def _get_json(params, api_key):
    url = DISCOVERY_URL + "?" + urlencode({**params, "apikey": api_key})
    req = Request(url, headers={"Accept": "application/json",
                                "User-Agent": "BarrysConcertAgenda/1.0"})
    with urlopen(req, timeout=25) as response:
        return json.load(response)


def _months_from_today(today, months=24):
    # Month intervals UTC for the API; event localDate is what we display.
    first = date(today.year, today.month, 1)
    for index in range(months + 1):
        month = first.month - 1 + index
        y, m = first.year + month // 12, month % 12 + 1
        next_year, next_month = (y + 1, 1) if m == 12 else (y, m + 1)
        start = date(y, m, 1)
        end = date(next_year, next_month, 1)
        if start >= today + timedelta(days=730):
            break
        yield max(start, today), end


def _fetch_range(start, end, api_key, extra=None, depth=0, getter=_get_json):
    """Avoid the Discovery API's 1000-result deep-paging limit by splitting dates."""
    params = {
        "countryCode": "NL",
        "segmentId": MUSIC_SEGMENT,
        "startDateTime": start.isoformat() + "T00:00:00Z",
        "endDateTime": end.isoformat() + "T00:00:00Z",
        "sort": "date,asc",
        "size": 200,
    }
    if extra:
        params.update(extra)
    first = getter({**params, "page": 0}, api_key)
    count = int((first.get("page") or {}).get("totalElements", 0))
    total_pages = int((first.get("page") or {}).get("totalPages", 1))
    if count > 950 and (end - start).days > 1 and depth < 12:
        midpoint = start + (end - start) // 2
        return (_fetch_range(start, midpoint, api_key, extra, depth + 1, getter)
                + _fetch_range(midpoint, end, api_key, extra, depth + 1, getter))
    if count > 1000:
        raise RuntimeError("Ticketmaster results exceed API paging limit in " + start.isoformat())
    out = (first.get("_embedded") or {}).get("events") or []
    for page in range(1, total_pages):
        item = getter({**params, "page": page}, api_key)
        out.extend((item.get("_embedded") or {}).get("events") or [])
    return out


def scrape_ticketmaster_nl(api_key=None, today=None, getter=_get_json):
    """Returns only concert/festival event records in NL. No key -> disabled."""
    key = (api_key if api_key is not None else os.getenv("TICKETMASTER_API_KEY", "")).strip()
    if not key:
        print("Ticketmaster NL: API key ontbreekt; officiële bron nog niet actief.", flush=True)
        return []
    today = today or date.today()
    events = []
    for start, end in _months_from_today(today):
        events.extend(_fetch_range(start, end, key, getter=getter))
    # Festivals may not all be assigned to the Music segment. Search by name
    # without the segment restriction, then still enforce Music classification.
    for festival in FESTIVALS:
        params = {"countryCode": "NL", "keyword": festival, "size": 200}
        page = getter(params, key)
        events.extend((page.get("_embedded") or {}).get("events") or [])
    concerts = {}
    for event in events:
        show = event_to_concert(event, today=today.isoformat())
        if show is None:
            continue
        # Same event can occur in a monthly segment response and a festival search.
        k = (show["date"], _norm(show["city"]), _venue_name(show["venue"]), _norm(_concert_title(show["artist"])))
        concerts.setdefault(k, show)
    # Avoid different "Friday / Saturday / weekend / regular / day ticket"
    # products presenting the same festival as several different concerts.
    # One festival per annual edition, displayed on the earliest event day.
    by_festival, regular = {}, []
    for show in concerts.values():
        festival = _festival_identity(show["artist"])
        if festival:
            edition = (festival, show["date"][:4])
            old = by_festival.get(edition)
            if old is None or show["date"] < old["date"]:
                by_festival[edition] = show
        else:
            regular.append(show)
    final = regular + list(by_festival.values())
    counts = Counter(x["venue"] for x in final)
    print("Ticketmaster NL: valid music/festival shows", len(final),
          "venues:", len(counts), "festival editions:", len(by_festival), flush=True)
    return final
