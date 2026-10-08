"""Publish only newly verified Amare, Bolwerk and Patronaat concerts.

This operation is run in the same GitHub Actions concurrency group as the
full production scraper. It starts from the latest published JSON feed and
does not re-scrape or remove other concert venues.
"""
from collections import Counter
from datetime import date
from pathlib import Path
from scrapers.podiuminfo_full import scrape_full_podiuminfo_source
from scrapers.common import scrape_patronaat
import json
import re

TARGETS=("Amare","Bolwerk","Patronaat")
MINIMUMS={"Amare":25,"Bolwerk":25,"Patronaat":125}

def norm(url):
    return url.strip().rstrip("/").lower()

def update():
    path=Path("concerts.json")
    published=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(published,list) or len(published)<2000:
        raise RuntimeError("Unexpectedly small original concert feed")
    today=date.today().isoformat()
    new={
        "Amare": scrape_full_podiuminfo_source("Amare"),
        "Bolwerk": scrape_full_podiuminfo_source("Bolwerk"),
        "Patronaat": scrape_patronaat(),
    }
    for source in TARGETS:
        fresh=new[source]
        urls=[norm(e["url"]) for e in fresh]
        if len(fresh)<MINIMUMS[source] or len(set(urls))!=len(urls):
            raise RuntimeError("Target source not complete: "+source+" "+str(len(fresh)))
        previous=sum(e.get("source")==source and e.get("date","")>=today for e in published)
        if len(fresh)<max(1,int(previous*0.7)):
            raise RuntimeError("Target dropped too far: "+source+" "+str(previous)+" -> "+str(len(fresh)))
        print("REPLACE",source,previous,"->",len(fresh),flush=True)

    if not any("slodde" in x["artist"].casefold() for x in new["Patronaat"]):
        raise RuntimeError("Required Patronaat concert SlodDe still absent")
    all_new=[x for group in new.values() for x in group]

    def inappropriate(e):
        if e.get("source")=="TivoliVredenburg":
            return bool(re.search(
                r"\b(?:podcast|pubquiz|karaoke|rondleiding|lezing|"
                r"discozwemmen|clubnacht|fanparty|silent disco|workshop)\b|"
                r"\bparty\s*$",
                e.get("artist",""),re.I,
            ))
        if e.get("source")=="Hedon":
            return bool(re.search(
                r"80s-verantwoord|80.s.verantwoord",
                e.get("artist",""),re.I,
            ))
        return False

    kept=[x for x in published if x.get("source") not in TARGETS and not inappropriate(x)]
    result=kept+all_new
    keys=set()
    for e in result:
        key=norm(e["url"])
        if key in keys:
            raise RuntimeError("Duplicate event URL: "+e["url"])
        if e.get("date","")<today:
            raise RuntimeError("Past event found: "+e.get("url",""))
        keys.add(key)

    result.sort(key=lambda e:(e["date"],e.get("time",""),e["artist"].casefold()))
    counts=Counter(e["source"] for e in result)
    if counts["BIRD"]<35 or counts["Neushoorn"]<100 or counts["TivoliVredenburg"]<300:
        raise RuntimeError("Unexpected regression at previously verified venue")
    print("NEW COMPLETE FEED:",len(result),"EVENTS; COUNTS:",dict(counts),flush=True)
    path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf8")

if __name__=="__main__":
    update()
