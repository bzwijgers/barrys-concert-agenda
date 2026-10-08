"""Inspect only publicly advertised TicketSwap sitemap/robots metadata."""
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import re
for host in ("https://www.ticketswap.com", "https://www.ticketswap.nl"):
    for path in ("/robots.txt", "/sitemap.xml"):
        url = host + path
        try:
            req=Request(url,headers={"User-Agent":"Mozilla/5.0 (compatible; BarryConcertAgenda/1.0)"})
            with urlopen(req,timeout=12) as resp:
                raw=resp.read(1500000).decode("utf-8","replace")
                print("URL",url,"status",resp.status,"len",len(raw),
                      "type",resp.headers.get("content-type"),flush=True)
                if path.endswith("robots.txt"):
                    print("ROBOTS",raw[:5000],flush=True)
                else:
                    urls=re.findall(r"<loc>(.*?)</loc>",raw,re.I)
                    print("SITEMAP URLS",len(urls),"sample",urls[:25],flush=True)
        except Exception as e:
            print("FAIL",url,repr(e)[:180],flush=True)
