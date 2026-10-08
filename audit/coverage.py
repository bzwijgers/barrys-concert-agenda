"""Audit official venue listings against the published feed, without changing it.

This is an independent discovery check, not a claim that every listing is a
concert: it reports potential missing official event URLs to investigate.
"""
from concurrent.futures import ThreadPoolExecutor
from html import unescape
from html.parser import HTMLParser
from collections import Counter
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import json
import re

class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.anchors=[]
    def handle_starttag(self, tag, attrs):
        if tag=="a":
            href=dict(attrs).get("href")
            if href:self.anchors.append(href)

SITES={
 "Rotown":(["https://www.rotown.nl/agenda/"],["/agenda/","/concert/","/event/"]),
 "Effenaar":(["https://www.effenaar.nl/agenda/"],["/agenda/"]),
 "013":(["https://www.013.nl/programma/"],["/programma/"]),
 "Baroeg":(["https://baroeg.nl/agenda/"],["/productie/"]),
 "Boerderij":(["https://poppodiumboerderij.nl/search/events/still/"],["/programma/"]),
 "PAARD":(["https://www.paard.nl/event/"],["/event/"]),
 "Melkweg":(["https://www.melkweg.nl/nl/agenda/?profile=Concert"],["/nl/agenda/"]),
 "TivoliVredenburg":(["https://www.tivolivredenburg.nl/agenda/","https://www.tivolivredenburg.nl/agenda?sf_genre=pop"],["/agenda/"]),
 "MEZZ":(["https://www.mezz.nl/voorbeeld-show-lijst/","https://www.mezz.nl/programma/"],["/programma/"]),
 "Patronaat":(["https://patronaat.nl/programma/","https://patronaat.nl/genre/rock/"],["/event/"]),
 "De Helling":(["https://dehelling.nl/agenda/","https://dehelling.nl/agenda/?page=2"],["/agenda/"]),
 "Klokgebouw":(["https://www.klokgebouw.nl/agenda"],["/agenda/"]),
 "Dynamo":(["https://www.dynamo-eindhoven.nl/evenementen/","https://www.dynamo-eindhoven.nl/activiteiten/"],["/evenement/"]),
 "Doornroosje":(["https://www.doornroosje.nl/","https://www.doornroosje.nl/agenda/"],["/event/"]),
 "Metropool":(["https://metropool.nl/agenda"],["/agenda/"]),
 "Hedon":(["https://hedon-zwolle.nl/","https://hedon-zwolle.nl/agenda/"],["/voorstelling/"]),
 "SPOT Groningen":(["https://www.spotgroningen.nl/programma/?genre=muziek","https://www.spotgroningen.nl/programma/?genre=muziek&page=2"],["/programma/"]),
 "Neushoorn":(["https://www.neushoorn.nl/programma","https://www.neushoorn.nl/programma?page=2","https://www.neushoorn.nl/programma/2","https://www.neushoorn.nl/programma?page=3"],["/events/"]),
 "Amare":(["https://www.amare.nl/nl/agenda"],["/nl/agenda/"]),
 "Bolwerk":(["https://www.hetbolwerk.nl/","https://ontdekpoort.nl/agenda"],["/agenda/","/event/"]),
 "Gebouw-T":(["https://gebouw-t.nl/agenda/","https://gebouw-t.nl/agenda/page/2/","https://gebouw-t.nl/agenda/page/3/"],["/agenda/"]),
 "dB's":(["https://www.dbstudio.nl/events/categorie/alles/concert/lijst/","https://dbstudio.nl/wp-json/tribe/events/v1/events/?categories=concert&per_page=1&page=1"],["/event/"]),
}
def canonical(url):
    x=urlsplit(url)
    host=(x.hostname or "").lower().removeprefix("www.")
    path=re.sub(r"/+","/",x.path).rstrip("/").lower()
    return host+path

def inspect(site,urls,prefixes,feed):
    old={canonical(e["url"]) for e in feed if e.get("source")==site}
    out=[]
    for page_url in urls:
        try:
            req=Request(page_url,headers={
                "User-Agent":"Mozilla/5.0 (compatible; BarryConcertAgendaQA/1.0)",
                "Accept":"text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
                "Accept-Language":"nl-NL,nl;q=0.9",
            })
            with urlopen(req,timeout=18) as r:
                html=r.read().decode("utf-8","replace")
                final=r.url
                status=r.status
                content_type=r.headers.get("Content-Type","")
            if "json" in content_type.lower() and html.startswith("{"):
                payload=json.loads(html)
                out.append(dict(url=page_url,status=status,content_type=content_type,size=len(html),
                                total=payload.get("total"),total_pages=payload.get("total_pages"),
                                event_entries=len(payload.get("events",[]))))
                continue
            p=Links();p.feed(html)
            found={}
            host=(urlsplit(final).hostname or "").removeprefix("www.")
            for h in p.anchors:
                full=urljoin(final,unescape(h)).split("#",1)[0].split("?",1)[0]
                x=urlsplit(full)
                if (x.hostname or "").removeprefix("www.")!=host:continue
                if not any(z in x.path for z in prefixes):continue
                if x.path.rstrip("/") in ("/agenda","/programma","/event","/events","/nl/agenda","/activiteiten","/evenementen"):
                    continue
                key=canonical(full)
                found[key]=full
            existing=[u for k,u in found.items() if k in old]
            missing=[u for k,u in found.items() if k not in old]
            out.append(dict(url=page_url,final=final,status=status,bytes=len(html),
                            links=len(found),feed_matching=len(existing),not_in_feed=len(missing),
                            missing_examples=missing[:14],all_preview=list(found.values())[:7],
                            next_markers={s:len(re.findall(re.escape(s),html,re.I)) for s in
                            ["next_page","loadmore","load-more","volgende","pagination","sitemap","page=2","api/"]}))
        except Exception as exc:
            out.append(dict(url=page_url,error=str(exc)[:240]))
    return site, dict(published=len(old),pages=out)

def main():
    with open("concerts.json",encoding="utf-8") as f:feed=json.load(f)
    with ThreadPoolExecutor(max_workers=9) as executor:
        results=list(executor.map(lambda item:inspect(item[0],item[1][0],item[1][1],feed),SITES.items()))
    report={site:details for site,details in results}
    for site,details in report.items():
        print("\n##",site,"published",details["published"],flush=True)
        for info in details["pages"]:
            print(json.dumps(info,ensure_ascii=False),flush=True)
    import os
    os.makedirs("diagnostics/output",exist_ok=True)
    with open("diagnostics/output/coverage.json","w",encoding="utf-8") as f:
        json.dump(report,f,ensure_ascii=False,indent=2)
    print("\nAUDIT_FINISHED",len(report),"sources",flush=True)
if __name__=="__main__":main()
