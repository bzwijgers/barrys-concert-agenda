from .common import *
from urllib.parse import urlencode
import json
import os
import unicodedata


PARSE_TICKETSWAP_API = "https://api.parse.bot/scraper/ce18a647-b0e2-4a1f-a4a4-61773779bffa/search_events"


def _ts_words(value):
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return set(re.findall(r"[a-z0-9]+", value.lower()))


def _ts_link_date(url):
    match = re.search(r"-(20\d{2}-\d{2}-\d{2})-[A-Za-z0-9]+$", url or "")
    return match.group(1) if match else ""


def _ts_candidate_score(concert, event):
    url = ((event.get("uri") or {}).get("url") or "").strip()
    if _ts_link_date(url) != concert.get("date", ""):
        return -1

    artist_words = {w for w in _ts_words(concert.get("artist", "")) if len(w) >= 2}
    event_words = _ts_words(event.get("name", ""))
    if not artist_words:
        return -1
    hits = len(artist_words & event_words)
    if hits < max(1, (len(artist_words) + 1) // 2):
        return -1

    score = hits * 10
    score += len(_ts_words(concert.get("venue", "")) & _ts_words(event.get("locationName", ""))) * 4
    score += len(_ts_words(concert.get("city", "")) & _ts_words(event.get("cityName", ""))) * 4
    return score


def _search_events(query, api_key):
    url = PARSE_TICKETSWAP_API + "?" + urlencode({"query": query})
    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "X-API-Key": api_key,
        "Accept": "application/json",
    })
    with urllib.request.urlopen(req, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))
    data = payload.get("data", payload)
    return data.get("results", []) if isinstance(data, dict) else []


def enrich_ticketswap_urls(concerts):
    print()
    print("=" * 60)
    print("TICKETSWAP EXACTE EVENTLINKS")
    print("=" * 60)

    api_key = os.environ.get("PARSE_API_KEY", "").strip()
    if not api_key:
        print("TicketSwap verrijking overgeslagen: PARSE_API_KEY ontbreekt")
        return concerts

    cache = {}
    matched = 0
    for concert in concerts:
        artist = concert.get("artist", "").strip()
        if not artist or not concert.get("date"):
            continue

        key = artist.lower()
        if key not in cache:
            try:
                cache[key] = _search_events(artist, api_key)
            except Exception as error:
                print("TicketSwap zoekfout:", artist, str(error))
                cache[key] = []

        scored = [(_ts_candidate_score(concert, event), event) for event in cache[key]]
        scored = [(score, event) for score, event in scored if score >= 0]
        if not scored:
            continue
        scored.sort(key=lambda item: item[0], reverse=True)
        best_score, event = scored[0]
        if len(scored) > 1 and scored[1][0] == best_score:
            continue

        url = ((event.get("uri") or {}).get("url") or "").strip()
        if not url:
            continue
        concert["ticketSwapUrl"] = url.replace("https://www.ticketswap.com/", "https://www.ticketswap.nl/")
        matched += 1
        print("TicketSwap match:", artist, concert.get("date"), "->", concert["ticketSwapUrl"])

    print("Exact gekoppelde TicketSwap-events:", matched)
    return concerts
