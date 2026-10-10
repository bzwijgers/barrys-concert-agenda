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
from urllib.error import HTTPError
from threading import Lock
from collections import Counter
import json
import os
import re
import time
import unicodedata

DISCOVERY_URL = "https://app.ticketmaster.com/discovery/v2/events.json"
MUSIC_SEGMENT = "KZFzniwnSyZfZ7v7nJ"
FESTIVALS = ("pinkpop", "lowlands", "bospop")
# Discovery API has short-term rate limits. Do not rely on the general 5,000/day
# quota as evidence that requests can be issued in a tight loop.
_API_LOCK = Lock()
_NEXT_API_REQUEST = 0.0
_MIN_REQUEST_INTERVAL_SECONDS = 0.65
# Extra ticket products, parking and loge seats are NOT additional concerts.
TICKET_PRODUCT = re.compile(
    r"\b(?:premium seats?|platinum tickets?|venue premium packages?|"
    r"vip(?:-| )?(?:tickets?|package|arrangement)?|sky lounge|"
    r"loge|meet\s*(?:&|and)\s*greet|hospitality|parking|parkeer(?:ticket|kaart|plek)|"
    r"upgrades?|lockers?|fast\s*lane|early\s*entry|rolstoelplaats|"
    r"membership|lidmaatschap|club\s*card|jaarkaart)\b",
    re.I,
)
# These are hospitality product locations, not stages. Verified in the
# official Ticketmaster venue listings (Club=Venue Premium Packages,
# Sky Lounge=separate paid lounge products).
UPSSELL_VENUE = re.compile(
    r"\b(?:ziggo dome club|afas live (?:sky lounge|loge))\b", re.I
)
CANCELLED = {"cancelled", "canceled", "postponed", "rescheduled"}
GENERIC_NAME = {"", "concert", "muziek", "unknown"}


def _norm(value):
    value = unicodedata.normalize("NFKD", (value or "").replace("&", " and "))
    value = "".join(c for c in value if not unicodedata.combining(c))
    value = re.sub(r"[^a-z0-9]+", " ", value.casefold())
    return " ".join(value.split())


def _venue_label(venue):
    """Recover an event's official venue name only from its canonical venue URL.

    Some Discovery API event records have venue.name=null even for real shows
    such as Tokio Hotel / Jill Scott at AFAS Live. The same venue includes the
    official Ticketmaster venue page URL. Never infer a venue from artist,
    address, city alone, or from a secondary upsell's name.
    """
    explicit = (venue.get("name") or "").strip()
    if explicit:
        return explicit
    venue_url = (venue.get("url") or "").strip()
    parts = urlsplit(venue_url)
    if parts.scheme != "https" or (
        parts.hostname or ""
    ).lower().removeprefix("www.") != "ticketmaster.nl":
        return ""
    match = re.match(r"^/venue/([^/]+)-tickets(?:/|$)", parts.path, re.I)
    if not match:
        return ""
    slug = match.group(1).lower()
    city_slug = re.sub(r"[^a-z0-9]+", "-", _norm((venue.get("city") or {}).get("name")))
    if city_slug and slug.endswith("-" + city_slug):
        slug = slug[:-(len(city_slug) + 1)]
    exact = {
        "afas-live": "AFAS Live",
        "ziggo-dome": "Ziggo Dome",
        "rotterdam-ahoy": "Rotterdam Ahoy",
        "rtm-stage-rotterdam-ahoy": "RTM Stage - Rotterdam Ahoy",
        "johan-cruijff-arena": "Johan Cruijff ArenA",
        "koninklijk-theater-carre": "Koninklijk Theater Carré",
        "tivolivredenburg": "TivoliVredenburg",
        "melkweg": "Melkweg",
        "paradiso": "Paradiso",
    }
    return exact.get(slug, slug.replace("-", " ").title())


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
    if name.startswith("melkweg"):
        return "melkweg"
    if name.startswith("paard ") or name == "paard":
        return "paard"
    if name.startswith("metropool"):
        return "metropool"
    if name.startswith("paradiso noord") or name.startswith("paradiso tolhuistuin"):
        return "tolhuistuin"
    if name.startswith("paradiso"):
        return "paradiso"
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
    # The same artist may be followed by "+ support", an anniversary number
    # or "luistersessie" / "listening session" at the other provider.
    # Normalize these descriptions for matching ONLY; retain display titles.
    def identity(value):
        value = re.sub(r"\b(?:listening session|luistersessie)\b", "", value)
        value = re.sub(r"\s+(?:support|with support|and support)\b.*$", "", value)
        return re.sub(r"\s+", " ", value).strip()
    x, y = identity(x), identity(y)
    if not x or not y:
        return False
    if x == y:
        return True
    # Lower bound 5 allows real short artist names (Mogwai, Eihwar and
    # Quadeca) while avoiding ambiguous single words like "DJ" or "Live".
    if min(len(x), len(y)) >= 5 and (x.startswith(y + " ") or y.startswith(x + " ")):
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


