from .common import *
from urllib.parse import urljoin, quote_plus, quote
import unicodedata


TICKETSWAP_BASE = "https://www.ticketswap.com"


def _ts_slug(value):
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.lower().replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def _ts_words(value):
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return set(re.findall(r"[a-z0-9]+", value.lower()))


def _ts_event_links(page):
    cleaned = page.replace("\\/", "/").replace("\\u002F", "/")
    # TicketSwap rendert eventlinks deels in HTML en deels in ingebedde JSON.
    # Zoek daarom niet alleen href-attributen, maar alle herkenbare eventpaden.
    pattern = re.compile(
        r'''(?:https://www\.ticketswap\.(?:com|nl))?(/(?:concert-tickets|event)/[a-z0-9][^"'<>\\\s?]*)''',
        re.I,
    )
    links = []
    seen = set()
    for match in pattern.finditer(cleaned):
        href = html_module.unescape(match.group(1))
        url = urljoin(TICKETSWAP_BASE, href).split("?", 1)[0].rstrip("/")
        if url not in seen:
            seen.add(url)
            links.append(url)
    return links


def _ts_link_date(url):
    match = re.search(r"-(20\d{2}-\d{2}-\d{2})-[A-Za-z0-9]+$", url)
    return match.group(1) if match else ""


def _ts_month_name(date_value):
    names = {
        1: "january", 2: "february", 3: "march", 4: "april",
        5: "may", 6: "june", 7: "july", 8: "august",
        9: "september", 10: "october", 11: "november", 12: "december",
    }
    if not re.match(r"^20\d{2}-\d{2}-\d{2}$", date_value or ""):
        return ""
    return names.get(int(date_value[5:7]), "")


def _ts_search_event_links(concert):
    """Fallback via Bing: TicketSwap event pages are indexed even when city pages are JS-rendered."""
    artist = concert.get("artist", "").strip()
    venue = concert.get("venue", "").strip()
    city = concert.get("city", "").strip()
    date = concert.get("date", "").strip()
    if not artist or not date:
        return []

    # Gebruik de Nederlandse TicketSwap-index; die wordt aantoonbaar
    # geindexeerd met exacte eventpagina's. Zoek zonder ISO-datum tussen
    # quotes, omdat de zichtbare zoekresultaten de datum lokaal formatteren.
    query = f'site:ticketswap.nl/concert-tickets "{artist}" "{venue}" "{city}"'
    search_url = "https://www.google.com/search?q=" + quote_plus(query)
    try:
        page = download_page_retry(search_url, attempts=2)
    except Exception:
        return []

    cleaned = html_module.unescape(page).replace("\\/", "/")
    pattern = re.compile(
        r'https?://www\.ticketswap\.(?:nl|com)/concert-tickets/[a-z0-9][^"&<>\\\s?]*',
        re.I,
    )
    return list(dict.fromkeys(match.group(0).rstrip("/") for match in pattern.finditer(cleaned)))



def _ts_google_cache_query(concert):
    """Vind exacte TicketSwap-eventpagina's via de publieke zoekindex."""
    artist = concert.get("artist", "").strip()
    venue = concert.get("venue", "").strip()
    city = concert.get("city", "").strip()
    if not artist:
        return []
    # Minder strikt dan voorheen: zoekindexen matchen venue/city soms niet in
    # de snippet, terwijl die wel in de uiteindelijke TicketSwap-URL staan.
    query = f'site:ticketswap.nl/concert-tickets "{artist}"'
    try:
        page = download_page_retry("https://www.google.com/search?q=" + quote_plus(query), attempts=1)
    except Exception:
        return []
    cleaned = html_module.unescape(page).replace("\\/", "/")
    return list(dict.fromkeys(re.findall(
        r'https?://www\\.ticketswap\\.(?:nl|com)/concert-tickets/[a-z0-9][^"&<>\\\\\\s?]*',
        cleaned, re.I
    )))

def _ts_candidate_score(concert, url):
    if _ts_link_date(url) != concert.get("date", ""):
        return -1

    slug = url.rsplit("/", 1)[-1].lower()
    candidate_words = _ts_words(slug)
    artist_words = _ts_words(concert.get("artist", ""))
    venue_words = _ts_words(concert.get("venue", ""))
    city_words = _ts_words(concert.get("city", ""))

    useful_artist = {w for w in artist_words if len(w) >= 2}
    if not useful_artist:
        return -1

    artist_hits = len(useful_artist & candidate_words)
    # Minimaal de helft van de betekenisvolle artiestwoorden moet kloppen.
    if artist_hits < max(1, (len(useful_artist) + 1) // 2):
        return -1

    score = artist_hits * 10
    score += len(venue_words & candidate_words) * 3
    score += len(city_words & candidate_words) * 3
    return score


def enrich_ticketswap_urls(concerts):
    print()
    print("=" * 60)
    print("TICKETSWAP EXACTE EVENTLINKS")
    print("=" * 60)

    # Eerst een kleine, snelle zoekindex-test op nabije toekomstige concerten.
    # Hiermee valideren we de discovery-route zonder 1.300 requests.
    from datetime import date, timedelta
    today = date.today()
    horizon = today + timedelta(days=14)
    targets = []
    for concert in concerts:
        try:
            d = date.fromisoformat(concert.get("date", ""))
        except Exception:
            continue
        if today <= d <= horizon:
            targets.append(concert)

    event_urls = set()
    for concert in targets:
        for url in _ts_google_cache_query(concert):
            event_urls.add(url)

    matched = 0
    for concert in concerts:
        scored = [(_ts_candidate_score(concert, url), url) for url in event_urls]
        scored = [(score, url) for score, url in scored if score >= 0]
        if not scored:
            continue
        scored.sort(reverse=True)
        best_score, best_url = scored[0]
        if len(scored) > 1 and scored[1][0] == best_score:
            continue
        concert["ticketSwapUrl"] = best_url.replace("https://www.ticketswap.com/", "https://www.ticketswap.nl/")
        matched += 1
        print("TicketSwap match:", concert.get("artist"), concert.get("date"), "->", concert["ticketSwapUrl"])

    print("TicketSwap zoekindex-events verzameld:", len(event_urls))
    print("Exact gekoppelde TicketSwap-events:", matched)
    return concerts
