"""Check real missing concerts against official live pages, not only mock fixtures."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from scrapers.common import download_page_retry
from scrapers.new_venues import parse_event

EXPECTED = [
    ("SPOT Groningen", "Groningen", "https://www.spotgroningen.nl/programma/timebox/", "2026-11-27"),
    ("SPOT Groningen", "Groningen", "https://www.spotgroningen.nl/programma/pitou/", "2026-11-20"),
    ("SPOT Groningen", "Groningen", "https://www.spotgroningen.nl/programma/levi-sct/", "2026-11-18"),
    ("SPOT Groningen", "Groningen", "https://www.spotgroningen.nl/programma/pieter-savenberg/", "2026-11-05"),
    ("SPOT Groningen", "Groningen", "https://www.spotgroningen.nl/programma/alexis-ffrench/", "2027-06-06"),
    ("Hedon", "Zwolle", "https://hedon-zwolle.nl/voorstelling/32962/big-sleep", "2026-11-15"),
    ("Metropool", "Hengelo", "https://metropool.nl/agenda/waxing-crescent", "2026-10-09"),
]
def check(case):
    venue, city, url, day = case
    html = download_page_retry(url, attempts=3)
    item = parse_event(html, url, venue, city)
    ok = bool(item and item["date"] == day)
    return ok, venue, url, item, day

if __name__ == "__main__":
    with ThreadPoolExecutor(max_workers=4) as executor:
        outcomes = list(executor.map(check, EXPECTED))
    for ok, venue, url, item, expected in outcomes:
        print("PASS" if ok else "FAIL", venue, url, "expected", expected,
              "actual", item, flush=True)
    if not all(result[0] for result in outcomes):
        raise SystemExit("One or more official live concerts still fail to parse")
    print("COMPLETE",len(outcomes),"known live concerts correctly parsed",flush=True)
