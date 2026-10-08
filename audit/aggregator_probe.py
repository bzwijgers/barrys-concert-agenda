"""Inspect completeness and venue name variants of Podiuminfo fallbacks."""
from scrapers.common import download_page_retry
from scrapers.podiuminfo_venues import PODIUMINFO_VENUES
from collections import Counter
from html import unescape
import json,re

all_sources = list(PODIUMINFO_VENUES.items()) + [
    ("Amare full", ("https://www.podiuminfo.nl/concertagenda/podium/amare/", "Amare", "Den Haag")),
    ("Bolwerk full", ("https://www.podiuminfo.nl/concertagenda/podium/het-bolwerk/", "Het Bolwerk", "Sneek")),
]
for name,(url,venue,city) in all_sources:
    print("\n==== AGGREGATOR",name,url,"====",flush=True)
    try:
        html=download_page_retry(url,attempts=3)
        scripts=re.findall(
            r'<script[^>]*type=["\x27]application/ld\+json["\x27][^>]*>(.*?)</script>',
            html,re.I|re.S,
        )
        types=Counter();loc=Counter();music=[];sample=[]
        for script in scripts:
            try: v=json.loads(unescape(script))
            except Exception:continue
            if isinstance(v,list):records=v
            elif isinstance(v,dict) and isinstance(v.get("@graph"),list):
                records=v["@graph"]
            else:records=[v]
            for item in records:
                if not isinstance(item,dict):continue
                kind=item.get("@type")
                if isinstance(kind,list):kind=";".join(kind)
                types[str(kind)]+=1
                if "Event" not in str(kind):continue
                place=item.get("location") or {}
                where=place.get("name","") if isinstance(place,dict) else str(place)
                loc[where]+=1
                music.append((str(item.get("name",""))[:90],where,str(item.get("startDate",""))[:22]))
        print("RAW LENGTH",len(html),"SCRIPTS",len(scripts),"TYPES",dict(types),
              "LOCATION COUNTS",dict(loc),"EVENT COUNT",len(music),flush=True)
        print("SAMPLES",music[:28],"LAST",music[-12:],flush=True)
        links=re.findall(r'<a\b[^>]*href=["\x27]([^"\x27]+)["\x27]',html,re.I)
        concert_links=[s for s in links if "/concert/" in s.lower()]
        unique_concerts=list(dict.fromkeys(concert_links))
        print("CONCERT HREFS",len(unique_concerts),"FIRST",unique_concerts[:12],
              "LAST",unique_concerts[-12:],flush=True)
        for term in ("dewolff","steve vai","haevn","teenage fanclub","ana popovic","Rufus Wainwright"):
            match=re.search(re.escape(term),html,re.I)
            if match:
                excerpt=re.sub(r"\s+"," ",html[max(0,match.start()-450):match.end()+550])
                print("EXCERPT",term,excerpt[:980],flush=True)
        for p in ('page=', '?page=', 'pagina=', 'start=', 'offset=', '/concertagenda/podium/', 'data-page'):
            print("PAGINATOR",p,[re.sub(r"\s+"," ",html[max(0,m.start()-60):m.end()+95])[:190]
                    for m in list(re.finditer(re.escape(p),html,re.I))[:5]],flush=True)

        print("PAGING MARKERS",[(s,len(re.findall(s,html,re.I))) for s in
              ("page=2","/page/2","volgende","pagination","more","next","load")],flush=True)
    except Exception as error:
        print("AGGREGATOR ERROR",name,repr(error),flush=True)
