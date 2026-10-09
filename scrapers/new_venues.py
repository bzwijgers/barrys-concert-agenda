"""Venue-specific concert scrapers, using official event links and detail pages.

Candidate tested independently before inclusion in the production feed.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta
from html import unescape
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit
from zoneinfo import ZoneInfo
import json
import re

from .common import download_page_retry, normalize_url

VENUES = {
    "De Helling": ("https://dehelling.nl/agenda/", "/agenda/", "Utrecht"),
    "Klokgebouw": ("https://www.klokgebouw.nl/agenda", "/agenda/", "Eindhoven"),
    "Dynamo": ("https://www.dynamo-eindhoven.nl/evenementen/", "/evenement/", "Eindhoven"),
    "Doornroosje": ("https://www.doornroosje.nl/", "/event/", "Nijmegen"),
    "BIRD": ("https://bird-rotterdam.nl/concerts/", "/event/", "Rotterdam"),
    "Metropool": ("https://metropool.nl/agenda", "/agenda/", "Hengelo"),
    "Hedon": ("https://hedon-zwolle.nl/", "/voorstelling/", "Zwolle"),
    "SPOT Groningen": ("https://www.spotgroningen.nl/programma/?genre=muziek", "/programma/", "Groningen"),
    "Neushoorn": ("https://www.neushoorn.nl/programma", "/events/", "Leeuwarden"),
    # Official Bibelot programme currently exposes its complete 97-event listing.
    # The discovery floor below rejects accidentally truncated output.
    "Bibelot": ("https://bibelot.net/programma/", "/programma/", "Dordrecht"),
    "De Pul": ("https://www.livepul.com/agenda/", "/agenda/", "Uden"),
    "De Bosuil": ("https://www.debosuil.nl/programma/", "/programma/", "Weert"),
}

# All previously pending venues are live after independent agenda checks.
CANDIDATE_VENUES = {}

MONTHS = {
    "jan":1,"januari":1,"january":1,"feb":2,"februari":2,"february":2,
    "mrt":3,"maa":3,"maart":3,"mar":3,"march":3,"apr":4,"april":4,
    "mei":5,"may":5,"jun":6,"juni":6,"june":6,"jul":7,"juli":7,"july":7,
    "aug":8,"augustus":8,"august":8,"sep":9,"september":9,
    "okt":10,"oct":10,"oktober":10,"october":10,"nov":11,"november":11,
    "dec":12,"december":12,
}

class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.anchors = []
        self.meta = {}
        self.times = []
        self.headings = []
        self._h1 = False

    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if tag == "a" and a.get("href"): self.anchors.append(a["href"])
        if tag == "meta":
            k=a.get("property") or a.get("name")
            if k: self.meta[k.lower()] = a.get("content","")
        if tag == "time" and a.get("datetime"): self.times.append(a["datetime"])
        if tag == "h1": self._h1 = True

    def handle_endtag(self, tag):
        if tag == "h1": self._h1 = False

    def handle_data(self, value):
        if self._h1 and value.strip(): self.headings.append(value.strip())

def page_text(html):
    no_scripts=re.sub(r"<(script|style|svg)\b[^>]*>.*?</\1>", " ", html, flags=re.I|re.S)
    return re.sub(r"\s+"," ",unescape(re.sub(r"<[^>]+>"," ",no_scripts))).strip()

def discover(html, base, prefix):
    p=Page();p.feed(html)
    found=[];seen=set()
    base_host=(urlsplit(base).hostname or '').removeprefix('www.')
    for href in p.anchors:
        full=urljoin(base,unescape(href)).split("#",1)[0].split("?",1)[0].rstrip("/")
        parsed=urlsplit(full)
        if (parsed.hostname or '').removeprefix('www.')!=base_host or prefix not in parsed.path: continue
        if parsed.path.rstrip("/") in (prefix.rstrip("/"),"/agenda","/programma","/events","/evenementen"): continue
        key=normalize_url(full)
        if key not in seen:
            found.append(full);seen.add(key)
    return found

def json_events(html):
    blobs=re.findall(r'<script[^>]*type=["\x27]application/ld\+json["\x27][^>]*>(.*?)</script>',html,re.I|re.S)
    def walk(node):
        if isinstance(node,list):
            for v in node: yield from walk(v)
        if isinstance(node,dict):
            typ=node.get("@type",[])
            if isinstance(typ,str):typ=[typ]
            if any(t in ("Event","MusicEvent") or t.endswith("Event") for t in typ):
                yield node
            for k,v in node.items():
                if isinstance(v,(list,dict)):yield from walk(v)
    for blob in blobs:
        try: yield from walk(json.loads(unescape(blob)))
        except (ValueError,TypeError):pass

def iso_date_time(s):
    if not s:return None
    try:
        v=str(s).strip().replace("Z","+00:00")
        if re.match(r"^\d{4}-\d\d-\d\d$",v):return (date.fromisoformat(v).isoformat(),"")
        dt=datetime.fromisoformat(v)
        if dt.tzinfo:dt=dt.astimezone(ZoneInfo("Europe/Amsterdam"))
        return dt.date().isoformat(), dt.strftime("%H:%M")
    except (ValueError,TypeError):return None

def date_from_text(text):
    # Prefer an explicit year. Dates without a year use the next occurrence.
    patterns=[
        r"\b(20\d\d)[-/](\d{1,2})[-/](\d{1,2})\b",
        r"\b(\d{1,2})[-/.](\d{1,2})[-/.](20\d\d)\b",
        r"\b(\d{1,2})[-/.](\d{1,2})[-/.](\d\d)\b",
    ]
    for index,pattern in enumerate(patterns):
        match=re.search(pattern,text)
        if not match:continue
        try:
            a,b,c=map(int,match.groups())
            if index==0:return date(a,b,c).isoformat()
            return date(c if c>100 else c+2000,b,a).isoformat()
        except ValueError:pass
    match=re.search(r"\b(\d{1,2})[\s-]+("+"|".join(sorted(MONTHS,key=len,reverse=True))+r")[a-z]*\.?[\s,-]*(20\d\d|\x27?\d\d)?\b",text,re.I)
    if not match:
        # English month first.
        match=re.search(r"\b("+"|".join(sorted(MONTHS,key=len,reverse=True))+r")[a-z]*\.?[\s-]+(\d{1,2})(?:st|nd|rd|th)?[,]?[\s]*(20\d\d)?\b",text,re.I)
        if not match:return None
        month=MONTHS.get(match.group(1).lower()[:3])
        day=int(match.group(2));raw_year=match.group(3)
    else:
        day=int(match.group(1))
        token=match.group(2).lower()
        month=MONTHS.get(token) or MONTHS.get(token[:3])
        raw_year=match.group(3)
    if not month:return None
    year=int(raw_year.lstrip("'")) if raw_year else date.today().year
    if year<100:year+=2000
    try:
        d=date(year,month,day)
        if not raw_year and d < date.today()-timedelta(days=14):
            d=date(year+1,month,day)
        return d.isoformat()
    except ValueError:return None

def main_time(text):
    for label in ("Hoofdprogramma","Show","Aanvang","Start","Begint","Concert"):
        m=re.search(r"\b"+label+r"\s*:?\s*(\d{1,2})[:.](\d{2})",text,re.I)
        if m and int(m.group(1))<24:
            return f"{int(m.group(1)):02d}:{m.group(2)}"
    # Door times are a better fallback than a random time elsewhere on the page.
    m=re.search(r"(?:Deuren|Doors|Zaal open)\s*:?\s*(\d{1,2})[:.](\d{2})",text,re.I)
    if m and int(m.group(1))<24:return f"{int(m.group(1)):02d}:{m.group(2)}"
    return ""

def hedon_primary_date_time(html, today=None):
    """Parse the event's own date block, not dates from recommendations."""
    today = today or date.today()

    def detail(label):
        pattern = (
            r"<dt[^>]*>\s*" + re.escape(label)
            + r"\s*</dt>\s*<dd[^>]*>(.*?)</dd>"
        )
        match = re.search(pattern, html, flags=re.I | re.S)
        return page_text(match.group(1)) if match else ""

    raw_date = detail("Datum")
    match = re.search(
        r"\b(ma|di|wo|do|vr|za|zo)\s+(\d{1,2})\s+"
        r"(jan|feb|mrt|apr|mei|jun|jul|aug|sep|okt|nov|dec)",
        raw_date, flags=re.I,
    )
    if not match:
        return None

    weekdays = {"ma":0, "di":1, "wo":2, "do":3, "vr":4, "za":5, "zo":6}
    month = MONTHS.get(match.group(3).lower())
    if not month:
        return None

    possible = []
    for year in range(today.year, today.year + 4):
        try:
            candidate = date(year, month, int(match.group(2)))
        except ValueError:
            continue
        if candidate >= today and candidate.weekday() == weekdays[match.group(1).lower()]:
            possible.append(candidate)
    if not possible:
        return None

    time_text = detail("Aanvang") or detail("Zaal open")
    time_match = re.search(r"\b([01]?\d|2[0-3]):([0-5]\d)\b", time_text)
    start = (
        f"{int(time_match.group(1)):02d}:{time_match.group(2)}"
        if time_match else ""
    )
    return min(possible).isoformat(), start


