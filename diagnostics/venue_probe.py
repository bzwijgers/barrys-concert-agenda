"""Diagnostic: sample actual HTML and link shapes from live venue websites."""
import concurrent.futures
import re
from html import unescape
from urllib.parse import urljoin, urlsplit
from urllib.request import urlopen, Request

SITES = {
 "Helling":"https://dehelling.nl/agenda/",
 "Klokgebouw":"https://www.klokgebouw.nl/agenda",
 "Dynamo":"https://www.dynamo-eindhoven.nl/activiteiten/",
 "Doornroosje":"https://www.doornroosje.nl/",
 "BIRD":"https://bird-rotterdam.nl/agenda/",
 "Amare":"https://www.amare.nl/nl/agenda",
 "Metropool":"https://metropool.nl/agenda",
 "Hedon":"https://hedon-zwolle.nl/",
 "SPOT":"https://www.spotgroningen.nl/programma/?genre=muziek",
 "Neushoorn":"https://www.neushoorn.nl/programma",
 "Bolwerk":"https://www.hetbolwerk.nl/",
 "GebouwT":"https://gebouw-t.nl/agenda/",
 "dBs":"https://www.dbstudio.nl/events/categorie/alles/concert/lijst/",
 "Bibelot":"https://bibelot.net/programma/",
 "DePul":"https://www.livepul.com/agenda/",
 "DeBosuil":"https://www.debosuil.nl/programma/",
}

def probe(entry):
 name, url=entry
 try:
  req=Request(url,headers={"User-Agent":"Mozilla/5.0 (compatible; ConcertAgenda/1.0)","Accept":"text/html","Accept-Language":"nl-NL,nl;q=0.9"})
  with urlopen(req,timeout=16) as r:
   raw=r.read().decode("utf-8","replace")
   final=r.url; status=r.status
  anchors=re.findall(r'''<a\b[^>]*href\s*=\s*["']([^"']+)["']''',raw,re.I|re.S)
  links=[]
  for href in anchors:
   target=urljoin(final,unescape(href))
   if urlsplit(target).hostname==urlsplit(final).hostname:
    if target not in links:links.append(target)
  scripts=re.findall(r'''<script[^>]*type=["']application/ld\+json["'][^>]*>(.*?)</script>''',raw,re.I|re.S)
  events=re.findall(r'''"@type"\s*:\s*"[^"]*(?:Event|MusicEvent)[^"]*"''',raw,re.I)
  dates=re.findall(r'''(?:startDate|dateTime|datetime)["'\s:=]+(20\d\d[-/]\d\d[-/]\d\d[^"<\s,}]*)''',raw,re.I)
  interesting=[x for x in links if not any(z in x for z in ("privacy","contact","nieuws","tickets","faq","terms","/info","/over-"))]
  if name == "DePul":
   # Inspect the currently unknown "Meer laden" endpoint without guessing
   # that the first HTML page is the full calendar.
   suspects = re.findall(
    r'''[^\\s"'<>]{0,90}(?:ajax|loadmore|load_more|load-more|wp-json|endpoint|pagination|offset|page=)[^\\s"'<>]{0,160}''',
    raw, re.I
   )
   print("DEPUL PAGINATION HINTS:",repr(list(dict.fromkeys(suspects))[:35]),flush=True)

  return f"\n=== {name} | HTTP {status} | len={len(raw)} | final={final} | anchor={len(links)} | ld={len(scripts)} eventtokens={len(events)} dates={len(dates)} ===\n"+ "\n".join(interesting[:22])+ "\nDATES "+repr(dates[:5])+"\nLD "+repr([x[:210] for x in scripts[:2]])
 except Exception as e:
  return f"\n=== {name} ERROR {type(e).__name__}: {str(e)[:200]} ==="

if __name__=="__main__":
 with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
  for result in ex.map(probe,SITES.items()):
   print(result,flush=True)