def event_to_concert(event, today=None, country_code="NL"):
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
    expected_domain = "ticketmaster.be" if country_code == "BE" else "ticketmaster.nl"
    if domain != expected_domain or urlsplit(url).scheme != "https":
        return None
    venues = ((event.get("_embedded") or {}).get("venues") or [])
    if not venues:
        return None
    v = venues[0]
    country = (v.get("country") or {}).get("countryCode")
    if country != country_code:
        return None
    venue = _venue_label(v)
    city = ((v.get("city") or {}).get("name") or "").strip()
    if not venue or not city or UPSSELL_VENUE.search(venue):
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
    return dict(artist=artist, venue=venue, city=city, country=country_code,
                date=day, time=start_time, source="Ticketmaster " + country_code, url=url)


def _get_json(params, api_key):
    """Pace queries, retry short-lived rate limits, never log the secret URL."""
    global _NEXT_API_REQUEST
    url = DISCOVERY_URL + "?" + urlencode({**params, "apikey": api_key})
    req = Request(url, headers={"Accept": "application/json",
                                "User-Agent": "BarrysConcertAgenda/1.0"})
    for attempt in range(5):
        with _API_LOCK:
            wait = max(0.0, _NEXT_API_REQUEST - time.monotonic())
            if wait:
                time.sleep(wait)
            _NEXT_API_REQUEST = time.monotonic() + _MIN_REQUEST_INTERVAL_SECONDS
        try:
            with urlopen(req, timeout=25) as response:
                return json.load(response)
        except HTTPError as error:
            if error.code != 429 or attempt >= 4:
                # A raw HTTPError contains a URL with the API key; hide it.
                raise RuntimeError("Ticketmaster API HTTP " + str(error.code)) from None
            retry_after = error.headers.get("Retry-After", "")
            delay = min(45, float(retry_after)) if retry_after.isdecimal() else (3 * 2 ** attempt)
            print("Ticketmaster API request temporarily limited (429), retrying.", flush=True)
            time.sleep(delay)
    raise RuntimeError("Ticketmaster Discovery API temporarily unavailable")


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


def _fetch_range(start, end, api_key, extra=None, depth=0, getter=_get_json, country_code="NL"):
    """Avoid the Discovery API's 1000-result deep-paging limit by splitting dates."""
    params = {
        "countryCode": country_code,
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
        return (_fetch_range(start, midpoint, api_key, extra, depth + 1, getter, country_code=country_code)
                + _fetch_range(midpoint, end, api_key, extra, depth + 1, getter, country_code=country_code))
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
    # Query the full 24-month horizon in one range where possible.
    # Previously querying 24 separate months caused avoidable HTTP 429s.
    # _fetch_range() splits only when the result set exceeds the safe paging cap.
    events = _fetch_range(today, today + timedelta(days=730), key, getter=getter)
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
