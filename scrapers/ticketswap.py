from .common import *
import unicodedata


def _ts_words(value):
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return set(re.findall(r"[a-z0-9]+", value.lower()))


def _ts_link_date(url):
    match = re.search(r"-(20\d{2}-\d{2}-\d{2})-[A-Za-z0-9]+$", url or "")
    return match.group(1) if match else ""


def _ts_candidate_score(concert, url):
    if _ts_link_date(url) != concert.get("date", ""):
        return -1
    slug_words = _ts_words((url or "").rsplit("/", 1)[-1])
    artist_words = {w for w in _ts_words(concert.get("artist", "")) if len(w) >= 2}
    if not artist_words:
        return -1
    hits = len(artist_words & slug_words)
    if hits < max(1, (len(artist_words) + 1) // 2):
        return -1
    score = hits * 10
    score += len(_ts_words(concert.get("venue", "")) & slug_words) * 3
    score += len(_ts_words(concert.get("city", "")) & slug_words) * 3
    return score


def enrich_ticketswap_urls(concerts):
    # TicketSwap geeft GitHub Actions momenteel HTTP 202 challenge-HTML
    # in plaats van eventdata. Laat bestaande/extern ontdekte exacte URLs
    # intact; voeg geen onbetrouwbare homepage- of zoeklinks toe.
    existing = sum(1 for concert in concerts if concert.get("ticketSwapUrl"))
    print()
    print("=" * 60)
    print("TICKETSWAP EXACTE EVENTLINKS")
    print("=" * 60)
    print("Bestaande exacte TicketSwap-links:", existing)
    print("Directe discovery tijdelijk uitgeschakeld wegens TicketSwap HTTP 202 challenge")
    return concerts
