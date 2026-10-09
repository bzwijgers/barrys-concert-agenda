"""Stable, source-independent first discovery timestamps for concert feeds.

Legacy events from the previous published feed are not suddenly marked new.
New events get one firstFound epoch millisecond timestamp that survives future
scraper runs, irrespective of when a particular phone opens the app.
"""
from __future__ import annotations

from typing import Any

from .common import normalize_url


def attach_first_found(concerts: list[dict], previous: list[dict], now_ms: int) -> list[dict]:
    prior_by_url = {}
    prior_by_event = {}
    for old in previous:
        if not isinstance(old, dict):
            continue
        url = normalize_url(old.get("url", ""))
        key = (
            old.get("source", "").casefold(),
            old.get("artist", "").casefold().strip(),
            old.get("date", ""),
            old.get("city", "").casefold(),
        )
        if url:
            prior_by_url[url] = old
        prior_by_event.setdefault(key, old)

    for event in concerts:
        url = normalize_url(event.get("url", ""))
        key = (
            event.get("source", "").casefold(),
            event.get("artist", "").casefold().strip(),
            event.get("date", ""),
            event.get("city", "").casefold(),
        )
        prior = prior_by_url.get(url) or prior_by_event.get(key)
        if prior is None:
            event["firstFound"] = now_ms
        else:
            # The first run sees legacy records without discovery metadata.
            # Zero means known BEFORE tracking began, not new today.
            first = prior.get("firstFound", 0)
            event["firstFound"] = first if type(first) is int and first > 0 else 0
    return concerts
