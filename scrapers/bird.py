"""Complete BIRD live concert listings from BIRD's public Prismic agenda API.

The server-rendered /agenda/ page shows just six highlighted events. Prismic
is the website's own content source and exposes the full agenda with an
explicit 'live' category, including future events not in /concerts/.
"""
import json
import re
from datetime import datetime, timedelta
from html import unescape
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from .common import download_page_retry, normalize_url

PRISMIC_API = "https://bird-rotterdam.cdn.prismic.io/api/v2"
BIRD_EVENT_BASE = "https://bird-rotterdam.nl/event/"
AMSTERDAM = ZoneInfo("Europe/Amsterdam")


def _request_json(url):
    data = json.loads(download_page_retry(url))
    if not isinstance(data, dict):
        raise RuntimeError("BIRD Prismic sent invalid JSON structure")
    return data


def _rich_text(value):
    if isinstance(value, str):
        return unescape(value).strip()
    if isinstance(value, list):
        return " ".join(
            unescape(str(part.get("text", ""))).strip()
            for part in value if isinstance(part, dict) and part.get("text")
        ).strip()
    return ""


def _live_category(item):
    categories = (item.get("data") or {}).get("main_categories") or []
    return any(
        isinstance(entry, dict)
        and isinstance(entry.get("main_category"), dict)
        and entry["main_category"].get("uid", "").casefold() == "live"
        for entry in categories
    )


def parse_bird_prismic_event(item, today=None):
    if not isinstance(item, dict) or item.get("type") != "agenda":
        return None
    if not _live_category(item):
        return None

    data = item.get("data") or {}
    uid = item.get("uid", "")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", uid):
        return None

    title = _rich_text(data.get("title"))
    if not title:
        return None

    if re.search(r"\b(?:afgelast|geannuleerd|cancelled|canceled)\b", title, re.I):
        return None

    # BIRD sometimes labels DJ cafe sessions as both club AND live.
    # These aren't music performances in Barry's concert agenda.
    if re.search(r"\bcaf[eé]\s+dj\s+sessions\b", title, re.I):
        return None

    try:
        event_dt = datetime.fromisoformat(str(data["event_date"]).replace("Z", "+00:00"))
        if event_dt.tzinfo is None:
            raise ValueError("BIRD event datetime has no timezone")
        local_dt = event_dt.astimezone(AMSTERDAM)
    except (ValueError, TypeError, KeyError, AttributeError):
        return None

    today = today or datetime.now(AMSTERDAM).date()
    if local_dt.date() < today:
        return None

    start = local_dt.strftime("%H:%M")
    displayed_times = _rich_text(data.get("times"))
    match = re.search(r"\b(?:start|aanvang|show)\s*:?\s*([01]?\d|2[0-3]):([0-5]\d)", displayed_times, re.I)
    if match:
        start = f"{int(match.group(1)):02d}:{match.group(2)}"

    venue = "BIRD"
    title_context = str(data.get("meta_title") or "") + " " + str(data.get("top_title") or "")
    # Some concerts BIRD presents are held at partner venues.
    for candidate in ("Annabel", "V11", "LantarenVenster", "Maassilo"):
        if re.search(r"\b(?:at|in|@)\s+" + re.escape(candidate) + r"\b", title_context, re.I):
            venue = candidate
            break

    return {
        "artist": title,
        "venue": venue,
        "city": "Rotterdam",
        "country": "NL",
        "date": local_dt.date().isoformat(),
        "time": start,
        "source": "BIRD",
        "url": BIRD_EVENT_BASE + uid,
    }


def scrape_bird():
    print("\n" + "=" * 60 + "\nBIRD LIVE (OFFICIAL PRISMIC)\n" + "=" * 60, flush=True)
    api = _request_json(PRISMIC_API)
    master = next((r["ref"] for r in api.get("refs", []) if r.get("isMasterRef")), None)
    endpoint = ((api.get("forms") or {}).get("everything") or {}).get("action")
    if not master or not endpoint or not endpoint.startswith("https://bird-rotterdam.cdn.prismic.io/"):
        raise RuntimeError("BIRD API missing valid public search endpoint or master ref")

    today = datetime.now(AMSTERDAM).date()
    cutoff = (today - timedelta(days=1)).isoformat()
    predicate = f'[[at(document.type,"agenda")][date.after(my.agenda.event_date,"{cutoff}")]]'
    url = endpoint + "?" + urlencode({"ref": master, "q": predicate, "pageSize": 100, "page": 1})
    found = {}
    total = None
    seen_urls = set()

    for page in range(1, 21):
        if url in seen_urls:
            raise RuntimeError("BIRD Prismic pagination loop")
        seen_urls.add(url)

        payload = _request_json(url)
        results = payload.get("results")
        if not isinstance(results, list):
            raise RuntimeError("BIRD Prismic missing results list")
        if total is None:
            total = payload.get("total_results_size")
        for record in results:
            event = parse_bird_prismic_event(record, today=today)
            if event:
                found[normalize_url(event["url"])] = event

        url = payload.get("next_page")
        if not url:
            break
        if not url.startswith("https://bird-rotterdam.cdn.prismic.io/"):
            raise RuntimeError("BIRD Prismic unsafe pagination URL")
    else:
        raise RuntimeError("BIRD Prismic unexpectedly exceeded 20 pages")

    items = sorted(found.values(), key=lambda item: (item["date"], item["time"], item["artist"].casefold()))
    print("BIRD future agenda records:", total, "LIVE concerts:", len(items), flush=True)
    print("BIRD first LIVE events:", [(e["artist"], e["date"], e["time"]) for e in items[:6]], flush=True)
    if len(items) < 15:
        raise RuntimeError(f"BIRD LIVE feed unexpectedly small ({len(items)}); refusing partial scrape")
    return items
