"""Incremental publication of two independently verified official venue feeds.

The full nightly scraper can take many minutes and may fail on unrelated venues.
This safe updater keeps all other concerts untouched. It refuses truncated
source feeds and never guesses or drops TicketSwap links.
"""
import json
import os
from collections import Counter
from datetime import date
from pathlib import Path

from scrapers.common import normalize_url
from scrapers.new_venues import scrape_venue
from scrapers.ticketswap import VERIFIED_EVENTS

FEED = Path("concerts.json")
SOURCES = {"Bibelot": 30, "De Pul": 25}
CACHE = Path("/tmp/barrys-verified-bibelot-depul.json")


def validate(rows, venue, minimum):
    unique = {normalize_url(r.get("url", "")) for r in rows}
    if len(rows) < minimum or len(unique) != len(rows):
        raise RuntimeError(f"{venue}: incomplete/duplicate feed: {len(rows)} rows, {len(unique)} unique URLs")
    for item in rows:
        if item.get("source") != venue or item.get("date", "") < date.today().isoformat():
            raise RuntimeError(f"{venue}: invalid source/date {item!r}")


def collect():
    combined = []
    for name, minimum in SOURCES.items():
        rows = scrape_venue(name)
        validate(rows, name, minimum)
        print("VERIFIED VENUE", name, "future concerts", len(rows), flush=True)
        combined.extend(rows)
    CACHE.write_text(json.dumps(combined, ensure_ascii=False), encoding="utf-8")


def apply():
    fresh = json.loads(CACHE.read_text(encoding="utf-8"))
    for name, minimum in SOURCES.items():
        validate([r for r in fresh if r.get("source") == name], name, minimum)

    previous = json.loads(FEED.read_text(encoding="utf-8"))
    if len(previous) < 1000:
        raise RuntimeError("Refusing to overwrite unexpectedly small main feed")

    prior_links = {
        (normalize_url(x.get("url", "")), x.get("date", "")): x["ticketSwapUrl"]
        for x in previous if x.get("ticketSwapUrl")
    }
    new = [x for x in previous if x.get("source") not in SOURCES]
    seen = {normalize_url(x["url"]) for x in new}
    for item in fresh:
        url = normalize_url(item["url"])
        if url in seen:
            continue
        item = dict(item)
        verified_key = (item["url"].rstrip("/") + "/", item["date"])
        link = VERIFIED_EVENTS.get(verified_key) or prior_links.get((url, item["date"]))
        if link:
            item["ticketSwapUrl"] = link
        seen.add(url)
        new.append(item)

    # Reapply existing verified direct links after updating the feed.
    for item in new:
        key = (item.get("url", "").rstrip("/") + "/", item.get("date", ""))
        if key in VERIFIED_EVENTS:
            item["ticketSwapUrl"] = VERIFIED_EVENTS[key]

    new.sort(key=lambda x: (x.get("date", ""), x.get("time", ""), x.get("artist", "").casefold()))
    counts = Counter(x.get("source") for x in new)
    for name, minimum in SOURCES.items():
        if counts[name] < minimum:
            raise RuntimeError(f"Publication safety stop: {name} only {counts[name]}")
    if len(new) < len(previous):
        raise RuntimeError(f"Publication safety stop: lost records, {len(previous)} -> {len(new)}")
    FEED.write_text(json.dumps(new, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("PUBLISH READY", len(previous), "->", len(new),
          "Bibelot", counts["Bibelot"], "De Pul", counts["De Pul"],
          "TicketSwap links", sum(bool(x.get("ticketSwapUrl")) for x in new), flush=True)


if __name__ == "__main__":
    if len(os.sys.argv) == 2 and os.sys.argv[1] == "collect":
        collect()
    elif len(os.sys.argv) == 2 and os.sys.argv[1] == "apply":
        apply()
    else:
        raise SystemExit("Usage: python -m audit.publish_bibelot_pul collect|apply")
