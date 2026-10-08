"""Compare official Hedon Nights against Barry's published concert feed."""
import json
from pathlib import Path
from scrapers.common import download_page_retry
from scrapers.new_venues import discover,filter_hedon_nights

def main():
    official=download_page_retry("https://hedon-zwolle.nl/nights",attempts=3)
    links=discover(official,"https://hedon-zwolle.nl/nights","/voorstelling/")
    filtered=filter_hedon_nights(links,official)
    if filtered:
        raise RuntimeError("Official Nights URLs were not all removed")
    feed=json.loads(Path("concerts.json").read_text(encoding="utf-8"))
    normalized=lambda u:u.lower().replace("www.hedon-zwolle.nl","hedon-zwolle.nl").rstrip("/")
    in_feed={normalized(e["url"]):e for e in feed if e["source"]=="Hedon"}
    night_concerts=[in_feed[normalized(u)] for u in links if normalized(u) in in_feed]
    print("OFFICIAL HEDON NIGHTS URLS:",len(links),flush=True)
    for e in night_concerts:
        print("INCORRECT CLUB EVENT:",e["artist"],e["date"],e["url"],flush=True)
    print("HEDON NIGHTS INCORRECTLY INCLUDED:",len(night_concerts),flush=True)
    if night_concerts:
        raise RuntimeError("Published concert feed contains official Hedon Nights events")

if __name__=="__main__":
    main()
