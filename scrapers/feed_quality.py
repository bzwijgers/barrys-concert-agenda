"""Quality gates shared by all music sources before publishing the concert feed."""
from __future__ import annotations

import re
import unicodedata
from urllib.parse import urlsplit


def _norm(value):
    value = unicodedata.normalize("NFKD", (value or "").casefold())
    value = "".join(char for char in value if not unicodedata.combining(char))
    return " ".join(re.findall(r"[a-z0-9]+", value))


def _is_secondary_index(event):
    return (urlsplit(event.get("url") or "").hostname or "").lower().removeprefix("www.") == "podiuminfo.nl"


def deduplicate_performances(events):
    """Prefer a concert hall's record over a secondary listing of the same show.

    URLs alone are insufficient: official halls, agents and public programme
    sites use different links for the same performance. Two performances on the
    same day with different times must survive. One index's start/door time may
    differ from the actual performance start, so source-index duplicates are
    matched even when their times differ.

    Only collapse exact artist/date/city/venue identities; avoid guessing
    that similarly named acts or nearby halls describe the same performance.
    """
    output = []
    bucket = {}
    removed = []
    for item in events:
        key = (item.get("date", ""), _norm(item.get("city")),
               _norm(item.get("venue")), _norm(item.get("artist")))
        matches = bucket.setdefault(key, [])
        duplicate_index = None
        for ix in matches:
            previous = output[ix]
            if (_is_secondary_index(previous) or _is_secondary_index(item)
                    or (previous.get("time") or "") == (item.get("time") or "")):
                duplicate_index = ix
                break
        if duplicate_index is None:
            matches.append(len(output))
            output.append(item)
        else:
            original = output[duplicate_index]
            if _is_secondary_index(original) and not _is_secondary_index(item):
                output[duplicate_index] = item
                removed.append(original)
            else:
                removed.append(item)
    return output, removed


# Targeted exclusions, not broad keywords like "party", "ADE" or "DJ":
# those would incorrectly reject live bands/performances and music festivals.
NON_CONCERT_TITLE = re.compile(
    r"^(?:fiesta macumba|90['’]?s now|cheeky monday\b|"
    r"muziek bingo(?: xxl)?\b|qmusic the party\b|"
    r"jimmy carr(?:\b|:)|)"
    r"|(?:^|[\s\-])(?:comedy show|stand[\s-]?up comedy)(?:\b|$)",
    re.I,
)


def is_known_nonconcert(event):
    """Drop specifically verified party/quiz/comedy entries, all providers."""
    title = (event.get("artist") or "").strip()
    return bool(NON_CONCERT_TITLE.search(title))
