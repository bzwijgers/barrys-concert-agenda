"""Read-only smoke probe for staged official concert sources.

Never publishes concerts.json. A site is eligible for production only after
verified event discovery and a venue-specific completeness threshold.
Usage: python -m audit.probe_staged_sources
"""
from collections import Counter
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
import json

from scrapers.next_sources import CANDIDATES
from scrapers.official_music_events import parse_official_music_events


def probe(candidate, getter=None):
    if getter is None:
        def getter(url):
            req = Request(url, headers={"User-Agent": "BarrysConcertAgenda/1.0",
                                        "Accept": "text/html"})
            with urlopen(req, timeout=18) as response:
                return response.read(3_000_000).decode("utf-8", errors="replace")
    try:
        html = getter(candidate.official_agenda)
        concerts = parse_official_music_events(
            html, candidate.official_agenda,
            candidate.name, candidate.city, candidate.country
        )
    except (URLError, HTTPError, TimeoutError, ValueError, OSError) as error:
        return {"name": candidate.name, "status": "unavailable",
                "count": 0, "reason": type(error).__name__}
    # Walhalla also publishes cabaret, children's performances and theatre.
    # A generic MusicEvent tag does not prove its official category is
    # Theaterconcert. Never stage such events as approved without
    # event-level genre validation from their detail pages.
    if not concerts:
        return {"name": candidate.name, "status": "needs-custom-scraper",
                "count": 0, "reason": "No verified MusicEvent metadata on landing page"}
    if candidate.name == "Theater Walhalla":
        return {"name": candidate.name, "status": "needs-theaterconcert-filter",
                "count": len(concerts),
                "reason": "Official Theaterconcert genre must be verified per performance"}
    unique = {event["url"] for event in concerts}
    if len(unique) != len(concerts):
        return {"name": candidate.name, "status": "needs-review",
                "count": len(concerts), "reason": "Duplicate event URLs"}
    return {"name": candidate.name, "status": "candidate-only",
            "count": len(concerts),
            "reason": "Detail-page coverage and completeness not yet verified"}


def main():
    outcomes = [probe(candidate) for candidate in CANDIDATES]
    print(json.dumps({"summary": dict(Counter(x["status"] for x in outcomes)),
                      "sources": outcomes}, ensure_ascii=False, indent=2))
    # Deliberately no live production changes: this is a diagnostic.


if __name__ == "__main__":
    main()
