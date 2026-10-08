"""Probe exact Metropool infinite-scroll endpoint found in first-party HTML."""
from urllib.request import Request,urlopen
from urllib.parse import urljoin
from html.parser import HTMLParser
import re
base="https://metropool.nl/"
class P(HTMLParser):
 def __init__(self):super().__init__();self.links=[]
 def handle_starttag(self,t,attrs):
  if t=="a" and dict(attrs).get("href"):self.links.append(urljoin(base,dict(attrs)["href"]))
for n in range(0,7):
 url=base+f"mvc/event/partial?pNumber={n}&keyword=&genre=&tag=&type=&StartDate=&EndDate=&locatie=&label=&newAnnounced=False"
 try:
  with urlopen(Request(url,headers={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/154 Safari/537.36","X-Requested-With":"XMLHttpRequest","Accept":"text/html, */*;q=0.01"}),timeout=15) as r:html=r.read().decode("utf-8","replace");status=r.status
  p=P();p.feed(html)
  links=list(dict.fromkeys(x for x in p.links if "/agenda/" in x and "/agenda/"!=x[-8:]))
  print("AJAX",n,"status",status,"html",len(html),"event_links",len(links),"sample",links[:6],flush=True)
 except Exception as e:print("AJAX",n,"ERROR",str(e)[:160],flush=True)
url=base+"sitemap.xml"
with urlopen(Request(url,headers={"User-Agent":"Mozilla/5.0"}),timeout=15) as r:html=r.read().decode("utf-8","replace")
all_urls=re.findall(r"<loc>\s*([^<]+)</loc>",html,re.I)
events=[x for x in all_urls if "/agenda/" in x]
print("SITEMAP",len(all_urls),"event_urls",len(events),"sample",events[:8],flush=True)
