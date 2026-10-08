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
                    event_sitemaps = [link for link in urls if re.search(r"/sitemap/event_\\d+\\.xml", link)]
                    print("EVENT_SITEMAPS",len(event_sitemaps),flush=True)
                    if host.endswith(".com") and event_sitemaps:
                        for sample_url in [event_sitemaps[0], event_sitemaps[-1]]:
                            try:
                                request = Request(sample_url,headers={"User-Agent":"Mozilla/5.0 (compatible; BarryConcertAgenda/1.0)"})
                                with urlopen(request,timeout=18) as result:
                                    document = result.read(8_000_000).decode("utf-8","replace")
                                found = re.findall(r"<loc>(.*?)</loc>", document)
                                print("EVENT PAGE SAMPLE",sample_url,"bytes",len(document),"event_urls",len(found),
                                      "sample",found[:4], "excelsior",sum("excelsior" in x.lower() for x in found),flush=True)
                            except Exception as exc:
                                print("EVENT PAGE ERROR",sample_url,repr(exc),flush=True)

        except Exception as e:
            print("FAIL",url,repr(e)[:180],flush=True)