def parse_event(html, url, name, city):
    parser=Page();parser.feed(html)
    meta=parser.meta
    primary=meta.get("og:title","") or meta.get("twitter:title","")
    title=unescape(primary)
    for delimiter in (" | "," // "," - Dynamo Eindhoven"," - Hedon Zwolle"," - Spot Groningen"," – De Helling"):
        if delimiter in title:title=title.split(delimiter,1)[0]
    title=title.strip() or (" ".join(parser.headings[:1]).strip())
    if name in ("Bibelot", "De Bosuil", "De Pul"):
        title = re.sub(r"\s*[|–—-]\s*(?:Bibelot|De Bosuil|De Pul)\s*$", "", title, flags=re.I).strip()
    if name=="Metropool" and " - " in title:
        title=title.split(" - ",1)[0].strip()
    if not title or title.lower() in ("agenda","programma","gerelateerde events","evenementen"):
        return None

    raw_text=page_text(html)
    description=unescape(meta.get("og:description","") or meta.get("description",""))
    # Dates in event metadata and URLs are safer than sidebar recommendations.
    primary_parts=[description,primary,url]
    parsed=None
    for event in json_events(html):
        if event.get("eventStatus","").lower().endswith("eventcancelled"):return None
        event_name=event.get("name","")
        if event_name and title[:12].lower() not in str(event_name).lower():continue
        parsed=iso_date_time(event.get("startDate"))
        if parsed:break
    # Hedon's own primary date block is yearless; derive the correct year
    # using its printed weekday rather than nearby recommended events.
    if name == "Hedon":
        hedon_result = hedon_primary_date_time(html)
        if hedon_result:
            parsed = hedon_result
    if not parsed:
        for source in primary_parts:
            found=date_from_text(source)
            if found:
                parsed=(found,"");break
    if not parsed:
        if name=="Hedon":
            match=re.search(r"\bDatum\s+(?:ma|di|wo|do|vr|za|zo)\s+(\d{1,2})\s+(jan|feb|mrt|apr|mei|jun|jul|aug|sep|okt|nov|dec)\.?\b",raw_text[:1100],re.I)
            if match:
                found=date_from_text(match.group(1)+" "+match.group(2))
                if found:parsed=(found,"")
        if not parsed:
            found=date_from_text(raw_text[:2800])
            if found:parsed=(found,"")
    if not parsed and name not in ("Doornroosje","Hedon","SPOT Groningen"):
        for source in parser.times[:8]:
            parsed=iso_date_time(source)
            if parsed:break
    if not parsed:return None
    event_date,event_time=parsed
    today=date.today().isoformat()
    if event_date<today:return None
    # Specific cancellation flags near the event heading; not generic footer text.
    start=raw_text.lower().find(title.lower()[:12])
    excerpt=raw_text[max(0,start): max(0,start)+650].lower() if start>=0 else ""
    if re.search(r"\b(?:dit evenement is afgelast|dit concert is afgelast|geannuleerd|cancelled|concert verplaatst)\b",excerpt,re.I):
        return None

    if not event_time:
        if name == "SPOT Groningen":
            # SPOT prints the show's official starting time *before* its label:
            # "20:30 start programma". This is not a door-opening time.
            # Read only the lead event block, not recommendations below.
            spot_start = re.search(
                r"\b([01]?\d|2[0-3])[:.]([0-5]\d)\s+"
                r"(?:start\s+programma|start\s+of\s+event)\b",
                raw_text[:2600], re.I,
            )
            if spot_start:
                event_time = f"{int(spot_start.group(1)):02d}:{spot_start.group(2)}"
        if name=='Doornroosje':
            body_match=re.search(r'\blocatie:\s*.+?\bdatum:\s*.+?\bzaal open:\s*\d{1,2}:\d{2}\s*uur\s*\bstart:\s*(\d{1,2}:\d{2})',raw_text[:1300],re.I)
            if body_match:event_time=body_match.group(1)
        elif name=='Metropool':
            schedule=re.search(r'\bTijdschema\b(.{0,300})',raw_text,re.I)
            if schedule:
                m=re.search(r'Aanvang (?:voorprogramma|hoofdact)\s*(\d{1,2}:\d{2})',schedule.group(1),re.I)
                if m:event_time=m.group(1)
        if not event_time:event_time=main_time(raw_text[:5000])
    venue=name
    if name=="Metropool":
        # Metropool runs three venues; keep the actual location.
        if re.search(r"\bEnschede\b",raw_text[:2200],re.I):venue="Metropool Enschede";city="Enschede"
        elif re.search(r"\bAlmelo\b",raw_text[:2200],re.I):venue="Metropool Almelo";city="Almelo"
        else:venue="Metropool Hengelo"
    if name=="Doornroosje":
        if re.search(r"\bMerleyn\b",raw_text[:2000],re.I):venue="Merleyn"
    if name=="SPOT Groningen":
        if re.search(r"(?:SPOT/)?De Oosterpoort",description+" "+raw_text[:1500],re.I):venue="De Oosterpoort"
        elif re.search("Stadsschouwburg",description+" "+raw_text[:1500],re.I):venue="Stadsschouwburg"

    # Only music performances: no non-music exhibitions, meetings or generic club nights.
    lowered=(primary+" "+description+" "+url).lower()
    # Classify nightlife/classical restrictions using the event identity, not
    # prose descriptions: an indie band may mention a rave in its biography,
    # and a rock tribute may be described as performing "klassiekers".
    identity=(primary+" "+url).lower()
    if name in ("Bibelot", "De Bosuil", "De Pul") and re.search(
        r"\b(?:40up|40.up|clubnight|clubnacht|pubquiz|spelletjes|game caf[eé]|rave|dj.set|disco|dance party|80.s classics|dans je|toen: the classics)\b",
        identity, flags=re.I,
    ):
        return None
    if name == "De Bosuil" and re.search(
        r"/programma/(?:het-feestje-2026|club-motion[^/]*|40up[^/]*|oud-en-nieuw[^/]*)$",
        urlsplit(url).path, re.I,
    ):
        return None
    if name == "Bibelot" and re.search(r"\bclub\b", raw_text[:600], re.I) and not re.search(r"\bconcert\b", raw_text[:600], re.I):
        return None
    if name=="Klokgebouw":
        # The agenda explicitly labels exhibitions, markets, conventions and parties.
        if re.search(r"fair|expo|vintage|design-week|kerstmarkt|conference|kennis|recruitment|beurs",lowered):
            return None
        genre_match=re.search(r"Agenda\s*/\s*([A-Za-z]+)",raw_text[:2000],re.I)
        if genre_match and genre_match.group(1).lower() in ("retail","public","expo","kennis","culture"):
            return None
    if name=="De Helling" and re.search(r"\b(?:rave|afrobeats|fanparty|disco|clubnachten?|nachtclub|clubnight|freax)\b|paardenrave|day-rave",identity):
        return None
    if name=="BIRD" and re.search(r"360-degrees|talk|clubnight|clubnacht|cafe-dj-sessions",lowered):
        return None
    if name=="Metropool" and re.search(r"comedy|muziekquiz|clubnacht|nightclub|party|silent disco",identity):
        return None
    if name=="Hedon" and re.search(r"hedon-academy|workshop|comedy|cabaret|lezing|rave|techno|80s-verantwoord|80.s.verantwoord|clubnacht|fanparty",identity):
        return None
    if name=="Klokgebouw" and re.search(r"snakepit|rave|dance|feest|party|festival-electronic|kerstborrel|cisco-connect",identity):
        return None
    if name=="SPOT Groningen" and re.search(r"klassieke?[- ]muziek|kamermuziek|orkestconcert|opera|ballet|cabaret|toneel",identity):
        return None
    # Neushoorn's broad agenda also lists wrestling, comedy and DJ nights.
    # Exclude only recognisable non-concert event titles; do not reject
    # artist biographies that happen to contain similar words.
    if name=="Neushoorn" and re.search(
        r"^(?:comedy night|uit de hoge hoed improv comedy|"
        r"queens & quizzes|powerslam|family rave day|the grave rave)\b",
        title, re.I,
    ):
        return None
    if name=="Hedon" and re.search(
        r"^(?:bezerkus bingo|q\s*music foute feestje|jimmy carr|never too late)\b",
        title, re.I,
    ):
        return None


    return {"artist":title,"venue":venue,"city":city,"country":"NL",
            "date":event_date,"time":event_time,
            "source":name,"url":url}

