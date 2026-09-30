from urllib.request import Request, urlopen
from datetime import datetime
import re
import html as html_module
import json
import time

URL = "https://www.effenaar.nl/agenda"
BASE_URL = "https://www.effenaar.nl"

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/154.0 Safari/537.36"
    ),
    "Accept-Language": "nl-NL,nl;q=0.9,en;q=0.8",
}

MONTHS = {
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


def clean_text(value):
    value = re.sub(r"<[^>]+>", " ", value)
    value = html_module.unescape(value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def extract_text(card, class_name):
    pattern = (
        r'<[^>]*class="[^"]*\b'
        + re.escape(class_name)
        + r'\b[^"]*"[^>]*>(.*?)</[^>]+>'
    )

    match = re.search(
        pattern,
        card,
        flags=re.IGNORECASE | re.DOTALL,
    )

    if not match:
        return ""

    return clean_text(match.group(1))


def extract_location(card):
    match = re.search(
        r'<div\s+class="card-info-location"[^>]*>(.*?)'
        r'</div>\s*</div>\s*</div>',
        card,
        flags=re.IGNORECASE | re.DOTALL,
    )

    if not match:
        return ""

    return clean_text(match.group(1))


def parse_date(value):
    parts = value.lower().strip().split()

    if len(parts) < 4:
        return None

    try:
        day = int(parts[1])
        month = MONTHS.get(parts[2])
        year = int(parts[3])

        if month is None:
            return None

        return f"{year:04d}-{month:02d}-{day:02d}"

    except (ValueError, IndexError):
        return None


def download_page(url):
    request = Request(url, headers=headers)

    with urlopen(request, timeout=30) as response:
        return response.read().decode(
            "utf-8",
            errors="replace",
        )


def extract_start_time(page):
    # Eerst zoeken naar JSON/structured data met startDate.
    start_date_matches = re.findall(
        r'"startDate"\s*:\s*"([^"]+)"',
        page,
        flags=re.IGNORECASE,
    )

    for value in start_date_matches:
        match = re.search(
            r'T(\d{2}):(\d{2})',
            value,
        )

        if match:
            return f"{match.group(1)}:{match.group(2)}"

    # Daarna zoeken naar zichtbare tijdsaanduidingen.
    text = clean_text(page)

    patterns = [
        r'(?:aanvang|start)\s*:?\s*(\d{1,2})[.:](\d{2})',
        r'(\d{1,2})[.:](\d{2})\s*(?:uur)',
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )

        if match:
            hour = int(match.group(1))
            minute = int(match.group(2))

            if 0 <= hour <= 23 and 0 <= minute <= 59:
                return f"{hour:02d}:{minute:02d}"

    return ""


print("Barry's Concert Agenda - Effenaar scraper")
print("Start:", datetime.now().isoformat(timespec="seconds"))

page = download_page(URL)

print("HTTP status: 200")
print("HTML grootte:", len(page))

card_pattern = re.compile(
    r'<a\s+class="agenda-card"\s+href="(/agenda/[^"]+)"',
    flags=re.IGNORECASE,
)

matches = list(card_pattern.finditer(page))

print("Agenda-kaarten gevonden:", len(matches))

concerts = []

skipped_cancelled = 0
skipped_no_title = 0
skipped_no_date = 0
skipped_bad_date = 0

times_found = 0
times_missing = 0
detail_errors = 0

for index, match in enumerate(matches):

    start = match.start()

    if index < len(matches) - 1:
        end = matches[index + 1].start()
    else:
        end = len(page)

    card = page[start:end]

    relative_url = match.group(1)
    detail_url = BASE_URL + relative_url

    title = extract_text(card, "card-title")
    date_text = extract_text(card, "card-info-date")
    location = extract_location(card)
    status = extract_text(card, "card-status").lower()

    if not title:
        skipped_no_title += 1
        continue

    if not date_text:
        skipped_no_date += 1
        continue

    if (
        "afgelast" in status
        or "geannuleerd" in status
        or "cancelled" in status
        or "canceled" in status
    ):
        skipped_cancelled += 1
        continue

    iso_date = parse_date(date_text)

    if not iso_date:
        skipped_bad_date += 1
        continue

    start_time = ""

    try:
        detail_page = download_page(detail_url)
        start_time = extract_start_time(detail_page)

        if start_time:
            times_found += 1
        else:
            times_missing += 1

    except Exception as error:
        detail_errors += 1
        print(
            "Detailpagina fout:",
            title,
            "-",
            str(error),
        )

    concerts.append(
        {
            "artist": title,
            "venue": location if location else "Effenaar",
            "city": "Eindhoven",
            "country": "NL",
            "date": iso_date,
            "time": start_time,
            "source": "Effenaar",
            "url": detail_url,
        }
    )

    # Kleine pauze zodat we Effenaar niet onnodig hard belasten.
    time.sleep(0.10)


unique_concerts = {}

for concert in concerts:
    key = concert["url"].rstrip("/").lower()
    unique_concerts[key] = concert

concerts = list(unique_concerts.values())

concerts.sort(
    key=lambda concert: (
        concert["date"],
        concert["artist"].lower(),
    )
)

with open(
    "concerts.json",
    "w",
    encoding="utf-8",
) as file:

    json.dump(
        concerts,
        file,
        ensure_ascii=False,
        indent=2,
    )


print()
print("============================================================")
print("RESULTAAT")
print("============================================================")

print("Agenda-kaarten:", len(matches))
print("Concerten opgeslagen:", len(concerts))
print("Afgelast/geannuleerd overgeslagen:", skipped_cancelled)
print("Zonder titel:", skipped_no_title)
print("Zonder datum:", skipped_no_date)
print("Ongeldige datum:", skipped_bad_date)

print()
print("Tijden gevonden:", times_found)
print("Tijden niet gevonden:", times_missing)
print("Detailpagina fouten:", detail_errors)

print()
print("Bestand gemaakt: concerts.json")
print()
print("Effenaar scraper gereed.")
