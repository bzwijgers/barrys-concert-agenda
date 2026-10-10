"""Belgian concerts from the official Ticketmaster Discovery API.

Uses the same API secret as the Dutch feed. Music events only, local
Belgian venues only, and no VIP/parking/upsell products. The central
pipeline handles cross-source performance deduplication.
"""
from collections import Counter
from datetime import date, timedelta
import os
from .ticketmaster_nl import _fetch_range, event_to_concert, merge_ticketmaster, _norm, _concert_title, _venue_name


def scrape_ticketmaster_be(api_key=None, today=None, getter=None):
    key = (api_key if api_key is not None else os.getenv("TICKETMASTER_API_KEY", "")).strip()
    if not key:
        print("Ticketmaster BE: API secret missing; skipping.", flush=True)
        return []
    today = today or date.today()
    args = {"country_code": "BE"}
    if getter is not None:
        args["getter"] = getter
    events = _fetch_range(today, today + timedelta(days=730), key, **args)
    found = {}
    for event in events:
        show = event_to_concert(event, today=today.isoformat(), country_code="BE")
        if not show:
            continue
        identity = (show["date"], _norm(show["city"]), _venue_name(show["venue"]),
                    _norm(_concert_title(show["artist"])))
        found.setdefault(identity, show)
    result = list(found.values())
    print("Ticketmaster BE:", len(result), "shows,",
          len(Counter(x["venue"] for x in result)), "venues", flush=True)
    return result