def filter_hedon_nights(urls, html):
    """Exclude URLs assigned to Hedon's official nightlife listings."""
    listed=discover(html,"https://hedon-zwolle.nl/nights","/voorstelling/")
    if len(listed)<5:
        raise RuntimeError("Hedon Nights list unexpectedly small")
    def key(url):
        u=urlsplit(url)
        return (u.hostname or "").lower().removeprefix("www."),u.path.lower().rstrip("/")
    blocked={key(u) for u in listed}
    remaining=[u for u in urls if key(u) not in blocked]
    print("Hedon official Nights excluded:",len(urls)-len(remaining),flush=True)
    return remaining



# The Klokgebouw agenda itself labels each linked card (Rock / Pop / Dance /
# Business / etc.) and shows its day and month. These details are more reliable
# than dates inferred from related-event widgets on the individual pages.
class KlokgebouwAgendaCards(HTMLParser):
    def __init__(self, base):
        super().__init__()
        self.base = base
        self.current = None
        self.cards = {}

    def handle_starttag(self, tag, attrs):
        data = dict(attrs)
        if tag == "a" and self.current is None:
            url = urljoin(self.base, unescape(data.get("href", "")))
            if (urlsplit(url).hostname or "").removeprefix("www.") == "klokgebouw.nl" and "/agenda/" in urlsplit(url).path:
                self.current = [normalize_url(url), []]
                return

    def handle_endtag(self, tag):
        if self.current is None or tag != "a":
            return
        if self.current is not None:
            key, parts = self.current
            text = re.sub(r"\s+", " ", " ".join(parts)).strip()
            genre = re.search(r"\b(Rock|Pop|Dance|Business|Retail|Public|Expo|Culture|Kennis)\b", text, re.I)
            shown = re.search(
                r"\b(?:ma|di|wo|do|vr|za|zo)\.?\s*(\d{1,2})\s*"
                r"(jan|feb|mrt|apr|mei|jun|jul|aug|sep|okt|nov|dec)\.?\b",
                text, re.I,
            )
            self.cards[key] = {
                "genre": genre.group(1).lower() if genre else "",
                "day": int(shown.group(1)) if shown else None,
                "month": MONTHS.get(shown.group(2).lower()) if shown else None,
            }
            self.current = None

    def handle_data(self, data):
        if self.current is not None:
            self.current[1].append(data)


