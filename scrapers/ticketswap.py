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


def _ts_search_event_links(concert):
    """Fallback via Bing: TicketSwap event pages are indexed even when city pages are JS-rendered."""
    artist = concert.get("artist", "").strip()
    venue = concert.get("venue", "").strip()
    city = concert.get("city", "").strip()
    date = concert.get("date", "").strip()
    if not artist or not date:
        return []

    query = f'site:ticketswap.com/concert-tickets "{artist}" "{venue}" "{city}" "{date}"'
    search_url = "https://www.bing.com/search?q=" + quote_plus(query)
    try:
        page = download_page_retry(search_url, attempts=2)
    except Exception:
        return []

    cleaned = html_module.unescape(page).replace("\\/", "/")
    pattern = re.compile(
        r'https?://www\.ticketswap\.com/concert-tickets/[a-z0-9][^"&<>\\\s?]*',
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

    by_city = {}
    for concert in concerts:
        city = concert.get("city", "").strip()
        if city and concert.get("date"):
            by_city.setdefault(city, []).append(concert)

    matched = 0
    for city, city_concerts in sorted(by_city.items()):
        city_slug = _ts_slug(city)
        if not city_slug:
            continue

        urls = []
        month_names = {
            1: "january", 2: "february", 3: "march", 4: "april",
            5: "may", 6: "june", 7: "july", 8: "august",
            9: "september", 10: "october", 11: "november", 12: "december",
        }
        months = sorted({
            month_names[int(concert["date"][5:7])]
            for concert in city_concerts
            if re.match(r"^20\d{2}-\d{2}-\d{2}$", concert.get("date", ""))
        })
        page_urls = [
            f"{TICKETSWAP_BASE}/concert-tickets/l/netherlands/{city_slug}"
        ]
        page_urls.extend(
            f"{TICKETSWAP_BASE}/concert-tickets/l/netherlands/{city_slug}/{month}"
            for month in months
        )
        page_urls.append(f"{TICKETSWAP_BASE}/city/{city_slug}")

        for page_url in page_urls:
            try:
                page = download_page_retry(page_url, attempts=2)
                urls.extend(_ts_event_links(page))
            except Exception:
                pass

        urls = list(dict.fromkeys(urls))
        if not urls:
            continue

        for concert in city_concerts:
            scored = [
                (_ts_candidate_score(concert, url), url)
                for url in urls
            ]
            scored = [(score, url) for score, url in scored if score >= 0]
            if not scored:
                # TicketSwap city pages zijn deels client-side gerenderd. Gebruik
                # alleen voor nog niet gevonden concerten een gerichte web-index fallback.
                search_urls = _ts_search_event_links(concert)
                scored = [
                    (_ts_candidate_score(concert, url), url)
                    for url in search_urls
                ]
                scored = [(score, url) for score, url in scored if score >= 0]
            if not scored:
                continue

            scored.sort(reverse=True)
            best_score, best_url = scored[0]
            # Geen koppeling bij een gelijke beste score: dan is de match ambigu.
            if len(scored) > 1 and scored[1][0] == best_score:
                continue

            concert["ticketSwapUrl"] = best_url
            matched += 1

    print("Exact gekoppelde TicketSwap-events:", matched)
    return concerts
