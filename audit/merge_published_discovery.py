"""Keep first-discovery timestamps consistent across concurrent feed publications."""
import json
import sys
from urllib.parse import urlsplit, urlunsplit


def identity(item):
    url = (item.get("url") or "").strip().rstrip("/")
    return (url.casefold(), item.get("date") or "")


def valid_timestamp(value):
    return value if type(value) is int and value > 0 else 0


def merge(previous, candidate):
    """Preserve the earliest positive discovery time for matching performances.

    A newly discovered event in the latest main feed must not become 'new'
    again when an older scrape is published. Never transfer timestamps
    across dates, since a venue can reuse an event URL for another show.
    """
    earlier = {identity(item): valid_timestamp(item.get("firstFound"))
               for item in previous if isinstance(item, dict) and item.get("url")}
    changed = 0
    for item in candidate:
        if not isinstance(item, dict) or not item.get("url"):
            continue
        key = identity(item)
        current = valid_timestamp(item.get("firstFound"))
        known = earlier.get(key)
        if known is None:
            continue
        result = min(current, known) if current and known else current or known
        if result != current:
            item["firstFound"] = result
            changed += 1
    return changed


def main():
    if len(sys.argv) != 3:
        raise SystemExit("Usage: python -m audit.merge_published_discovery previous.json candidate.json")
    with open(sys.argv[1], encoding="utf-8") as f:
        previous = json.load(f)
    with open(sys.argv[2], encoding="utf-8") as f:
        candidate = json.load(f)
    if not isinstance(previous, list) or not isinstance(candidate, list):
        raise SystemExit("Expected two JSON arrays")
    count = merge(previous, candidate)
    with open(sys.argv[2], "w", encoding="utf-8") as f:
        json.dump(candidate, f, ensure_ascii=False, indent=2)
    print("First-discovery timestamps restored:", count)


if __name__ == "__main__":
    main()
