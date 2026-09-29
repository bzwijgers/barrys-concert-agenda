from urllib.request import Request, urlopen
from datetime import datetime
import re

URL = "https://www.effenaar.nl/agenda"

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/154.0 Safari/537.36"
    ),
    "Accept-Language": "nl-NL,nl;q=0.9,en;q=0.8",
}

print("Barry's Concert Agenda - Effenaar test")
print("Start:", datetime.now().isoformat(timespec="seconds"))

request = Request(URL, headers=headers)

with urlopen(request, timeout=30) as response:
    html = response.read().decode("utf-8", errors="replace")
    status = response.status

print("HTTP status:", status)
print("HTML grootte:", len(html))

match = re.search(
    r"Toon resultaten\s*\((\d+)\)",
    html,
    flags=re.IGNORECASE
)

if match:
    print("Effenaar resultaat-aantal:", match.group(1))
else:
    print("Effenaar resultaat-aantal: NIET GEVONDEN")

print(
    "The Devil Wears Prada gevonden:",
    "The Devil Wears Prada" in html
)

print(
    "Skating Polly gevonden:",
    "Skating Polly" in html
)

print(
    "Afgelast-markering gevonden:",
    "afgelast" in html.lower()
)

print("Effenaar test gereed.")
