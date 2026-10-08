"""Check whether public search engines expose actual TicketSwap event URLs.

No private account, credentials, or cookies. Diagnostic only.
"""
from html import unescape
from urllib.parse import quote_plus, unquote, urlparse, parse_qs
from urllib.request import Request, urlopen
import re

QUERIES = (
    '"Robert Jon" "Utrecht" "2026-10-10" site:ticketswap.nl/concert-tickets',
    '"30 Jaar Excelsior Recordings" "2026-12-27" site:ticketswap.nl/concert-tickets',
)
ENDPOINTS = (
    ("google", "https://www.google.com/search?q="),
    ("bing", "https://www.bing.com/search?q="),
    ("ddg", "https://html.duckduckgo.com/html/?q="),
)
REGEX = re.compile(r"https?://(?:www\.)?ticketswap\.(?:nl|com)/concert-tickets/[A-Za-z0-9/%._~-]+", re.I)

def check():
    for query in QUERIES:
        print("QUERY", query, flush=True)
        for name, base in ENDPOINTS:
            try:
                req = Request(base + quote_plus(query), headers={
                    "User-Agent": "Mozilla/5.0 (Linux; Android 15) AppleWebKit/537.36 Chrome/131.0 Mobile Safari/537.36",
                    "Accept-Language": "nl-NL,nl;q=0.9,en;q=0.8",
                })
                with urlopen(req, timeout=12) as resp:
                    html = resp.read(1_200_000).decode("utf-8", "replace")
                    code = resp.status
                matches = set()
                for text in (html, unescape(html), unquote(unescape(html))):
                    matches.update(REGEX.findall(text))
                print(name, "http", code, "bytes", len(html),
                      "candidate_links", len(matches), repr(list(matches)[:3]), flush=True)
            except Exception as exc:
                print(name, type(exc).__name__, str(exc)[:110], flush=True)

if __name__ == "__main__":
    check()
