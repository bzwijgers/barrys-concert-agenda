"""Inspect De Pul's official load-more implementation without publishing partial data."""
import re
from html import unescape
from urllib.parse import urljoin
from urllib.request import Request, urlopen

BASE = "https://www.livepul.com/agenda/"
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/131.0 Safari/537.36"}
KEYWORDS = re.compile(r"ajax|load.?more|meer laden|pagina|pagination|page.?num|offset|wp-json|endpoint|fetch\(", re.I)


def download(url):
    with urlopen(Request(url, headers=HEADERS), timeout=14) as response:
        return response.read(2_000_000).decode("utf-8", "replace")


def main():
    html = download(BASE)
    for offset in (0, 20):
        endpoint = (
            "https://www.livepul.com/query.php"
            "?source=agenda&agenda_page=true&month=all&search=false"
            "&amount_of_events_already_shown=" + str(offset)
        )
        try:
            import json
            data = json.loads(download(endpoint))
            output = data.get("output", "")
            print("PUL_API", offset, "output_len", len(output),
                  "show_more_possible", data.get("show_more_possible"),
                  "event_cards", output.count("agenda-event--actual-event"),
                  "event_links", re.findall(r'href=["\\x27]([^"\\x27]+)', output)[:5], flush=True)
        except Exception as error:
            print("PUL_API_ERROR", offset, repr(error), flush=True)
    print("PUL_HTML_BYTES", len(html), flush=True)
    for match in list(KEYWORDS.finditer(html))[:45]:
        print("PAGE_HINT", repr(unescape(html[max(0, match.start()-90):match.end()+180])), flush=True)

    scripts = re.findall(r"""<script[^>]+src\s*=\s*["']([^"']+)""", html, re.I)
    print("SCRIPT_COUNT", len(scripts), flush=True)
    hints = [urljoin(BASE, unescape(s)) for s in scripts
             if "swiper" not in s.lower()]
    print("PAGE_SCRIPT_URLS", hints, flush=True)
    # Inspect each site's own scripts, excluding the external slider library.
    for url in hints[:6]:
        try:
            js = download(url)
            if "site.min.js" in url:
                for needle in ('/query.php?', 'agenda-events__show-more', 'show_more_possible'):
                    position = js.find(needle)
                    print("PUL_SCRIPT_CONTEXT", needle, repr(js[max(0,position-2800):position+1000]) if position >= 0 else "NOT FOUND", flush=True)
            matches = list(KEYWORDS.finditer(js))
            print("SCRIPT", url, "bytes", len(js), "hits", len(matches), flush=True)
            for match in matches[:12]:
                print("JS_HINT", repr(js[max(0,match.start()-130):match.end()+220]), flush=True)
        except Exception as error:
            print("SCRIPT_ERROR", url, str(error)[:170], flush=True)


if __name__ == "__main__":
    main()
