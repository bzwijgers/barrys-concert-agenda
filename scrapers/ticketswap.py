from .common import *
from urllib.parse import urljoin, quote_plus
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

    # Verzamel TicketSwap-events per stad/maand. Dit is tientallen requests
    # in plaats van een zoekmachine-request voor ieder concert.
    pages = {}
    event_urls = set()
    for concert in concerts:
        city = concert.get("city", "").strip()
        date = concert.get("date", "").strip()
        if not city or not re.match(r"^20\d{2}-\d{2}-\d{2}$", date):
            continue
        key = (_ts_slug(city), date[:7])
        pages[key] = (city, date)

    for (city_slug, year_month), (city, date) in sorted(pages.items()):
        month = _ts_month_name(date)
        # TicketSwap gebruikt momenteel /next-month voor de eerstvolgende
        # kalendermaand en genre/maandpagina's als extra bron.
        candidates = [
            f"https://www.ticketswap.nl/concert-tickets/l/netherlands/{city_slug}/next-month",
            f"https://www.ticketswap.nl/concert-tickets/l/netherlands/{city_slug}",
        ]
        if month:
            candidates.extend([
                f"https://www.ticketswap.nl/concert-tickets/g/rock/{month}",
                f"https://www.ticketswap.nl/concert-tickets/g/pop/{month}",
                f"https://www.ticketswap.nl/concert-tickets/g/indie/{month}",
                f"https://www.ticketswap.nl/concert-tickets/g/metal/{month}",
                f"https://www.ticketswap.nl/concert-tickets/g/folk/{month}",
            ])

        for page_url in candidates:
            if page_url in event_urls:
                continue
            try:
                page = download_page_retry(page_url, attempts=2)
            except Exception:
                continue
            for url in _ts_event_links(page):
                event_urls.add(url)

    matched = 0
    for concert in concerts:
        if concert.get("ticketSwapUrl"):
            matched += 1
            continue
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

    print("TicketSwap eventlinks verzameld:", len(event_urls))
    print("Exact gekoppelde TicketSwap-events:", matched)
    return concerts
