"""Refuse a concurrent publication that unexpectedly loses future concert coverage.

This guard compares the verified candidate with the *latest* main feed, not
with the potentially stale feed checked out when the scraper started.
"""
import json
import sys
from collections import Counter
from datetime import datetime
from zoneinfo import ZoneInfo


def counts(items, today):
    return Counter(
        x["source"] for x in items
        if isinstance(x, dict)
        and isinstance(x.get("source"), str)
        and isinstance(x.get("date"), str)
        and x["date"] >= today
    )


def check(previous, candidate, today=None, minimum_baseline=20, max_drop=0.35):
    today = today or datetime.now(ZoneInfo('Europe/Amsterdam')).date().isoformat()
    if not isinstance(previous, list) or not isinstance(candidate, list):
        raise ValueError("Both feeds must contain JSON arrays")
    old, new = counts(previous, today), counts(candidate, today)
    issues = []
    for source, count in sorted(old.items()):
        if count < minimum_baseline:
            continue
        if new[source] < count * (1 - max_drop):
            issues.append(f"{source}: {count} -> {new[source]}")
    old_total, new_total = sum(old.values()), sum(new.values())
    if old_total >= minimum_baseline and new_total < old_total * (1 - max_drop):
        issues.append(f"TOTAL: {old_total} -> {new_total}")
    if issues:
        raise ValueError("Unexpected future-concert loss; publication blocked: " + "; ".join(issues))
    return old_total, new_total


def main():
    if len(sys.argv) != 3:
        raise SystemExit("Usage: python -m audit.publication_guard previous.json candidate.json")
    with open(sys.argv[1], encoding="utf-8") as f:
        previous = json.load(f)
    with open(sys.argv[2], encoding="utf-8") as f:
        candidate = json.load(f)
    try:
        before, after = check(previous, candidate)
    except ValueError as exc:
        raise SystemExit(str(exc))
    print(f"Publication guard OK: {before} -> {after} future concerts")


if __name__ == "__main__":
    main()
