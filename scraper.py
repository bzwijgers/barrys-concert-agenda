from urllib.request import Request, urlopen
from urllib.parse import urljoin, urlparse
from datetime import datetime
import html as html_module
import re

URL = "https://www.effenaar.nl/agenda"
BASE_URL = "https://www.effenaar.nl"

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/154.0 Safari/537.36"
    ),
    "Accept-Language": "nl-NL,nl;q=0.9,en;q=0.8",
}

print("Barry's Concert Agenda - Effenaar structuurtest")
print("Start:", datetime.now().isoformat(timespec="seconds"))

request = Request(URL, headers=headers)

with urlopen(request, timeout=30) as response:
    raw = response.read()
    page = raw.decode("utf-8", errors="replace")
    status = response.status

print("HTTP status:", status)
print("HTML grootte:", len(page))

# ---------------------------------------------------------
# 1. Officieel aantal resultaten op de agenda
# ---------------------------------------------------------

result_match = re.search(
    r"Toon\s+resultaten\s*\(\s*(\d+)\s*\)",
    page,
    flags=re.IGNORECASE,
)

if result_match:
    expected_count = int(result_match.group(1))
else:
    expected_count = None

print("Effenaar resultaat-aantal:", expected_count)

# ---------------------------------------------------------
# 2. Alle href-attributen uit de HTML halen
# ---------------------------------------------------------

href_matches = re.findall(
    r"""href\s*=\s*["']([^"']+)["']""",
    page,
    flags=re.IGNORECASE,
)

print("Alle href-attributen:", len(href_matches))

# ---------------------------------------------------------
# 3. Alleen mogelijke Effenaar event-URL's bewaren
# ---------------------------------------------------------

event_urls = []

for href in href_matches:
    href = html_module.unescape(href).strip()

    absolute_url = urljoin(BASE_URL, href)

    parsed = urlparse(absolute_url)

    if parsed.netloc.lower() not in {
        "effenaar.nl",
        "www.effenaar.nl",
    }:
        continue

    path = parsed.path.rstrip("/")

    # Alleen detailpagina's onder /agenda/...
    # De hoofdpagina /agenda zelf valt dus af.
    if not path.lower().startswith("/agenda/"):
        continue

    # Geen archief/filter/etc.
    if path.lower().startswith("/agenda/archief"):
        continue

    clean_url = (
        f"https://www.effenaar.nl{path}"
    )

    if clean_url not in event_urls:
        event_urls.append(clean_url)

print("Unieke /agenda/... URLs:", len(event_urls))

# ---------------------------------------------------------
# 4. Bekende voorbeelden controleren
# ---------------------------------------------------------

devil_urls = [
    url for url in event_urls
    if "devil" in url.lower()
]

skating_urls = [
    url for url in event_urls
    if "skating" in url.lower()
]

print(
    "Devil Wears Prada URL gevonden:",
    len(devil_urls) > 0
)

print(
    "Skating Polly URL gevonden:",
    len(skating_urls) > 0
)

# ---------------------------------------------------------
# 5. Statusmarkeringen tellen
# ---------------------------------------------------------

cancelled_words = [
    "afgelast",
    "geannuleerd",
    "cancelled",
    "canceled",
]

for word in cancelled_words:
    count = page.lower().count(word.lower())
    print(f"Tekst '{word}': {count} keer")

# ---------------------------------------------------------
# 6. Eerste 20 unieke event-URL's tonen
# ---------------------------------------------------------

print()
print("EERSTE 20 EVENT-URLS")
print("--------------------")

for number, event_url in enumerate(
    event_urls[:20],
    start=1,
):
    print(f"{number:03d}: {event_url}")

# ---------------------------------------------------------
# 7. URLs rond bekende artiesten tonen
# ---------------------------------------------------------

print()
print("BEKENDE TEST-URLS")
print("-----------------")

for event_url in devil_urls:
    print("DEVIL:", event_url)

for event_url in skating_urls:
    print("SKATING:", event_url)

# ---------------------------------------------------------
# 8. Controle
# ---------------------------------------------------------

print()
print("CONTROLE")
print("--------")

if expected_count is not None:
    difference = expected_count - len(event_urls)

    print("Agenda meldt:", expected_count)
    print("Unieke event-URLs:", len(event_urls))
    print("Verschil:", difference)

    if difference == 0:
        print("RESULTAAT: EXACTE MATCH")
    else:
        print("RESULTAAT: NOG GEEN EXACTE MATCH")
else:
    print("RESULTAAT: agenda-aantal niet gevonden")

print()
print("Effenaar structuurtest gereed.")
