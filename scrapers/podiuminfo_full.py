"""Full future concert schedules for Amare and Het Bolwerk.

Their official sites currently block GitHub runners. Podiuminfo's regular
venue page embeds only 25 event JSON-LD records; its complete concertagenda
page exposes a substantially larger date-labelled list in server HTML.
"""
from datetime import date
from html import unescape
from html.parser import HTMLParser
from urllib.parse import urlsplit
import re

from .common import download_page_retry, normalize_url

MONTHS = {
    "januari":1, "februari":2, "maart":3, "april":4, "mei":5, "juni":6,
    "juli":7, "augustus":8, "september":9, "oktober":10,
    "november":11, "december":12,
}
WEEKDAYS = "maandag|dinsdag|woensdag|donderdag|vrijdag|zaterdag|zondag"

SOURCES = {
    "Amare": (
        "https://www.podiuminfo.nl/concertagenda/podium/amare/",
        "Amare", "Den Haag",
    ),
    "Bolwerk": (
        "https://www.podiuminfo.nl/concertagenda/podium/het-bolwerk/",
        "Het Bolwerk", "Sneek",
    ),
}

class ConcertAnchors(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self,tag,attrs):
        if tag != "a":
            return
        d = dict(attrs)
        if "/concert/" in d.get("href", "") and d.get("aria-label"):
            self.links.append(d)


def parse_full_podiuminfo_anchor(anchor, venue, source, city, today=None):
    href = str(anchor.get("href", "")).split("?", 1)[0].rstrip("/")
    if not href.startswith("https://www.podiuminfo.nl/concert/"):
        return None
    path = urlsplit(href).path.rstrip("/").split("/")
    if len(path) < 5 or path[-1].casefold() != venue.casefold().replace(" ", "-"):
        return None

    label = unescape(str(anchor.get("aria-label", "")))
    pattern = (
        rf",\s*(?:{WEEKDAYS})\s+(\d{{1,2}})\s+"
        rf"({'|'.join(MONTHS)})\s+(20\d{{2}})\s+om\s+"
        rf"([01]?\d|2[0-3]):([0-5]\d)"
    )
    found = re.search(pattern, label, flags=re.I)
    if not found:
        return None

    artist = label[:found.start()].strip()
    if artist.casefold().startswith("concert "):
        artist = artist[8:].strip()
    if not artist:
        return None
    try:
        day = date(
            int(found.group(3)),
            MONTHS[found.group(2).lower()],
            int(found.group(1)),
        )
    except (ValueError,KeyError):
        return None
    if day < (today or date.today()):
        return None

    # Keep only music performances, not a ballroom/dance/social calendar.
    unwanted = (
        r"social dance|workshop|masterclass|cabaret|comedy|"
        r"dancehague|danspaleis|meet.?up|lezing|rondleiding|ballet|"
        r"dj.?party|80's.?90's.?00's party|clubnacht"
    )
    if re.search(unwanted,artist,re.I):
        return None

    return {
        "artist": artist,
        "venue": venue,
        "city": city,
        "country": "NL",
        "date": day.isoformat(),
        "time": f"{int(found.group(4)):02d}:{found.group(5)}",
        "source": source,
        "url": href,
    }


def scrape_full_podiuminfo_source(source):
    url, venue, city = SOURCES[source]
    html = download_page_retry(url,attempts=3)
    parser = ConcertAnchors()
    parser.feed(html)
    results = {}
    for anchor in parser.links:
        concert = parse_full_podiuminfo_anchor(anchor,venue,source,city)
        if concert:
            results[normalize_url(concert["url"])] = concert

    concerts = sorted(
        results.values(),
        key=lambda item: (item["date"],item["time"],item["artist"].casefold()),
    )
    print("Full Podiuminfo",source,":",len(concerts),
          "future music events from",len(parser.links),"candidate links",flush=True)
    if len(concerts) < 25:
        raise RuntimeError(
            "Full " + source + " external programme unexpectedly small: "
            + str(len(concerts))
        )
    return concerts
