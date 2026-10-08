"""Investigate missing events, pagination and filters using live official pages."""
from urllib.request import Request,urlopen
from urllib.parse import urljoin,urlsplit
from html import unescape
from html.parser import HTMLParser
import json,re
from collections import Counter
from scrapers.common import _detail_date_time, find_site_event_urls
from scrapers.new_venues import parse_event, date_from_text

class Links(HTMLParser):
    def __init__(self):super().__init__();self.hrefs=[]
    def handle_starttag(self,tag,attrs):
        if tag=="a":
            x=dict(attrs)
            if x.get("href"):self.hrefs.append((x["href"],str(x.get("class",""))))
def get(url):
    with urlopen(Request(url,headers={"User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X) AppleWebKit/537.36 Chrome/131 Safari/537.36","Accept-Language":"nl-NL,nl;q=0.9"}),timeout=20) as r:
        h=r.read().decode("utf8","replace");return h,r.url,r.status

URLS={
"Neushoorn": ["https://www.neushoorn.nl/programma","https://www.neushoorn.nl/programma?page=2"],
"Tivoli": ["https://www.tivolivredenburg.nl/agenda?sf_genre=pop","https://www.tivolivredenburg.nl/agenda/page/2/?sf_genre=pop","https://www.tivolivredenburg.nl/agenda/page/3/?sf_genre=pop"],
"Boerderij":[
"https://poppodiumboerderij.nl/programma/myrath/","https://poppodiumboerderij.nl/programma/banned-from-utopia-1/","https://poppodiumboerderij.nl/programma/bigbigtrain/",
"https://poppodiumboerderij.nl/programma/greghowe/"],
"Hedon":["https://hedon-zwolle.nl/voorstelling/32972/froukje","https://hedon-zwolle.nl/voorstelling/33049/new-purple-celebration-the-music-of-prince","https://hedon-zwolle.nl/voorstelling/32962/big-sleep"],
"Helling":["https://dehelling.nl/agenda/john-coffey-support-eyesores-09-10-2026/","https://dehelling.nl/agenda/jhariah-support-plonki-14-10-2026/"],
"Neushoorn extra":[
"https://www.neushoorn.nl/events/wodan-boys", "https://www.neushoorn.nl/events/monkeyjam-okt"
],
"Patronaat":["https://patronaat.nl/event/yuna-10-10-26/","https://patronaat.nl/event/slodde-vos-16-10-26/"],
"Effenaar":["https://www.effenaar.nl/agenda/alpha-wolf","https://www.effenaar.nl/agenda/john-illsley-dire-straits"],
}
for key, urls in URLS.items():
    print("\n#####",key,flush=True)
    for url in urls:
        try:
            html, final, status=get(url);p=Links();p.feed(html)
            matched=[(h,cls) for h,cls in p.hrefs if any(t in h.lower() for t in ("page/","page=","volgende","next","load"))]
            script_src=re.findall(r'<script[^>]*src=["\x27]([^"\x27]+)',html,re.I)
            h1=re.search(r"<h1[^>]*>(.*?)</h1>",html,re.S|re.I)
            title=re.search(r"<title[^>]*>(.*?)</title>",html,re.S|re.I)
            print("PAGE",url,"FINAL",final,"STATUS",status,"BYTES",len(html),"TITLE",re.sub(r"<[^>]+>"," ",h1.group(1) if h1 else (title.group(1) if title else ""))[:100],"DATE",_detail_date_time(html),"TEXTDATE",date_from_text(re.sub(r"<[^>]+>"," ",html[:45000])),"LINKS",len(p.hrefs),"PAGELINKS",matched[:13],"SCRIPTS",script_src[:8],flush=True)
            if key in ("Hedon","Helling"):
                name,city=("Hedon","Zwolle") if key=="Hedon" else ("De Helling","Utrecht")
                print("PARSED",parse_event(html,url,name,city),flush=True)
                txt=re.sub(r"\s+"," ",re.sub("<[^>]*>"," ",html))
                print("CONTENT",txt[:850],flush=True)
            if key=="Neushoorn":
                print("EVENTLINKS",len(find_site_event_urls(html,"https://www.neushoorn.nl","/events/")),"MARKERS",[(t,html.count(t)) for t in ("page/2","?page=2","pagination","loadMore","nextPage","100")],flush=True)
                for term in ("page/2","?page=2","pagination","pageNumber","totalPages"):
                    m=re.search(re.escape(term),html,re.I)
                    if m: print("SNIPPET",term,re.sub(r"\s+"," ",html[max(0,m.start()-150):m.end()+220])[:390],flush=True)
            if key=="Tivoli":
                print("EVENTLINKS",len(find_site_event_urls(html,"https://www.tivolivredenburg.nl","/agenda/")),flush=True)
        except Exception as exc:print("ERROR",url,repr(exc),flush=True)
