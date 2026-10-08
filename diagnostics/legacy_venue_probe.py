"""Find concrete upstream data sources for Gebouw-T, dB's, Amare and Bolwerk."""
import re
from html import unescape
from urllib.request import Request, urlopen, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError
from html.parser import HTMLParser
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor

URLS=[
"https://gebouw-t.nl/agenda/","https://gebouw-t.nl/sitemap_index.xml",
"https://gebouw-t.nl/wp-sitemap.xml","https://gebouw-t.nl/event-sitemap.xml",
"https://gebouw-t.nl/agenda/sega-guitar-now-featuring-leif-de-leeuw-band/",
"https://dbstudio.nl/events/categorie/alles/concert/lijst/","https://dbstudio.nl/events/?post_type=tribe_events",
"https://dbstudio.nl/wp-sitemap.xml",
"https://www.amare.nl/nl/nl-pop-11kr","https://www.amare.nl/nl/agenda","https://www.amare.nl/nl/agenda/nits-j436",
"https://www.podiuminfo.nl/podium/44/concerten/Het-Bolwerk/Sneek/",
"https://ontdekpoort.nl/",
]
class Anchors(HTMLParser):
 def __init__(self):super().__init__();self.hrefs=[]
 def handle_starttag(self,tag,attrs):
  if tag=="a":
   u=dict(attrs).get("href")
   if u:self.hrefs.append(u)
class NoRedirect(HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):return None
def one(url):
 try:
  q=Request(url,headers={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/154 Safari/537.36","Accept-Language":"nl-NL,nl;q=0.9","Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"})
  try:
   r=build_opener(NoRedirect).open(q,timeout=12)
   text=r.read().decode("utf-8","replace");status=r.status;location=r.url
  except HTTPError as e:
   if e.code in (301,302,303,307,308):
    return f"URL {url} -> HTTP {e.code}, location={e.headers.get('Location')}, cookie={str(e.headers.get('Set-Cookie'))[:200]}"
   return f"URL {url} -> HTTP {e.code}"
  p=Anchors();p.feed(text)
  tokens=re.findall(r'https?:(?:\\?/){2}[^"\'<>\s]{15,120}',text,re.I)
  seen=[]
  for x in tokens:
   if any(t in x for t in ("/agenda/","/events/","/evenement/","-sitemap.xml","/voorstelling/")) and x not in seen:seen.append(x)
  hrefs=[urljoin(location,unescape(x)) for x in p.hrefs if any(k in x for k in ("/agenda/","/events/","/evenement/","/show/","/voorstelling/","/artist/"))]
  snippets=[]
  for key in ("marble-sounds","sega-guitar","legends-of-rock","tribe-events-calendar","event-title-link","Mister & Mrs","The Dublin Legends"):
   pos=text.lower().find(key.lower())
   if pos>=0:snippets.append((key,text[max(0,pos-190):pos+210].replace("\n"," ")[:400]))
  return f"URL {url} -> HTTP {status}, size {len(text)}, anchors {len(p.hrefs)}; event hrefs: {hrefs[:9]}; xml tags: {re.findall(r'<loc>.*?</loc>',text)[:7]}; raw links: {seen[:7]}; snippets: {snippets[:4]}"
 except Exception as e:return f"URL {url} ERROR {repr(e)[:250]}"
if __name__=="__main__":
 with ThreadPoolExecutor(max_workers=7) as ex:
  for x in ex.map(one,URLS):print(x,flush=True)
