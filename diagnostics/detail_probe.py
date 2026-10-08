"""Inspect live event detail pages to build defensible venue-specific parsers."""
from concurrent.futures import ThreadPoolExecutor
from html import unescape
from html.parser import HTMLParser
from urllib.request import Request, urlopen
import re
from urllib.error import HTTPError

URLS = {
 "Helling": "https://dehelling.nl/agenda/the-magic-numbers-12-10-2026/",
 "Klokgebouw": "https://www.klokgebouw.nl/agenda/danny-vera-2026",
 "Dynamo": "https://www.dynamo-eindhoven.nl/evenement/the-hara/",
 "Doornroosje": "https://www.doornroosje.nl/event/ao-2/",
 "BIRD": "https://bird-rotterdam.nl/event/brothers-moving-10-10-2026/",
 "Amare": "https://amare.nl/nl/agenda",
 "Metropool": "https://metropool.nl/agenda/khemmis",
 "Hedon": "https://hedon-zwolle.nl/voorstelling/33084/escah",
 "SPOT": "https://www.spotgroningen.nl/programma/elmer/",
 "Neushoorn": "https://www.neushoorn.nl/events/wodan-boys",
 "Bolwerk": "https://hetbolwerk.nl/",
 "Gebouw-T": "https://gebouw-t.nl/agenda/",
 "dBs": "https://dbstudio.nl/events/categorie/alles/concert/lijst/",
}
class Analyzer(HTMLParser):
 def __init__(self):
  super().__init__();self.titles=[];self.times=[];self.metas=[];self.anchor=[];self._in_h1=False;self._in_time=False
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag=="h1":self._in_h1=True
  if tag=="time":self._in_time=True;self.times.append(a.get("datetime",""))
  if tag=="meta" and (a.get("property") or a.get("name")):
   k=a.get("property",a.get("name",""))
   if any(x in k.lower() for x in ("date","time","title","description","event")):self.metas.append((k,a.get("content","")[:140]))
 def handle_endtag(self,tag):
  if tag=="h1":self._in_h1=False
  if tag=="time":self._in_time=False
 def handle_data(self,data):
  if self._in_h1:self.titles.append(data.strip())
  if self._in_time:self.times.append(data.strip())
def one(pair):
 name,url=pair
 try:
  r=urlopen(Request(url,headers={"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/154 Safari/537.36","Accept-Language":"nl-NL,nl;q=0.9"}),timeout=16)
  html=r.read().decode("utf-8","replace");url=r.url
  p=Analyzer();p.feed(html)
  ld=re.findall(r'''<script[^>]*type=["']application/ld\\+json["'][^>]*>(.*?)</script>''',html,re.I|re.S)
  dates=re.findall(r'''(?:startDate|dateTime|datetime)["'\\s:=]+(20\\d\\d.{0,30})''',html,re.I)
  date_text=re.findall(r'''(?:ma|di|wo|do|vr|za|zo|Mon|Tue|Wed|Thu|Fri|Sat|Sun)[a-z]*[., ]+\\d{1,2}[^<\\n]{0,55}''',html,re.I)
  h1=" ".join(x for x in p.titles if x)
  text=unescape(re.sub(r'<[^>]+>',' ',re.sub(r'<(script|style)[^>]*>.*?</\\1>',' ',html,flags=re.S|re.I)))
  text=re.sub(r'\\s+',' ',text)
  position=text.lower().find(h1.lower()[:30]) if h1 else 0
  snippet=text[max(0,position):position+850]
  return repr(dict(name=name,url=url,size=len(html),title=h1[:140],times=p.times[:10],metas=p.metas[:10],startDates=dates[:4],dateText=date_text[:4],ld=[x[:360] for x in ld[:2]],snippet=snippet,website_signals={s:html.count(s) for s in ("agenda","event","wp-json","__NEXT_DATA__","graphql","eventbrite","data-date")} ))
 except Exception as e: return repr(dict(name=name,url=url,error=str(e)[:300]))
if __name__=="__main__":
 with ThreadPoolExecutor(max_workers=5) as pool:
  for x in pool.map(one,URLS.items()):print(x,flush=True)
