"""Post-publication QA for the generated concert feed.

Run independently from the scraper so no partially-updated feed can be
mistaken for a verified publication.
"""
from collections import Counter
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit
import json
import re

feed = json.loads(Path("concerts.json").read_text(encoding="utf-8"))
if not isinstance(feed, list):
    raise RuntimeError("Feed root must be a list")

required = [
    "013", "Rotown", "Effenaar", "Paradiso", "Tolhuistuin",
    "Baroeg", "Boerderij", "PAARD", "Melkweg", "MEZZ",
    "Patronaat", "TivoliVredenburg", "Gebouw-T", "dB's",
    "De Helling", "Klokgebouw", "Doornroosje", "Dynamo",
    "BIRD", "Metropool", "Hedon", "SPOT Groningen",
    "Neushoorn", "Amare", "Bolwerk",
]
counts=Counter(x.get("source","") for x in feed)
print("TOTAL",len(feed))
print("PER_SOURCE",dict(sorted(counts.items())))
missing=[name for name in required if counts[name]==0]
if missing:raise RuntimeError("Missing venue sources: "+repr(missing))

seen=set();invalid=[]
today=date.today().isoformat()
for item in feed:
    if not isinstance(item,dict):
        invalid.append(("not_dict",str(item)[:30]));continue
    source=item.get("source","")
    artist=item.get("artist","").strip()
    url=item.get("url","")
    day=item.get("date","")
    time=item.get("time","")
    if not artist or not item.get("city") or not source:
        invalid.append(("missing data",url));continue
    if not re.fullmatch(r"20\d\d-\d\d-\d\d",day) or day<today:
        invalid.append(("date",url));continue
    if time and not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d",time):
        invalid.append(("time",url));continue
    if urlsplit(url).scheme!="https" or not urlsplit(url).netloc:
        invalid.append(("URL",url));continue
    normalized=url.rstrip("/").lower()
    if normalized in seen:invalid.append(("duplicate URL",url))
    seen.add(normalized)
if invalid:
    print("INVALID_SAMPLES",invalid[:20])
    raise RuntimeError("Invalid concerts: "+str(len(invalid)))

cases={
    "De Helling":("john-coffey-support-eyesores-09-10-2026","2026-10-09"),
    "Klokgebouw":("danny-vera-2026","2026-10-31"),
    "Doornroosje":("event/sharp-pins/","2026-11-10"),
    "BIRD":("brothers-moving-10-10-2026","2026-10-10"),
    "Metropool":("agenda/khemmis","2026-10-11"),
    "Hedon":("voorstelling/33084/escah","2026-12-17"),
    "SPOT Groningen":("programma/elmer","2026-10-09"),
}
for name,(needle,expected_day) in cases.items():
    if expected_day < today:continue
    matches=[x for x in feed if x.get("source")==name and needle in x.get("url","")]
    if not matches or all(x["date"]!=expected_day for x in matches):
        raise RuntimeError("Missing or incorrect expected event: "+name+" "+needle)
print("PASS: all sources present, dates valid, unique URLs, known shows correctly dated")
