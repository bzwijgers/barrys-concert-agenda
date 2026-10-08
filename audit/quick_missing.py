"""Fast live parser checks for concrete concerts absent from the published feed."""
from scrapers.common import download_page_retry,_detail_date_time,_detail_title
from scrapers.new_venues import parse_event, page_text
import re
urls=[
 ("De Helling","Utrecht","https://dehelling.nl/agenda/high-fade-23-04-2027/"),
 ("De Helling","Utrecht","https://dehelling.nl/agenda/kruidkoek-joost-oomen-support-tim-koehoorn-23-10-2026/"),
 ("De Helling","Utrecht","https://dehelling.nl/agenda/freax-07-11-2026/"),
 ("Effenaar","Eindhoven","https://www.effenaar.nl/agenda/john-illsley-dire-straits"),
 ("Effenaar","Eindhoven","https://www.effenaar.nl/agenda/alpha-wolf"),
]
for name,city,url in urls:
    try:
        html=download_page_retry(url,attempts=2)
        print("\nURL",url,"LEN",len(html),flush=True)
        print("DETAIL TITLE",_detail_title(html),"DATE",_detail_date_time(html),flush=True)
        if name=="De Helling":
            print("PARSED",parse_event(html,url,name,city),flush=True)
            clean=page_text(html)
            print("TEXT HEAD",clean[:2000],flush=True)
            for term in ("rave","afrobeats","fanparty","disco","clubnacht","nachtclub","clubnight"):
                for m in list(re.finditer(term,html,re.I))[:2]:
                    print("FILTER FOUND",term,"CONTEXT",html[max(0,m.start()-100):m.end()+110],flush=True)
    except Exception as e:
        print("ERROR",url,repr(e),flush=True)
