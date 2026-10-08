"""Inspect pagination and complete official programme discovery for Metropool."""
from urllib.request import Request,urlopen
from html.parser import HTMLParser
import re
from html import unescape
from urllib.parse import urljoin
URLS=[
"https://metropool.nl/agenda",
"https://metropool.nl/agenda?page=2",
"https://metropool.nl/agenda?page=3",
"https://metropool.nl/agenda?offset=10",
"https://metropool.nl/sitemap.xml",
"https://metropool.nl/robots.txt",
"https://metropool.nl/sitemap_index.xml",
"https://metropool.nl/agenda/2",
]
class Linker(HTMLParser):
 def __init__(self):super().__init__();self.hrefs=[]
 def handle_starttag(self,t,a):
  d=dict(a)
  if t=="a" and d.get("href"):self.hrefs.append(d["href"])
for url in URLS:
 try:
  with urlopen(Request(url,headers={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/154 Safari/537.36"}),timeout=12) as resp: html=resp.read().decode("utf-8","replace");real=resp.url
  p=Linker();p.feed(html)
  links=list(dict.fromkeys([urljoin(real,u) for u in p.hrefs if "/agenda/" in u and not any(k in u for k in ["?","/2/"])]))
  sitemap=re.findall(r'<loc>(.*?)</loc>',html,re.I)
  scripts=re.findall(r'<script[^>]+src=["\x27]([^"\x27]+)',html,re.I)
  sign={x:len(re.findall(x,html,re.I)) for x in ("load.more","loadmore","pagination","infinite","endpoints","graphql","fetch\\(","api/events","api/agenda","data-page","data-url","next-page")}
  print(url,"status200 len",len(html),"events",len(links),"sample",links[:8],"loc",sitemap[:8],"scripts",scripts[:5],"signals",sign,flush=True)
  for m in re.finditer("load.more|loadmore|pagination|infinite|axios|fetch\\(",html,re.I):
   pos=m.start()
   if pos>10000:
    print("  CONTEXT",html[pos-160:pos+240].replace("\n"," ")[:400])
    if pos>len(html)-20000:break
 except Exception as e:print(url,"ERROR",str(e)[:160],flush=True)
