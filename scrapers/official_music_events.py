"""Strict JSON-LD music-event parser for staged Dutch and Belgian venues.

Use on independently verified official event pages only. No date guessing, no
cross-domain event URLs, and no silent conversion of talks/parties to concerts.
"""
from datetime import date, datetime
from html import unescape
from urllib.parse import urljoin, urlsplit
from zoneinfo import ZoneInfo
import json
import re

BLOCK = re.compile(r'<script\b[^>]*type\s*=\s*["\x27]application/ld\+json["\x27][^>]*>(.*?)</script>', re.I | re.S)
DENIED = re.compile(r"\b(?:comedy|cabaret|workshop|quiz|pubquiz|lezing|talk|clubnight|disco|party|nachtclub|afterparty|rave)\b", re.I)


def _walk(value):
    if isinstance(value, list):
        for child in value:
            yield from _walk(child)
    elif isinstance(value, dict):
        kind = value.get("@type", ())
        kinds = [kind] if isinstance(kind, str) else kind if isinstance(kind, list) else []
        if "MusicEvent" in kinds:
            yield value
        for child in value.values():
            if isinstance(child, (list, dict)):
                yield from _walk(child)


def _on_domain(url, root):
    host = (urlsplit(url).hostname or "").lower().removeprefix("www.")
    domain = (urlsplit(root).hostname or "").lower().removeprefix("www.")
    return urlsplit(url).scheme == "https" and host == domain


def parse_official_music_events(html, page_url, source, city, country, today=None):
    today = today or date.today()
    result = {}
    for match in BLOCK.finditer(html):
        try:
            nodes = list(_walk(json.loads(unescape(match.group(1)))))
        except (ValueError, TypeError):
            continue
        for event in nodes:
            title = unescape(str(event.get("name") or "")).strip()
            if not title or DENIED.search(title):
                continue
            status = str(event.get("eventStatus") or "").lower()
            if any(term in status for term in ("cancelled", "canceled", "postponed")):
                continue
            raw_date = str(event.get("startDate") or "").strip()
            try:
                if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw_date):
                    day, time = date.fromisoformat(raw_date), ""
                else:
                    dt = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
                    if dt.tzinfo:
                        dt = dt.astimezone(ZoneInfo("Europe/Amsterdam"))
                    day, time = dt.date(), dt.strftime("%H:%M")
            except ValueError:
                continue
            if day < today:
                continue
            target = event.get("url") or page_url
            if isinstance(target, dict):
                target = target.get("@id") or target.get("url") or ""
            target = urljoin(page_url, str(target))
            if not _on_domain(target, page_url):
                continue
            loc = event.get("location") or {}
            if isinstance(loc, list):
                loc = next((x for x in loc if isinstance(x, dict)), {})
            hall = loc.get("name") if isinstance(loc, dict) else None
            hall = unescape(str(hall or source)).strip()
            result[target.rstrip("/")] = {
                "artist": title, "venue": hall, "city": city,
                "country": country, "date": day.isoformat(), "time": time,
                "source": source, "url": target.rstrip("/")
            }
    return list(result.values())