def klokgebouw_listing_cards(html, base="https://www.klokgebouw.nl/agenda"):
    parser = KlokgebouwAgendaCards(base)
    parser.feed(html)
    return parser.cards


def is_nonconcert_listing(name, url):
    path = urlsplit(url).path.lower()
    if name == "SPOT Groningen":
        # These are category, information or subscription pages; their
        # recommended shows previously produced fictitious "concerts".
        return bool(re.search(r"/programma/(?:verzameling|abonnement)(?:/|-|$)", path))
    if name == "Klokgebouw":
        return bool(re.search(
            r"(?:cisco-connect|kerstborrel|dutch-design-week|kerstmarkt|chili-fest)",
            path,
        ))
    return False


def deduplicate_doornroosje_festival_days(events):
    """A festival landing page and numbered ticket page are not two concerts."""
    retained = {}
    for event in events:
        url = urlsplit(event["url"]).path.lower().rstrip("/")
        if (event.get("source") == "Doornroosje"
                and re.fullmatch(r"/event/soulcrusher-20\d\d(?:-\d+)?", url)):
            key = (event["artist"].casefold().strip(),
                   event["date"], event["venue"].casefold().strip())
            old = retained.get(key)
            # Prefer the canonical unnumbered URL, not an arbitrary
            # fetch/concurrency order.
            if old is None or (
                re.search(r"-20\d\d-\d+$", url) is None
                and re.search(r"-20\d\d-\d+$", urlsplit(old["url"]).path.lower().rstrip("/")) is not None
            ):
                retained[key] = event
        else:
            retained[(normalize_url(event["url"]),)] = event
    return list(retained.values())

