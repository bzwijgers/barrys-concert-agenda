from urllib.request import Request, urlopen
from datetime import datetime
import re
import html as html_module

URL = "https://www.effenaar.nl/agenda"

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/154.0 Safari/537.36"
    ),
    "Accept-Language": "nl-NL,nl;q=0.9,en;q=0.8",
}

print("Barry's Concert Agenda - Effenaar kaarttest")
print("Start:", datetime.now().isoformat(timespec="seconds"))

request = Request(URL, headers=headers)

with urlopen(request, timeout=30) as response:
    page = response.read().decode("utf-8", errors="replace")

print("HTTP status: 200")
print("HTML grootte:", len(page))

# Een paar verschillende evenementen om de structuur te onderzoeken.
test_events = [
    ("SKATING POLLY", "/agenda/skatingpolly-1okt"),
    ("BLANKS", "/agenda/blanks-nieuwe-datum"),
    ("DEVIL WEARS PRADA", "/agenda/devil-wears-prada"),
    ("ALPHA WOLF", "/agenda/alpha-wolf"),
]

def clean_fragment(fragment):
    # HTML entities leesbaar maken.
    fragment = html_module.unescape(fragment)

    # Grote hoeveelheden witruimte verkleinen.
    fragment = re.sub(r"\s+", " ", fragment)

    return fragment.strip()

print()
print("============================================================")
print("HTML RONDOM BEKENDE EVENTLINKS")
print("============================================================")

for label, event_path in test_events:

    position = page.lower().find(event_path.lower())

    print()
    print("------------------------------------------------------------")
    print(label)
    print("URL:", event_path)
    print("Positie:", position)
    print("------------------------------------------------------------")

    if position == -1:
        print("EVENTLINK NIET GEVONDEN")
        continue

    # Ruim stuk vóór en na de URL.
    start = max(0, position - 2500)
    end = min(len(page), position + 2500)

    fragment = page[start:end]
    fragment = clean_fragment(fragment)

    print(fragment)

print()
print("============================================================")
print("SNELLE CONTROLE OP VELDNAMEN")
print("============================================================")

search_terms = [
    "date",
    "startDate",
    "start_date",
    "location",
    "venue",
    "eventStatus",
    "cancelled",
    "geannuleerd",
    "afgelast",
]

for term in search_terms:
    count = page.lower().count(term.lower())
    print(f"{term}: {count}")

print()
print("Effenaar kaarttest gereed.")
