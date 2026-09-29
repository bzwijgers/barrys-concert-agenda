from urllib.request import Request, urlopen
from datetime import datetime
import re
import html as html_module
import json

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
    # Voorbeeld:
    # za 10 okt 2026

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


print("Barry's Concert Agenda - Effenaar scraper")
print("Start:", datetime.now().isoformat(timespec="seconds"))

request = Request(URL, headers=headers)

with urlopen(request, timeout=30) as response:
    page = response.read().decode(
        "utf-8",
        errors="replace",
    )

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

for index, match in enumerate(matches):

    start = match.start()

    if index < len(matches) - 1:
        end = matches[index + 1].start()
    else:
        end = len(page)

    card = page[start:end]

    relative_url = match.group(1)

    title = extract_text(
        card,
        "card-title",
    )

    date_text = extract_text(
        card,
        "card-info-date",
    )

    location = extract_location(card)

    status = extract_text(
        card,
        "card-status",
    ).lower()

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

    concerts.append(
        {
            "artist": title,
            "venue": location if location else "Effenaar",
            "city": "Eindhoven",
            "country": "NL",
            "date": iso_date,
            "time": "",
            "source": "Effenaar",
            "url": BASE_URL + relative_url,
        }
    )


# Dubbele URL's verwijderen
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
print("Bestand gemaakt: concerts.json")
print()
print("Effenaar scraper gereed.")