def scrape_venue(name, maximum=500):
    agenda, prefix,city=VENUES[name]
    html=download_page_retry(agenda,attempts=2)
    found=discover(html,agenda,prefix)
    listing_cards = klokgebouw_listing_cards(html, agenda) if name == "Klokgebouw" else {}
    found = [url for url in found if not is_nonconcert_listing(name, url)]
    if name == "Klokgebouw":
        excluded_categories = {"dance", "business", "retail", "public", "expo", "culture", "kennis"}
        found = [
            url for url in found
            if listing_cards.get(normalize_url(url), {}).get("genre") not in excluded_categories
        ]
    if name == "De Bosuil":
        # /programma/archief is a navigation link, not a concert detail.
        # The previous parser invented a date from its archive listings.
        found = [url for url in found
                 if not re.search(r"/programma/archief(?:/|$)", urlsplit(url).path, re.I)]
        # The official programme currently lists ~67 future events.
        # Refuse a silently truncated first page.
        if len(found) < 45:
            raise RuntimeError(f"De Bosuil: incomplete programme: {len(found)} event URLs")
    if name == "Klokgebouw":
        # Known non-concert listings return HTTP 500 on their detail URLs.
        # Filter only these unmistakably non-music events before detail fetch.
        excluded_slugs = (
            "/agenda/dutch-design-week",
            "/agenda/kerstmarkt",
            "/agenda/chili-fest",
        )
        excluded = [url for url in found if any(
            slug in url.lower() for slug in excluded_slugs
        )]
        found = [url for url in found if url not in excluded]
        print("Klokgebouw non-concert listings excluded:", excluded, flush=True)
    if name=="Hedon":
        nights=download_page_retry("https://hedon-zwolle.nl/nights",attempts=3)
        found=filter_hedon_nights(found,nights)
    if name=="Bibelot":
        # Verified FacetWP pager: /programma/?_paged=2,3,...
        # Load every page and compare discovered event URLs with its own
        # total_rows count. Never silently publish the first 30 only.
        pager = re.search(
            r'"pager":\s*\{[^}]*"total_rows":\s*(\d+)[^}]*"total_pages":\s*(\d+)',
            html,
        )
        if not pager:
            raise RuntimeError("Bibelot: official FacetWP pagination metadata missing")
        total_rows, total_pages = map(int, pager.groups())
        if total_pages < 1 or total_pages > 30:
            raise RuntimeError(f"Bibelot: suspicious page count {total_pages}")
        keys = {normalize_url(url) for url in found}
        for number in range(2, total_pages + 1):
            html_page = download_page_retry(
                agenda + "?_paged=" + str(number), attempts=2
            )
            page_links = discover(html_page, agenda, prefix)
            additions = 0
            for event_url in page_links:
                key = normalize_url(event_url)
                if key not in keys:
                    found.append(event_url)
                    keys.add(key)
                    additions += 1
            print("Bibelot page", number, "found", len(page_links),
                  "new", additions, "total", len(found), flush=True)
            if additions == 0:
                raise RuntimeError(f"Bibelot: pagination stalled at page {number}")
        minimum_coverage = max(40, int(total_rows * 0.90))
        if len(found) < minimum_coverage:
            raise RuntimeError(
                f"Bibelot: incomplete agenda ({len(found)} of {total_rows} "
                f"events, expected at least {minimum_coverage})"
            )
    if name=="De Pul":
        # Exact load-more endpoint and parameters verified in the venue's
        # own /js/site.min.js. It returns {output, show_more_possible}.
        # Count actual rendered event cards, NOT unique links, for the offset.
        found = []
        seen = set()
        shown = 0
        for page_number in range(1, 90):
            query = (
                "https://www.livepul.com/query.php"
                "?source=agenda&agenda_page=true&month=all&search=false"
                "&amount_of_events_already_shown=" + str(shown)
            )
            payload = json.loads(download_page_retry(query, attempts=2))
            if not isinstance(payload, dict) or "show_more_possible" not in payload:
                raise RuntimeError("De Pul API: missing pagination marker")
            output = payload.get("output", "")
            if not isinstance(output, str):
                raise RuntimeError("De Pul API: invalid event HTML")
            cards = len(re.findall(
                r"""class=["'][^"']*\bagenda-event--actual-event\b""",
                output, flags=re.I,
            ))
            links = discover(output, agenda, prefix)
            added = 0
            for event_url in links:
                key = normalize_url(event_url)
                if key not in seen:
                    seen.add(key)
                    found.append(event_url)
                    added += 1
            print("De Pul API page", page_number,
                  "event cards", cards, "new links", added,
                  "total", len(found), flush=True)
            if cards == 0 and payload["show_more_possible"]:
                raise RuntimeError("De Pul: load-more reports more events but page is empty")
            shown += cards
            if len(found) > maximum:
                raise RuntimeError("De Pul: over maximum event count")
            if not payload["show_more_possible"]:
                break
            if cards == 0:
                raise RuntimeError("De Pul: pagination did not advance")
        else:
            raise RuntimeError("De Pul pagination page limit reached")
        if shown < 20 or len(found) < 15:
            raise RuntimeError("De Pul: suspiciously incomplete official programme")
    if name=="Neushoorn":
        # Webflow renders a maximum of 100 events per collection page.
        # Its next-page link uses a collection-specific query name rather
        # than the generic ?page=2 parameter.
        match = re.search(r"([A-Za-z0-9]+_page)=2", html, flags=re.I)
        if len(found)>=100 and not match:
            raise RuntimeError("Neushoorn lists 100 events but its pagination key was not found")
        if match:
            key_name=match.group(1)
            found_keys={normalize_url(url) for url in found}
            for page_number in range(2, 30):
                next_url=agenda.split("?",1)[0]+"?"+key_name+"="+str(page_number)
                html_page=download_page_retry(next_url,attempts=2)
                page_links=discover(html_page,agenda,prefix)
                additions=0
                for event_url in page_links:
                    key=normalize_url(event_url)
                    if key not in found_keys:
                        found.append(event_url)
                        found_keys.add(key)
                        additions+=1
                print("Neushoorn Webflow page:",page_number,
                      "page links:",len(page_links),"new:",additions,flush=True)
                if not page_links or additions==0:
                    break
                if len(page_links)<100:
                    break
            else:
                raise RuntimeError("Neushoorn pagination limit reached before agenda end")
    if name=="Metropool":
        # The agenda HTML contains only the first ten entries. Its own
        # infinite-scroll code calls /mvc/event/partial?pNumber=N.
        discovered_keys={normalize_url(url) for url in found}
        for number in range(2, 65):
            partial_url=(
                "https://metropool.nl/mvc/event/partial?pNumber="
                + str(number)
                + "&keyword=&genre=&tag=&type=&StartDate=&EndDate="
                + "&locatie=&label=&newAnnounced=False"
            )
            try:
                page_html=download_page_retry(partial_url,attempts=2)
            except Exception as error:
                # Metropool's final batch returns HTTP 200 with an empty
                # response instead of a normal end-of-pagination marker.
                # This is a valid stopping condition after prior batches.
                if "Lege HTML-response" in str(error) and number > 2:
                    print("Metropool pagination complete at page", number,
                          "collected links:", len(found), flush=True)
                    break
                raise RuntimeError("Metropool pagination page "
                                   + str(number) + " failed: " + str(error))
            page_links=discover(page_html,agenda,prefix)
            added=0
            for url in page_links:
                key=normalize_url(url)
                if key not in discovered_keys:
                    found.append(url)
                    discovered_keys.add(key)
                    added+=1
            if number%5==0:
                print("Metropool agenda batches:",number,
                      "links:",len(found),flush=True)
            if not page_links or not added:
                break
    if len(found) > maximum:
        raise RuntimeError(f"{name}: discovered {len(found)} links, exceeding processing limit {maximum}; refusing truncated agenda")
    if not found:raise RuntimeError(f"{name}: no event URLs discovered")
    items=[];errors=0;recovered=0
    # If Metropool intermittently returns 500 for particular detail pages,
    # the most recent *verified* published record is the only safe fallback.
    # Recovery is URL-exact and only allowed for still-future concerts.
    previous = previous_published_venue_events(name) if name=="Metropool" else {}
    def read(url):
        event_html=download_page_retry(url,attempts=3 if name=="Metropool" else 2)
        return parse_event(event_html,url,name,city)
    # Fewer parallel requests reduce HTTP 500s from Metropool's backend.
    workers = 3 if name=="Metropool" else 7
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures={ex.submit(read,url):url for url in found}
        for future in as_completed(futures):
            url = futures[future]
            try:
                item=future.result()
                if item:
                    if name == "Klokgebouw":
                        metadata = listing_cards.get(normalize_url(url), {})
                        day, month = metadata.get("day"), metadata.get("month")
                        if day is not None and month is not None:
                            # Use the date printed beside this exact event link.
                            # Never inherit a time belonging to the wrong day.
                            year = date.fromisoformat(item["date"]).year
                            try:
                                shown_date = date(year, month, day).isoformat()
                                if shown_date != item["date"]:
                                    item["date"] = shown_date
                                    item["time"] = ""
                            except ValueError:
                                pass
                    items.append(item)
            except Exception as error:
                url = futures[future]
                saved = previous.get(normalize_url(url))
                if saved:
                    recovered+=1
                    items.append(saved)
                    if recovered<=3:
                        print("Metropool: reused previously verified future event:",url,flush=True)
                else:
                    errors+=1
                    if errors<=3:
                        print(name,"detail error:",url,str(error)[:160],flush=True)
    if name == "Doornroosje":
        items = deduplicate_doornroosje_festival_days(items)
    unique={normalize_url(i["url"]):i for i in items}
    if not unique:
        raise RuntimeError(f"{name}: no future concerts parsed from {len(found)} links; refusing empty agenda")
    if errors > max(2, int(len(found) * 0.10)):
        raise RuntimeError(f"{name}: {errors}/{len(found)} detail requests failed without verified fallback; refusing incomplete agenda")
    if recovered > max(10,int(len(found)*0.20)):
        raise RuntimeError(f"{name}: {recovered}/{len(found)} events needed fallback; refusing overly stale agenda")
    print(name,"discovered:",len(found),"future concerts:",len(unique),
          "request errors:",errors,"verified fallbacks:",recovered,flush=True)
    return sorted(unique.values(),key=lambda i:(i["date"],i["time"],i["artist"]))

