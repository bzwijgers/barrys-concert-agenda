"""Safely enrich concert feed with public first-party TicketSwap event sitemaps.

No Google/Bing scraping, login, access token, or hidden Android WebView.
Only exact dated links with corroborating artist + city/venue are accepted.
All event sitemaps must download successfully before *any* publication.
"""
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
import json
import re
import sys
import unicodedata
from urllib.request import Request, urlopen
from xml.etree import ElementTree

from scrapers.common import normalize_url

BASE = "https://www.ticketswap.com"
INDEX = BASE + "/sitemap.xml"
CACHE = "/tmp/barrys-public-ticketswap-event-links.json"
DATE_RE = re.compile(r"-(20\d{2}-\d{2}-\d{2})-[a-zA-Z0-9]+$")
STOP = {"and", "the", "het", "een", "en", "van", "de", "der",
        "with", "feat", "featuring", "presents", "tour", "live",
        "show", "in", "at", "on", "plus", "andmore"}
ALIASES = {
    "den haag": {"hague", "haag", "gravenhage"},
    "'s-gravenhage": {"hague", "haag", "gravenhage"},
    "antwerpen": {"antwerp"},
    "brussel": {"brussels"},
    "bruxelles": {"brussels"},
    "gent": {"ghent"},
    "den bosch": {"bosch", "hertogenbosch"},
}


def words(s):
    decomposed = unicodedata.normalize("NFKD", s or "")
    ascii_text = "".join(c for c in decomposed if not unicodedata.combining(c))
    return {part for part in re.findall(r"[a-z0-9]+", ascii_text.lower())
            if len(part) >= 2 and part not in STOP}


def download(url):
    request = Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; ConcertAgenda/1.0)",
        "Accept": "application/xml,text/xml;q=0.9,*/*;q=0.8",
    })
    with urlopen(request, timeout=25) as response:
        if response.status != 200:
            raise RuntimeError(f"HTTP {response.status}: {url}")
        return response.read(8_000_000)


def locations(xml):
    tree = ElementTree.fromstring(xml)
    return [
        element.text.strip()
        for element in tree.iter()
        if element.tag.endswith("}loc") or element.tag == "loc"
        if element.text and element.text.strip()
    ]


def collect():
    index = locations(download(INDEX))
    files = [x for x in index if re.search(r"/sitemap/event_\d+\.xml$", x)]
    if len(files) < 30 or len(files) > 120:
        raise RuntimeError(f"Unexpected TicketSwap sitemap count: {len(files)}")
    print("TICKETSWAP SITEMAP FILES", len(files), flush=True)
    collected = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        tasks = {pool.submit(download, address): address for address in files}
        for task in as_completed(tasks):
            address = tasks[task]
            entries = locations(task.result())  # Error stops all publication.
            if len(entries) < 100:
                raise RuntimeError(f"Unusually small TicketSwap sitemap {address}: {len(entries)}")
            collected.extend(entries)
    unique = sorted({url for url in collected if "/concert-tickets/" in url
                    and DATE_RE.search(url)})
    if len(unique) < 20_000:
        raise RuntimeError(f"Unexpectedly few dated concert links: {len(unique)}")
    with open(CACHE, "w", encoding="utf-8") as file:
        json.dump(unique, file, ensure_ascii=False)
    print("TICKETSWAP VALID DATED CONCERT LINKS", len(unique), flush=True)


def score(concert, candidate):
    last = candidate.rstrip("/").split("/")[-1]
    match = DATE_RE.search(last)
    if not match or match.group(1) != concert.get("date"):
        return -1
    candidate_words = words(last)
    artist_words = words(concert.get("artist", ""))
    if not artist_words:
        return -1
    artist_matches = len(artist_words & candidate_words)
    required = len(artist_words) if len(artist_words) <= 5 else len(artist_words) - 1
    if artist_matches < required:
        return -1
    city_words = words(concert.get("city", ""))
    city_words |= ALIASES.get(concert.get("city", "").strip().lower(), set())
    venue_words = words(concert.get("venue", ""))
    city_matches = len(city_words & candidate_words)
    venue_matches = len(venue_words & candidate_words)
    # A short one-word artist is not enough without venue confirmation.
    if len(artist_words) == 1 and venue_matches == 0:
        return -1
    if city_matches == 0 and venue_matches == 0:
        return -1
    return 20 * artist_matches + 8 * venue_matches + 5 * city_matches


def assign(feed, urls):
    index = defaultdict(list)
    for link in urls:
        match = DATE_RE.search(link.rstrip("/").split("/")[-1])
        if match:
            index[match.group(1)].append(link)
    added = 0
    ambiguous = 0
    for concert in feed:
        if concert.get("ticketSwapUrl"):
            continue
        day = concert.get("date", "")
        if day < date.today().isoformat():
            continue
        options = sorted(
            ((score(concert, link), link) for link in index.get(day, ())),
            reverse=True,
        )
        passing = [(rating, link) for rating, link in options if rating >= 0]
        if not passing:
            continue
        if len(passing) > 1 and passing[0][0] == passing[1][0]:
            ambiguous += 1
            continue  # Never guess between two equally plausible events.
        concert["ticketSwapUrl"] = passing[0][1].replace(
            "https://www.ticketswap.com/", "https://www.ticketswap.nl/"
        )
        added += 1
    print("TICKETSWAP NEW EXACT MATCHES", added,
          "AMBIGUOUS SKIPPED", ambiguous, flush=True)
    return added


def apply():
    with open(CACHE, encoding="utf-8") as file:
        links = json.load(file)
    with open("concerts.json", encoding="utf-8") as file:
        feed = json.load(file)
    if len(feed) < 3000 or len(links) < 20_000:
        raise RuntimeError("Insufficient feed or indexed links")
    previous = sum(bool(e.get("ticketSwapUrl")) for e in feed)
    new = assign(feed, links)
    total = sum(bool(e.get("ticketSwapUrl")) for e in feed)
    if total != previous + new:
        raise RuntimeError("Unexpected TicketSwap link loss during enrichment")
    if new < 10 and previous < 10:
        raise RuntimeError("Fewer than ten exact matches; withholding publication")
    with open("concerts.json", "w", encoding="utf-8") as file:
        json.dump(feed, file, ensure_ascii=False, indent=2)
        file.write("\n")
    print("FEED PUBLISH READY", len(feed), "old links", previous,
          "added", new, "total exact links", total, flush=True)
    for example in [e for e in feed if e.get("ticketSwapUrl")][:8]:
        print("EXACT SAMPLE", example["artist"], example["date"],
              example["city"], "->", example["ticketSwapUrl"], flush=True)


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "collect":
        collect()
    elif len(sys.argv) == 2 and sys.argv[1] == "apply":
        apply()
    else:
        raise SystemExit("Use collect or apply")
