"""Diagnose BIRD's live agenda from the same GitHub Actions environment as the scraper."""
from urllib.request import Request, urlopen
from urllib.parse import urljoin
from html import unescape
from html.parser import HTMLParser
import re
import json

class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.a = []
        self.scripts = []
        self.forms = []
    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == "a": self.a.append(d)
        if tag == "script" and d.get("src"): self.scripts.append(d.get("src"))
        if tag == "form": self.forms.append(d)

def fetch(url):
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; ConcertAgendaCheck/1.0)", "Accept": "text/html,application/xhtml+xml"})
    with urlopen(req, timeout=25) as r:
        content = r.read().decode("utf-8", errors="replace")
        print("URL",url,"FINAL",r.url,"STATUS",r.status,"BYTES",len(content),"TYPE",r.headers.get("Content-Type"),flush=True)
        return content

for url in [
    "https://bird-rotterdam.nl/agenda/",
    "https://bird-rotterdam.nl/concerts/",
    "https://bird-rotterdam.nl/agenda/?category=live",
    "https://bird-rotterdam.nl/agenda/?month=11-2026",
]:
    print("\n====",url,"====",flush=True)
    try: html=fetch(url)
    except Exception as e:
        print("FETCH ERROR",repr(e),flush=True)
        continue
    p=Links();p.feed(html)
    events=[]
    for a in p.a:
        href=a.get("href","")
        if "/event/" in href:
            full=urljoin(url,unescape(href)).split("#")[0]
            if full not in events:events.append(full)
    print("ANCHORS",len(p.a),"EVENTS",len(events),"SCRIPTS",len(p.scripts),flush=True)
    print("EVENT URLS",json.dumps(events[:70],ensure_ascii=False),flush=True)
    print("FORM",p.forms[:6],flush=True)
    print("SCRIPT",p.scripts[:15],flush=True)
    print("Markers",[(k,len(list(re.finditer(re.escape(k),html,re.I)))) for k in ("live","filter","month","page","load more","pagination","prismic","__NEXT_DATA__","__NUXT__","data-category","event_type")],flush=True)
    for term in ("filter", "Live", "pagination", "loadMore", "agenda-filter", "nextPage", "month=", "__NEXT_DATA__"):
        matches=list(re.finditer(re.escape(term),html,re.I))
        print("SNIPPETS",term,[re.sub(r"\\s+"," ",html[max(0,m.start()-180):m.end()+220])[:400] for m in matches[:3]],flush=True)