def previous_published_venue_events(name, today=None, path="concerts.json"):
    """Exact URL fallback from the already published feed (never a guessed date).

    Failure to read prior data must not bypass the normal completeness checks.
    """
    today = today or date.today().isoformat()
    try:
        with open(path, encoding="utf-8") as handle:
            events = json.load(handle)
    except (OSError, ValueError, TypeError):
        return {}
    if not isinstance(events, list):
        return {}
    return {
        normalize_url(event["url"]): event
        for event in events
        if isinstance(event, dict)
        and event.get("source") == name
        and isinstance(event.get("url"), str)
        and isinstance(event.get("date"), str)
        and event["date"] >= today
        and event.get("artist")
        and event.get("venue")
    }


def scrape_new_venues():
    # Each venue is independent. Running them concurrently avoids making
    # the weekly job wait for all slow detail pages sequentially.
    names=[name for name in VENUES if name!="BIRD"]
    combined=[]
    failed=[]
    with ThreadPoolExecutor(max_workers=3) as executor:
        jobs={executor.submit(scrape_venue,name):name for name in names}
        for future in as_completed(jobs):
            name=jobs[future]
            try:
                concerts=future.result()
                combined.extend(concerts)
                print("Finished",name,len(concerts),"concerts",flush=True)
            except Exception as error:
                failed.append(f"{name}: {error}")
                print(name,"ERROR:",repr(error),flush=True)
    if failed:
        raise RuntimeError("Incomplete new-venue scrape: " + "; ".join(failed))
    return combined

if __name__=="__main__":
    data=scrape_new_venues()
    for name in VENUES:
        items=[i for i in data if i["source"]==name]
        print("SUMMARY",name,len(items),repr(items[:2]),flush=True)
