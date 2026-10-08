"""Verify a known Paradiso concert is present in both cached recovery and live feed."""
from datetime import date
from pathlib import Path
import json
from scrapers.paradiso import PARADISO_RECOVERY_EVENTS, paradiso_parse_event
from scrapers.common import download_page_retry

URL="https://www.paradiso.nl/nl/programma/honey-im-home/2841259"
REQUIRED=("Honey I'm Home","Tolhuistuin","Tolhuistuin","2026-12-30","20:30")

def verify(item):
    if not item:
        raise RuntimeError("Honey I'm Home missing")
    actual=tuple(item.get(x) for x in ("artist","venue","source","date","time"))
    if actual!=REQUIRED:
        raise RuntimeError(f"Incorrect verified Tolhuistuin concert: {actual!r}")
    return actual

def main():
    assert PARADISO_RECOVERY_EVENTS[URL]=="2026-12-30"
    backup=json.loads(Path("scrapers/paradiso_recovery.json").read_text(encoding="utf-8"))
    verify(next((x for x in backup if x.get("url")==URL),None))
    feed=json.loads(Path("concerts.json").read_text(encoding="utf-8"))
    verify(next((x for x in feed if x.get("url")==URL),None))
    print("PASS: show present in recovery and published feed",flush=True)
    html=download_page_retry(URL,attempts=4)
    parsed=paradiso_parse_event(html,URL)
    print("LIVE PARADISO:",verify(parsed),"html bytes:",len(html),flush=True)
    print("PASSED all recovery and live official page tests",flush=True)

if __name__=="__main__": main()
