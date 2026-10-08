"""Live diagnostic for concerts listed by venues but missing from feed.

This diagnostic intentionally does NOT mutate concerts.json.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import date
import json
import re
from scrapers.common import download_page_retry, _detail_date_time, _detail_title, clean_text
from scrapers.new_venues import parse_event, json_events, date_from_text, iso_date_time, hedon_primary_date_time

CASES={
"SPOT Groningen":[
"https://www.spotgroningen.nl/programma/timebox/",
"https://www.spotgroningen.nl/programma/pitou/",
"https://www.spotgroningen.nl/programma/levi-sct/",
"https://www.spotgroningen.nl/programma/pieter-savenberg/",
"https://www.spotgroningen.nl/programma/alexis-ffrench/",
],
"Hedon":[
"https://hedon-zwolle.nl/voorstelling/32962/big-sleep",
"https://hedon-zwolle.nl/voorstelling/33038/never-too-late",
"https://hedon-zwolle.nl/voorstelling/32928/bartofso",
],
"Metropool":[
"https://metropool.nl/agenda/nona",
"https://metropool.nl/agenda/waxing-crescent",
"https://metropool.nl/agenda/spanish-heat",
],
"De Helling":[
"https://dehelling.nl/agenda/freax-07-11-2026/",
"https://dehelling.nl/agenda/le-guess-who-2026-06-11-2026/",
],
"Effenaar":[
"https://www.effenaar.nl/agenda/cryogenic-presents-reincarnated",
"https://www.effenaar.nl/agenda/kovacs-13feb",
],
"PAARD":[
"https://www.paard.nl/event/john-illsley-of-dire-straits/",
"https://www.paard.nl/event/moodyblues/",
],
"Boerderij":[
"https://poppodiumboerderij.nl/programma/bigbigtrain/",
"https://poppodiumboerderij.nl/programma/sari-schorr/",
"https://poppodiumboerderij.nl/programma/thetangent/",
]
}
CITIES={"SPOT Groningen":"Groningen","Hedon":"Zwolle","Metropool":"Hengelo",
        "De Helling":"Utrecht","Effenaar":"Eindhoven","PAARD":"Den Haag","Boerderij":"Zoetermeer"}
def one(case):
    name,url=case
    try:
        html=download_page_retry(url, attempts=2)
        title=_detail_title(html)
        text=clean_text(html)
        e=list(json_events(html))
        record=dict(name=name,url=url,bytes=len(html),
            title=title[:135],from_common=_detail_date_time(html),
            textdate=date_from_text(text[:2800]), meta=[])
        for event in e[:3]:
            record["meta"].append(dict(name=str(event.get("name",""))[:90],
                 date=event.get("startDate"),status=event.get("eventStatus")))
        if name in ("Hedon","Metropool","De Helling","SPOT Groningen"):
            record["parsed"]=parse_event(html,url,name,CITIES[name])
        if name=="Hedon":
            record["hedon_primary"]=hedon_primary_date_time(html)
        record["beginning"]=text[:650]
        return record
    except Exception as exc:
        return dict(name=name,url=url,error=str(exc)[:350])
def main():
    cases=[(name,url) for name, urls in CASES.items() for url in urls]
    with ThreadPoolExecutor(max_workers=7) as pool:
        results=list(pool.map(one,cases))
    for x in results:
        print("DETAIL",json.dumps(x,ensure_ascii=False,default=str),flush=True)
if __name__=="__main__":main()
