"""Inspect title/date extraction for live music venue regressions."""
from concurrent.futures import ThreadPoolExecutor
from diagnostics.new_venues_candidate import Page, date_from_text, page_text, parse_event, discover
from scrapers.common import download_page_retry

DETAILS=[
("Doornroosje","https://www.doornroosje.nl/event/ao-2/","Nijmegen"),
("Doornroosje","https://www.doornroosje.nl/event/kingongolo-kiniata/","Nijmegen"),
("Doornroosje","https://www.doornroosje.nl/event/trockener-kecks/","Nijmegen"),
("Doornroosje","https://www.doornroosje.nl/event/dressed-like-boys-2/","Nijmegen"),
("Doornroosje","https://www.doornroosje.nl/event/sharp-pins/","Nijmegen"),
("Hedon","https://hedon-zwolle.nl/voorstelling/33084/escah","Zwolle"),
("Metropool","https://metropool.nl/agenda/khemmis","Hengelo"),
("Metropool","https://metropool.nl/agenda/rowwen-heze","Hengelo"),
]
def f(x):
 name,url,city=x
 try:
  html=download_page_retry(url,attempts=2)
  p=Page();p.feed(html)
  desc=p.meta.get("og:description","") or p.meta.get("description","")
  title=p.meta.get("og:title","")
  raw=page_text(html)
  dates=[(str(t),date_from_text(str(t))) for t in (desc,title,url,raw[:2800])]
  vals=(name,url,"og_title",title[:140],"og_description",desc[:180],
        "dates",dates,"times",p.times[:6],"actual",parse_event(html,url,name,city),
        "body_tail",raw[-550:][:180])
  return repr(vals)
 except Exception as e:return repr((name,url,"error",str(e)[:200]))
if __name__=="__main__":
 with ThreadPoolExecutor(max_workers=6) as ex:
  for value in ex.map(f,DETAILS):print(value,flush=True)
 html=download_page_retry("https://www.dynamo-eindhoven.nl/evenementen/",attempts=2)
 p=Page();p.feed(html)
 print("DYNAMO ANCHORS",len(p.anchors),"event-containing",
       [u for u in p.anchors if "/evenement/" in u][:12],flush=True)
 print("DYNAMO DISCOVER",discover(html,"https://www.dynamo-eindhoven.nl/evenementen/","/evenement/")[:3])
