import json
import re
import urllib.request
import urllib.error

URLS = [
    "https://www.ticketswap.nl/concert-tickets/james-blake-utrecht-tivolivredenburg-2026-10-06-CZA4ntDvc8empFpLDfnso",
    "https://www.ticketswap.nl/concert-tickets/l/netherlands/utrecht/next-month",
]
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/154.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
    "Accept-Language": "nl-NL,nl;q=0.9,en;q=0.8",
}
for url in URLS:
    print("\nURL", url)
    try:
        req=urllib.request.Request(url,headers=HEADERS)
        with urllib.request.urlopen(req,timeout=20) as r:
            raw=r.read().decode("utf-8","replace")
            print("STATUS",r.status,"FINAL",r.geturl(),"TYPE",r.headers.get("content-type"),"LEN",len(raw))
            for needle in ["James Blake","graphql","activeEvents","getPopularEvents","__NEXT_DATA__","CZA4ntDvc8empFpLDfnso"]:
                print(needle, needle.lower() in raw.lower())
            hosts=sorted(set(re.findall(r'https?://[^/"\\s]+',raw,re.I)))
            print("HOSTS", [h for h in hosts if "ticket" in h.lower() or "api" in h.lower()][:30])
            ops=sorted(set(re.findall(r'(?:operationName|queryName)[^A-Za-z0-9_]{1,20}([A-Za-z][A-Za-z0-9_]{3,60})',raw)))
            print("OPS",ops[:50])
    except Exception as e:
        print("ERROR",repr(e))
