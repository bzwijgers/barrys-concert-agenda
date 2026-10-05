from .common import *
from datetime import datetime
import html
import time
import unicodedata
from urllib.parse import parse_qs, quote_plus, unquote, urlparse
from urllib.request import Request, urlopen


SEARCH_URL = "https://html.duckduckgo.com/html/?q={query}"
TICKETSWAP_EVENT_RE = re.compile(
    r"https?://(?:www\.)?ticketswap\.(?:nl|com)/concert-tickets/[^\s\"'<>]+",
    re.I,
)


def _ts_words(value):
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return set(re.findall(r"[a-z0-9]+", value.lower()))


def _ts_link_date(url):
    match = re.search(r"-(20\d{2}-\d{2}-\d{2})-[A-Za-z0-9]+(?:[/?#].*)?$", url or "")
    return match.group(1) if match else ""


def _ts_candidate_score(concert, url):
    if _ts_link_date(url) != concert.get("date", ""):
        return -1
    slug_words = _ts_words((url or "").split("?", 1)[0].rsplit("/", 1)[-1])
    artist_words = {w for w in _ts_words(concert.get("artist", "")) if len(w) >= 2}
    if not artist_words:
        return -1
    hits = len(artist_words & slug_words)
    if hits < max(1, (len(artist_words) + 1) // 2):
        return -1

    venue_hits = len(_ts_words(concert.get("venue", "")) & slug_words)
    city_hits = len(_ts_words(concert.get("city", "")) & slug_words)
    if venue_hits == 0 and city_hits == 0:
        return -1

    return hits * 10 + venue_hits * 3 + city_hits * 3


def _unwrap_search_url(value):
    value = html.unescape(value or "")
    if value.startswith("//"):
        value = "https:" + value
    parsed = urlparse(value)
    if "duckduckgo.com" in parsed.netloc and parsed.path.startswith("/l/"):
        target = parse_qs(parsed.query).get("uddg", [""])[0]
        if target:
            return unquote(target)
    return value


def _extract_candidates(page):
    candidates = []
    for raw in re.findall(r'href=[\"\']([^\"\']+)', page or "", flags=re.I):
        url = _unwrap_search_url(raw)
        match = TICKETSWAP_EVENT_RE.search(url)
        if match:
            candidates.append(match.group(0).rstrip(".,);]"))
    # Some engines expose the destination as escaped/plain text as well.
    decoded = html.unescape(page or "")
    candidates.extend(TICKETSWAP_EVENT_RE.findall(decoded))
    return list(dict.fromkeys(candidates))


def _search_candidates(concert):
    query = (
        'site:ticketswap.com/concert-tickets OR site:ticketswap.nl/concert-tickets '
        f'\"{concert.get("artist", "")}\" '
        f'\"{concert.get("city", "")}\" '
        f'{concert.get("date", "")}'
    )
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/154.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "nl-NL,nl;q=0.9,en;q=0.8",
    }
    request = Request(
        SEARCH_URL.format(query=quote_plus(query)),
        headers=headers,
    )
    with urlopen(request, timeout=15) as response:
        page = response.read().decode("utf-8", errors="replace")
    return _extract_candidates(page)


def enrich_ticketswap_urls(concerts):
    existing = sum(1 for concert in concerts if concert.get("ticketSwapUrl"))
    found = 0
    checked = 0

    print()
    print("=" * 60)
    print("TICKETSWAP EXACTE EVENTLINKS")
    print("=" * 60)
    print("Bestaande exacte TicketSwap-links:", existing)

    pending = [concert for concert in concerts if not concert.get("ticketSwapUrl")]
    pending.sort(
        key=lambda concert: (
            0 if concert.get("artist", "").strip().lower() == "gavin degraw"
                 and concert.get("date") == "2026-10-13" else 1,
            concert.get("date", ""),
        )
    )

    # Small rotating-friendly batch: search engines are discovery helpers,
    # not a bulk API. Existing links remain cached in concerts.json.
    for concert in pending[:20]:

        # Start conservatively: only concerts in the next 180 days.
        try:
            concert_date = datetime.strptime(concert.get("date", ""), "%Y-%m-%d").date()
        except Exception:
            continue
        days = (concert_date - datetime.now().date()).days
        if days < 0 or days > 180:
            continue

        checked += 1
        try:
            candidates = _search_candidates(concert)
        except Exception as error:
            print("TicketSwap zoekfout:", concert.get("artist"), str(error))
            continue

        scored = sorted(
            ((_ts_candidate_score(concert, url), url) for url in candidates),
            reverse=True,
        )
        best = next(((score, url) for score, url in scored if score >= 0), None)
        if best:
            concert["ticketSwapUrl"] = best[1]
            found += 1
            print("TicketSwap gevonden:", concert.get("artist"), "->", best[1])

        # Keep the public search endpoint load modest.
        time.sleep(0.4)

    print("TicketSwap gecontroleerd:", checked)
    print("Nieuwe exacte TicketSwap-links:", found)
    return concerts
