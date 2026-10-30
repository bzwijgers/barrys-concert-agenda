"""Audit direct TicketSwap URLs in the *published* concert feed (read-only).

This does not delete a match, edit main, visit ticket pages or infer an event
from a TicketSwap homepage. It reports coverage and unsafe/ambiguous mappings.
The Android app has a separate strict matcher and only displays valid matches.
"""
import json
import re
from collections import Counter
from datetime import date
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlsplit
import unicodedata

PUBLIC = "https://bzwijgers.github.io/barrys-concert-agenda/concerts.json"
DATE = re.compile(r"-(20\d{2}-\d{2}-\d{2})-[a-zA-Z0-9]+$")
STOP = {"the", "a", "and", "of", "in", "live", "tour", "show", "presents"}
HOSTS = {"www.ticketswap.nl", "ticketswap.nl", "www.ticketswap.com", "ticketswap.com"}
ALIASES = {
    "den haag": {"hague", "gravenhage"},
    "'s-gravenhage": {"hague", "gravenhage"},
    "s-gravenhage": {"hague", "gravenhage"},
    "antwerpen": {"antwerp"},
    "brussel": {"brussels"},
    "bruxelles": {"brussels"},
    "gent": {"ghent"},
}


def words(s):
    ascii_text = "".join(ch for ch in unicodedata.normalize("NFD", s or "")
                         if not unicodedata.combining(ch))
    return {w for w in re.findall("[a-z0-9]+", ascii_text.lower())
            if len(w) > 1 and w not in STOP}


def free_entry(concert):
    """Known free-admission event: a TicketSwap URL should not be offered."""
    return (
        concert.get("date") == "2026-12-06"
        and concert.get("artist", "").lower() == "just graduated: marco bernardi en katrina kabineca"
        and concert.get("venue", "").lower() == "amare"
        and concert.get("city", "").lower() == "den haag"
        and concert.get("url", "").rstrip("/")
            == "https://www.podiuminfo.nl/concert/485136/Just-Graduated-Marco-Bernardi-en-Katrina-Kabineca/Amare"
    )


def exception(concert, link):
    source = concert.get("url", "").rstrip("/")
    if (concert.get("artist", "").lower() == "lords of altamont + sick shooters"
            and concert.get("date") == "2026-11-22"
            and concert.get("venue", "").lower() == "db's"
            and concert.get("city", "").lower() == "utrecht"
            and source == "https://dbstudio.nl/event/lords-of-altamont"
            and link == "https://www.ticketswap.nl/concert-tickets/lords-of-altamont-utrecht-dbs-oefenstudios-concertzaal-muziekcafe-2026-11-22-CdENvHWLHRMhVuoMG4LxW"):
        return True
    if (concert.get("artist", "").lower() == "the apers"
            and concert.get("date") == "2026-10-09"
            and concert.get("venue", "").lower() == "rotown"
            and source == "https://www.rotown.nl/agenda/the-apers-1"
            and "maladroit-rotterdam-rotown-2026-10-09-" in link):
        return True
    if (concert.get("artist", "").lower() == "30 jaar excelsior recordings"
            and concert.get("date") == "2026-12-27"
            and concert.get("venue", "").lower() == "tolhuistuin"
            and source == "https://www.paradiso.nl/nl/programma/30-jaar-excelsior-recordings/2902321"
            and "30-jaar-excelsior-recordings-amsterdam-tolhuistuin-2026-12-27-" in link):
        return True
    return False


def problem(concert):
    if free_entry(concert):
        return "suppressed-free-admission"
    link = (concert.get("ticketSwapUrl") or "").strip()
    if not link:
        return "missing"
    uri = urlsplit(link)
    if uri.scheme != "https" or (uri.hostname or "").lower() not in HOSTS:
        return "unsafe-host"
    if not uri.path.startswith("/concert-tickets/"):
        return "not-detail-page"
    slug = uri.path.removeprefix("/concert-tickets/")
    if "/" in slug or not DATE.search(slug):
        return "not-dated-detail-link"
    if DATE.search(slug).group(1) != concert.get("date"):
        return "wrong-date"
    if exception(concert, link):
        return "verified-exception"
    match_words = words(slug)
    artist = words(concert.get("artist", ""))
    if not artist:
        return "empty-artist"
    required = len(artist) if len(artist) <= 4 else len(artist) - 1
    if len(artist & match_words) < required:
        return "wrong-artist"
    city = (concert.get("city") or "").lower().strip()
    if not (words(city) & match_words or ALIASES.get(city, set()) & match_words
            or words(concert.get("venue", "")) & match_words):
        return "wrong-place"
    return "matched"


def load_feed():
    try:
        req = Request(PUBLIC, headers={"User-Agent": "BarryConcertAgendaV3LinkAudit/1.0"})
        with urlopen(req, timeout=30) as rsp:
            feed = json.load(rsp)
        if len(feed) < 1000:
            raise RuntimeError("Published feed unexpectedly small")
        return feed, "published URL"
    except Exception as error:
        print("WARNING live feed unavailable:", type(error).__name__, str(error)[:150])
        return json.loads(Path("concerts.json").read_text(encoding="utf-8")), "checked-out feed SNAPSHOT"


def main():
    feed, origin = load_feed()
    future = [c for c in feed if c.get("date", "") >= date.today().isoformat()]
    with_link = [c for c in future if c.get("ticketSwapUrl")]
    by_status = Counter(problem(c) for c in with_link)
    print("FEED ORIGIN:", origin)
    print("TOTAL EVENTS:", len(feed), "FUTURE:", len(future))
    print("FUTURE WITH TICKETSWAP LINK:", len(with_link), "/", len(future))
    print("TICKETSWAP VALIDATION:", dict(by_status))
    mismatches = [(problem(c), c) for c in with_link
                  if problem(c) not in {"matched", "verified-exception", "suppressed-free-admission"}]
    print("QUESTIONABLE EXAMPLES:")
    for kind, c in mismatches[:35]:
        print(kind, "|", c.get("artist"), "|", c.get("date"), "|", c.get("venue"),
              "|", c.get("ticketSwapUrl", "")[:200])
    # This is a report: existing main feed is shared by V1/V2/V3 and must not
    # be edited or failed automatically based on only a URL-slug heuristic.
    if not future:
        raise SystemExit("ERROR: No upcoming concerts to audit")


if __name__ == "__main__":
    main()
