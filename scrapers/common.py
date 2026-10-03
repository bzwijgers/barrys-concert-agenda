from urllib.request import Request, urlopen
from urllib.parse import urlsplit, urlunsplit, quote
from urllib.error import HTTPError, URLError
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor, as_completed
import re
import html as html_module
import json
import time


# ============================================================
# ALGEMEEN
# ============================================================

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/154.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,*/*;q=0.8"
    ),
    "Accept-Language": "nl-NL,nl;q=0.9,en;q=0.8",
    "Cache-Control": "no-cache",
}

MONTHS_SHORT = {
    "jan": 1,
    "feb": 2,
    "mrt": 3,
    "maa": 3,
    "apr": 4,
    "mei": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "okt": 10,
    "nov": 11,
    "dec": 12,
}

MONTHS_LONG = {
    "januari": 1,
    "februari": 2,
    "maart": 3,
    "april": 4,
    "mei": 5,
    "juni": 6,
    "juli": 7,
    "augustus": 8,
    "september": 9,
    "oktober": 10,
    "november": 11,
    "december": 12,
}


def encode_url(url):
    parts = urlsplit(url)

    encoded_path = quote(
        parts.path,
        safe="/%:@"
    )

    encoded_query = quote(
        parts.query,
        safe="=&%:@/?"
    )

    return urlunsplit(
        (
            parts.scheme,
            parts.netloc,
            encoded_path,
            encoded_query,
            parts.fragment,
        )
    )


def download_page(url):
    safe_url = encode_url(url)

    request = Request(
        safe_url,
        headers=HEADERS
    )

    with urlopen(
        request,
        timeout=30
    ) as response:
        return response.read().decode(
            "utf-8",
            errors="replace"
        )


def download_page_retry(
    url,
    attempts=3
):
    last_error = None

    for attempt in range(attempts):
        try:
            return download_page(url)

        except Exception as error:
            last_error = error

            if attempt < attempts - 1:
                time.sleep(1)

    raise last_error


def clean_text(value):
    value = re.sub(
        r"<[^>]+>",
        " ",
        value
    )

    value = html_module.unescape(
        value
    )

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value.strip()


def normalize_url(url):
    return (
        url
        .strip()
        .rstrip("/")
        .lower()
    )


def clean_json_text(text):
    return (
        text
        .replace("\\/", "/")
        .replace('\\"', '"')
        .replace("\\u0026", "&")
        .replace("\\u0027", "'")
        .replace("\\u2018", "‘")
        .replace("\\u2019", "’")
        .replace("\\u2013", "–")
        .replace("\\u2014", "—")
        .replace("&amp;", "&")
        .strip()
    )


def find_json_value(
    text,
    key
):
    regex = re.compile(
        r'"'
        + re.escape(key)
        + r'"\s*:\s*"((?:\\.|[^"\\])*)"',
        flags=re.IGNORECASE,
    )

    match = regex.search(text)

    if not match:
        return None

    return match.group(1)


# ============================================================
# GENERIEKE PODIUM-HELPERS
# ============================================================

def find_site_event_urls(page, base_url, path_prefix):
    page = page.replace("\\/", "/").replace("\\u002F", "/").replace("\\u002f", "/")
    pattern = re.compile(r"""href\s*=\s*["']([^"']+)["']""", flags=re.IGNORECASE)
    result = []
    seen = set()

    for match in pattern.finditer(page):
        href = html_module.unescape(match.group(1)).split("#", 1)[0]
        if href.startswith("/"):
            url = base_url.rstrip("/") + href
        elif href.startswith(base_url):
            url = href
        else:
            continue

        clean_url = url.split("?", 1)[0].rstrip("/") + "/"
        if path_prefix not in clean_url:
            continue
        if normalize_url(clean_url) == normalize_url(base_url.rstrip("/") + path_prefix):
            continue

        key = normalize_url(clean_url)
        if key not in seen:
            seen.add(key)
            result.append(clean_url)

    return result



def find_labeled_event_urls(page, base_url, path_prefix, wanted_label, labels):
    page = page.replace("\\/", "/").replace("\\u002F", "/").replace("\\u002f", "/")
    pattern = re.compile(r"""href\s*=\s*["']([^"']+)["']""", flags=re.IGNORECASE)
    result = []
    seen = set()
    labels_lower = [label.lower() for label in labels]

    for match in pattern.finditer(page):
        href = html_module.unescape(match.group(1)).split("#", 1)[0]
        if href.startswith("/"):
            url = base_url.rstrip("/") + href
        elif href.startswith(base_url):
            url = href
        else:
            continue
        clean_url = url.split("?", 1)[0].rstrip("/") + "/"
        if path_prefix not in clean_url:
            continue
        raw_context = page[max(0, match.start() - 700):min(len(page), match.end() + 700)]
        context = clean_text(raw_context).lower()
        anchor_text = clean_text(page[match.start():match.end()]).lower()
        center = max(0, context.find(anchor_text))
        distances = {}
        for label in labels_lower:
            positions = [m.start() for m in re.finditer(re.escape(label), context)]
            distances[label] = min((abs(pos - center) for pos in positions), default=999999)
        nearest = min(distances, key=distances.get)
        if nearest != wanted_label.lower() or distances[nearest] > 450:
            continue
        key = normalize_url(clean_url)
        if key not in seen:
            seen.add(key)
            result.append(clean_url)
    return result

def _detail_title(page):
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", page, flags=re.IGNORECASE | re.DOTALL)
    if h1:
        return clean_text(h1.group(1))
    title = re.search(r"<title[^>]*>(.*?)</title>", page, flags=re.IGNORECASE | re.DOTALL)
    return clean_text(title.group(1)).split("|", 1)[0].strip() if title else ""


def _detail_date_time(page):
    matches = re.findall(r'"startDate"\s*:\s*"([^"]+)"', page, flags=re.IGNORECASE)
    for value in matches:
        match = re.search(r"(20\d{2}-\d{2}-\d{2})T(\d{2}):(\d{2})", value)
        if match:
            return match.group(1), match.group(2) + ":" + match.group(3)

    text = clean_text(page)
    months = "|".join(MONTHS_LONG.keys())
    match = re.search(r"(\d{1,2})\s+(" + months + r")\s+(20\d{2})", text, flags=re.IGNORECASE)
    if not match:
        short_months = "|".join(MONTHS_SHORT.keys())
        short_match = re.search(r"(\d{1,2})\s+(" + short_months + r")\s+[\'’]?(\d{2})", text, flags=re.IGNORECASE)
        if not short_match:
            return None, ""
        day = int(short_match.group(1))
        month = MONTHS_SHORT[short_match.group(2).lower()]
        event_date = date(2000 + int(short_match.group(3)), month, day).isoformat()
        after = text[short_match.end():short_match.end() + 500]
        time_match = re.search(r"(?:Start|Aanvang|Deur(?:en)? open)\s*:?\s*(\d{1,2})[:.]([0-5]\d)", after, flags=re.IGNORECASE)
        event_time = f"{int(time_match.group(1)):02d}:{int(time_match.group(2)):02d}" if time_match else ""
        return event_date, event_time

    day = int(match.group(1))
    month = MONTHS_LONG[match.group(2).lower()]
    event_date = date(int(match.group(3)), month, day).isoformat()

    after = text[match.end():match.end() + 500]
    time_match = re.search(r"(?:Start|Aanvang|Deur(?:en)? open)\s*:?\s*(\d{1,2})[:.]([0-5]\d)", after, flags=re.IGNORECASE)
    if not time_match:
        time_match = re.search(r"\b(\d{1,2})[:.]([0-5]\d)\b", after)

    event_time = ""
    if time_match:
        event_time = f"{int(time_match.group(1)):02d}:{int(time_match.group(2)):02d}"

    return event_date, event_time


def scrape_detail_events(urls, venue, city, source, date_from_url=False):
    today = date.today()
    concerts = []

    def fetch(url):
        page = download_page_retry(url)
        artist = _detail_title(page)
        artist = re.sub(r"\s+[\-–—]\s+(?:Poppodium\s+)?(?:Boerderij|PAARD|Melkweg|TivoliVredenburg).*$", "", artist, flags=re.IGNORECASE).strip()
        artist_lower = artist.lower()
        if "afgelast" in artist_lower or "geannuleerd" in artist_lower or "cancelled" in artist_lower or "canceled" in artist_lower:
            return None
        event_date, event_time = _detail_date_time(page)
        if date_from_url:
            url_dates = re.findall(r"(\d{2})-(\d{2})-(20\d{2})", url)
            if url_dates:
                day_value, month_value, year_value = url_dates[-1]
                event_date = f"{year_value}-{month_value}-{day_value}"
                matching_start = re.search(r'"startDate"\s*:\s*"' + re.escape(event_date) + r'T(\d{2}):(\d{2})', page, flags=re.IGNORECASE)
                if matching_start:
                    event_time = matching_start.group(1) + ":" + matching_start.group(2)
        if not artist or not event_date:
            return None
        if date.fromisoformat(event_date) < today:
            return None

        return {
            "artist": artist,
            "venue": venue,
            "city": city,
            "country": "NL",
            "date": event_date,
            "time": event_time,
            "source": source,
            "url": url,
        }

    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(fetch, url): url for url in urls}
        for future in as_completed(futures):
            try:
                concert = future.result()
                if concert:
                    concerts.append(concert)
            except Exception as error:
                print(source, "detailpagina fout:", futures[future], "-", str(error))

    unique = {normalize_url(item["url"]): item for item in concerts}
    result = list(unique.values())
    result.sort(key=lambda item: (item["date"], item["time"], item["artist"].lower()))
    return result


def scrape_boerderij():
    base = "https://" + "poppodiumboerderij" + ".nl"
    page = download_page_retry(base + "/search/events/still/")
    urls = find_site_event_urls(page, base, "/programma/")
    print("Boerderij links gevonden:", len(urls))
    return scrape_detail_events(urls, "Boerderij", "Zoetermeer", "Boerderij")


def scrape_paard():
    base = "https://www." + "paard" + ".nl"
    page = download_page_retry(base + "/event/")
    urls = find_site_event_urls(page, base, "/event/")
    urls = [url for url in urls if normalize_url(url) not in {normalize_url(base + "/event/"), normalize_url(base + "/en/event/")}]
    print("PAARD links gevonden:", len(urls))
    return scrape_detail_events(urls, "PAARD", "Den Haag", "PAARD")


def scrape_melkweg():
    base = "https://www." + "melkweg" + ".nl"
    page = download_page_retry(base + "/nl/agenda/?profile=Concert")
    urls = find_labeled_event_urls(page, base, "/nl/agenda/", "Concert", ("Concert", "Club", "Film", "Expositie", "Festival"))
    print("Melkweg concertlinks gevonden:", len(urls))
    return scrape_detail_events(urls, "Melkweg", "Amsterdam", "Melkweg", date_from_url=True)


def scrape_tivolivredenburg():
    base = "https://www." + "tivolivredenburg" + ".nl"
    genres = (
        "pop", "rock", "indie", "singer-songwriter", "roots-blues-americana",
        "metal-punk-heavy", "hiphop-rb-1", "classic-pop-60s-90s", "nederlands",
        "global-1-pop-rock", "soul-funk-jazz", "reggae-ska", "electronic-1"
    )
    urls = []
    seen = set()
    for genre in genres:
        page = download_page_retry(base + "/agenda?sf_genre=" + genre)
        for url in find_site_event_urls(page, base, "/agenda/"):
            key = normalize_url(url)
            if key not in seen:
                seen.add(key)
                urls.append(url)
    print("TivoliVredenburg niet-klassieke links gevonden:", len(urls))
    return scrape_detail_events(urls, "TivoliVredenburg", "Utrecht", "TivoliVredenburg")
