"""Verify full upcoming concert discovery from high-risk venues.

Runs without mutating published concerts.json, printing exact sample missing
concerts and counts to prove pagination/primary-date changes work live.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter
from pathlib import Path
import json

from scrapers.new_venues import scrape_venue
from scrapers.common import scrape_tivolivredenburg, scrape_patronaat, scrape_boerderij
from scrapers.podiuminfo_venues import scrape_podiuminfo_venues

JOBS = {
    "Neushoorn": lambda: scrape_venue("Neushoorn"),
    "Hedon": lambda: scrape_venue("Hedon"),
    "De Helling": lambda: scrape_venue("De Helling"),
    "TivoliVredenburg": scrape_tivolivredenburg,
    "Patronaat": scrape_patronaat,
    "Boerderij": scrape_boerderij,
    "Podiuminfo": scrape_podiuminfo_venues,
}

def main():
    with open("concerts.json",encoding="utf-8") as file:
        old=json.load(file)
    old_urls={}
    for entry in old:
        source=entry.get("source","")
        old_urls.setdefault(source,set()).add(entry.get("url","").lower().rstrip("/"))

    results={}
    with ThreadPoolExecutor(max_workers=3) as ex:
        pending={ex.submit(fn):label for label,fn in JOBS.items()}
        for f in as_completed(pending):
            source=pending[f]
            try:
                events=f.result()
            except Exception as error:
                print("FAILED",source,repr(error),flush=True)
                results[source]={"error":repr(error)}
                continue
            by_source={}
            for event in events:
                by_source.setdefault(event["source"],[]).append(event)
            for name,rows in by_source.items():
                old_keys=old_urls.get(name,set())
                missing=[x for x in rows if x["url"].lower().rstrip("/") not in old_keys]
                report={"count":len(rows),"previous_count":len(old_keys),
                        "new_count":len(missing),
                        "new_samples":[(x["date"],x["artist"],x["url"]) for x in missing[:12]],
                        "preview":[(x["date"],x["artist"]) for x in rows[:6]]}
                results[name]=report
                print("VERIFIED",name,json.dumps(report,ensure_ascii=False),flush=True)

    expected={"Neushoorn":100,"Hedon":112,"TivoliVredenburg":141,"De Helling":53}
    fail=[]
    for src,old_count in expected.items():
        actual=results.get(src,{}).get("count",0)
        if actual<old_count:fail.append((src,actual,old_count))
    Path("diagnostics/output").mkdir(exist_ok=True,parents=True)
    with open("diagnostics/output/source-verification.json","w",encoding="utf-8") as f:
        json.dump(results,f,ensure_ascii=False,indent=2)
    if fail:raise RuntimeError("Fewer than previously published at critical sources: "+repr(fail))
    for src in ("Neushoorn","Hedon","TivoliVredenburg"):
        if not results.get(src,{}).get("new_count",0):
            raise RuntimeError("No additional concerts found at source "+src)
    print("ALL CRITICAL VENUE UPGRADES VERIFIED",flush=True)

if __name__=="__main__":
    main()
