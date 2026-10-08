"""Proof-of-concept complete event feeds from Podiuminfo's full venue listings."""
from html.parser import HTMLParser
from html import unescape
from datetime import date
from collections import Counter
from urllib.parse import urlsplit
from urllib.request import Request,urlopen
import json,re

MONTHS = {
    "januari":1,"februari":2,"maart":3,"april":4,"mei":5,"juni":6,
    "juli":7,"augustus":8,"september":9,"oktober":10,"november":11,"december":12
}
WEEKDAYS = "maandag|dinsdag|woensdag|donderdag|vrijdag|zaterdag|zondag"

class ConcertLinks(HTMLParser):
    def __init__(self):super().__init__();self.anchors=[]
    def handle_starttag(self,tag,attrs):
        if tag=="a":
            d=dict(attrs)
            if "/concert/" in d.get("href","") and d.get("aria-label"):
                self.anchors.append(d)

def parse_anchor(item,venue,source,city,today=None):
    href=item.get("href","").split("?",1)[0].rstrip("/")
    if not href.startswith("https://www.podiuminfo.nl/concert/"):return None
    path=urlsplit(href).path.rstrip("/").split("/")
    if not path or path[-1].casefold()!=venue.casefold().replace(" ","-"):return None
    label=unescape(item.get("aria-label",""))
    pattern=rf",\s*(?:{WEEKDAYS})\s+(\d{{1,2}})\s+({'|'.join(MONTHS)})\s+(20\d{{2}})\s+om\s+([01]?\d|2[0-3]):([0-5]\d)"
    match=re.search(pattern,label,re.I)
    if not match:return None
    event_title=label[:match.start()].strip()
    if event_title.casefold().startswith("concert "):event_title=event_title[8:].strip()
    event_date=date(int(match.group(3)),MONTHS[match.group(2).lower()],int(match.group(1)))
    if event_date < (today or date.today()):return None
    exclude=r"social dance|workshop|masterclass|cabaret|comedy|dancehague|danspaleis|meet.?up|lezing|rondleiding|ballet|dj.?party|80's.?90's.?00's party|clubnacht"
    if not event_title or re.search(exclude,event_title,re.I):return None
    return dict(artist=event_title,venue=venue,city=city,country="NL",
                date=event_date.isoformat(),time=f"{int(match.group(4)):02d}:{match.group(5)}",
                source=source,url=href)

VENUES={
    "Amare":("https://www.podiuminfo.nl/concertagenda/podium/amare/","Amare","Den Haag"),
    "Bolwerk":("https://www.podiuminfo.nl/concertagenda/podium/het-bolwerk/","Het Bolwerk","Sneek"),
}

def scrape_full(source):
    url,venue,city=VENUES[source]
    req=Request(url,headers={"User-Agent":"Mozilla/5.0 (compatible; BarryConcertAgenda/1.0)"})
    with urlopen(req,timeout=25) as r:html=r.read().decode("utf8","replace")
    parser=ConcertLinks();parser.feed(html)
    found={}
    errors=Counter()
    for a in parser.anchors:
        x=parse_anchor(a,venue,source,city)
        if x:found[x["url"].lower()]=x
        else:errors["excluded_or_bad"]=errors["excluded_or_bad"]+1
    result=sorted(found.values(),key=lambda x:(x["date"],x["time"],x["artist"]))
    print("SOURCE",source,"HTML",len(html),"RAW EVENT ANCHORS",len(parser.anchors),
          "VALID",len(result),"EXCLUDED",errors["excluded_or_bad"],flush=True)
    for x in result[:12]+result[-8:]:
        print("EXAMPLE",source,json.dumps(x,ensure_ascii=False),flush=True)
    return result

if __name__=="__main__":
    for name in VENUES:
        events=scrape_full(name)
        if len(events)<30:raise RuntimeError(f"{name}: unexpectedly few concert rows {len(events)}")
        expected={"Amare":["HAEVN","DeWolff","Steve Vai"],"Bolwerk":["Teenage Fanclub","Ana Popovic"]}
        for keyword in expected[name]:
            if not any(keyword.lower() in e["artist"].lower() for e in events):
                raise RuntimeError(f"{name}: missing known future event {keyword}")
        print("COMPLETE-LIST REGRESSION PASS",name,len(events),flush=True)
