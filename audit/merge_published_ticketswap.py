"""Never let a long-running concert scraper erase previously published TicketSwap links.

Called by the publication workflow AFTER fetching the latest origin/main,
not against the stale checkout from when the scraper started.
"""
import json
import sys
from pathlib import Path

def key(item):
    return (str(item.get("url", "")).strip().rstrip("/").casefold(),
            str(item.get("date", "")).strip())

def preserve_ticket_links(generated, latest_published):
    latest = {
        key(item): item["ticketSwapUrl"]
        for item in latest_published
        if isinstance(item, dict) and item.get("ticketSwapUrl")
    }
    preserved = 0
    existing = 0
    checked = 0
    for item in generated:
        if not isinstance(item, dict):
            raise ValueError("Expected concert dict")
        current_key = key(item)
        previously_verified = latest.get(current_key)
        if previously_verified:
            checked += 1
            if item.get("ticketSwapUrl") != previously_verified:
                item["ticketSwapUrl"] = previously_verified
                preserved += 1
            else:
                existing += 1
    if any(item.get("ticketSwapUrl") != latest[key(item)]
           for item in generated if key(item) in latest):
        raise RuntimeError("Refusing to publish: known TicketSwap links would disappear")
    return preserved, existing, checked


def main(previous_file, generated_file):
    earlier = json.loads(Path(previous_file).read_text(encoding="utf-8"))
    current = json.loads(Path(generated_file).read_text(encoding="utf-8"))
    if not isinstance(earlier, list) or not isinstance(current, list):
        raise ValueError("Invalid concert database")
    preserved, existing, checked = preserve_ticket_links(current, earlier)
    with open(generated_file, "w", encoding="utf-8") as output:
        json.dump(current, output, ensure_ascii=False, indent=2)
        output.write("\n")
    print("LIVE TICKETSWAP LINKS PRESERVED:", preserved,
          "already present:", existing,
          "verified links in still-listed concerts:", checked,
          "resulting total:", sum(bool(e.get("ticketSwapUrl")) for e in current),
          flush=True)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Usage: python -m audit.merge_published_ticketswap prior.json generated.json")
    main(sys.argv[1], sys.argv[2])
