"""Find the complete Bibelot official programme feed and pagination mechanism."""
from html import unescape
from urllib.parse import urljoin
from urllib.request import Request, urlopen
import re

BASE = "https://bibelot.net/programma/"
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/131.0 Safari/537.36"}
PATTERN = re.compile(r"api|ajax|wp-json|load.?more|pagination|page=|event|programma|fetch\(|graphql|filter", re.I)

def download(url):
    request = Request(url,headers=HEADERS)
    with urlopen(request,timeout=14) as r:
        return r.read(2_000_000).decode("utf-8","replace")

def main():
    page=download(BASE)
    print("BIBELOT HTML BYTES:",len(page),flush=True)
    print("OFFICIAL EVENT LINK COUNT:",len(set(re.findall(
        r'href=["\\x27](https?://bibelot.net/programma/[^"\\x27]+)',page,re.I
    ))),flush=True)
    for needle in ("97 van de", "evenementen", "load-more", "wp-json", "event-list", "filter"):
        i=page.lower().find(needle.lower())
        if i>=0:print("HTML",needle,repr(page[max(0,i-300):i+650]),flush=True)
    scripts=re.findall(r"""<script[^>]+src\s*=\s*["']([^"']+)""",page,re.I)
    print("SCRIPT COUNT",len(scripts),flush=True)
    for source in scripts[-18:]:
        url=urljoin(BASE,unescape(source))
        if any(skip in url for skip in ("jquery","recaptcha","google","gtm","maps","swiper")):continue
        try:
            js=download(url)
            matches=list(PATTERN.finditer(js))
            print("SCRIPT",url,"bytes",len(js),"matches",len(matches),flush=True)
            for match in matches[:15]:
                print("JS",repr(js[max(0,match.start()-130):match.end()+230]),flush=True)
        except Exception as exc:
            print("JS FAILED",url,repr(exc),flush=True)

if __name__=="__main__":
    main()
