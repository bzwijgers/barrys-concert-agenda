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

# Check the site's public Prismic content API, which can provide the complete
# event catalogue rather than a single server-rendered six-event selection.
from urllib.parse import urlencode
from collections import Counter
api_url = "https://bird-rotterdam.cdn.prismic.io/api/v2"
print("\\n==== PRISMIC API ====",flush=True)
try:
    raw = fetch(api_url)
    api = json.loads(raw)
    print("API KEYS",list(api.keys()),flush=True)
    print("REFS",[(x.get("ref"),x.get("isMasterRef")) for x in api.get("refs",[])[:4]],flush=True)
    print("TYPES",api.get("types"),flush=True)
    ref = next(x["ref"] for x in api["refs"] if x.get("isMasterRef"))
    endpoint = api.get("forms",{}).get("everything",{}).get("action","https://bird-rotterdam.cdn.prismic.io/api/v2/documents/search")
    for query in (None,'[[at(document.type,"event")]]','[[at(document.type,"events")]]','[[at(document.type,"agenda")]]'):
        args={"ref":ref,"pageSize":100,"page":1}
        if query: args["q"]=query
        url=endpoint+"?"+urlencode(args)
        print("QUERY",query,flush=True)
        try:
            data=json.loads(fetch(url))
            print("RESULTS",data.get("results_size"),"TOTAL",data.get("total_results_size"),"PAGES",data.get("total_pages"),"NEXT",data.get("next_page"),flush=True)
            print("TYPES",Counter(x.get("type") for x in data.get("results",[])),flush=True)
            for x in data.get("results",[])[:3]:
                print("SAMPLE",{"type":x.get("type"),"uid":x.get("uid"),"url":x.get("url"),"data_keys":list(x.get("data",{}).keys()),"data_sample":{k:str(v)[:260] for k,v in x.get("data",{}).items() if any(t in k for t in ("date","start","type","cat","title","time","name"))}},flush=True)
        except Exception as exc:print("QUERY ERROR",repr(exc),flush=True)
except Exception as exc:
    print("API ERROR",repr(exc),flush=True)

for q in (
  '[[at(document.type,"agenda")][date.after(my.agenda.event_date, "2026-10-07")]]',
  '[[date.after(my.agenda.event_date, "2026-10-07")]]',
  '[[at(document.type,"agenda")][date.after(my.agenda.event_date, "2026-10-07T00:00:00+0000")]]'
):
    print("FUTURE QUERY",q,flush=True)
    try:
        raw=fetch(endpoint+"?"+urlencode({"ref":ref,"pageSize":100,"page":1,"q":q}))
        data=json.loads(raw)
        print("FUTURE TOTAL",data.get("total_results_size"),"PAGES",data.get("total_pages"),flush=True)
        events=data.get("results",[])
        print("FUTURE SAMPLE",[(x.get("uid"),x.get("data",{}).get("event_date"),[a.get("main_category",{}).get("uid") for a in x.get("data",{}).get("main_categories",[])]) for x in events[:25]],flush=True)
    except Exception as e:print("FUTURE ERROR",repr(e),flush=True)
