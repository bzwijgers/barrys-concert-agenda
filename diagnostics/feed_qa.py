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
    if expected_day <= today:continue  # Same-day listings may disappear before this scraper completes.
    matches=[x for x in feed if x.get("source")==name and needle.rstrip("/") in x.get("url","").rstrip("/")]
    if not matches or all(x["date"]!=expected_day for x in matches):
        raise RuntimeError("Missing or incorrect expected event: "+name+" "+needle)
# These real shows disappeared because generic words in artist biographies
# were mistakenly treated as nightlife/classical-event categories.
# Guard them until their performance dates have passed.
recovered=[
    ("SPOT Groningen","https://www.spotgroningen.nl/programma/timebox/","2026-11-27"),
    ("SPOT Groningen","https://www.spotgroningen.nl/programma/pitou/","2026-11-20"),
    ("SPOT Groningen","https://www.spotgroningen.nl/programma/levi-sct/","2026-11-18"),
    ("SPOT Groningen","https://www.spotgroningen.nl/programma/pieter-savenberg/","2026-11-05"),
    ("SPOT Groningen","https://www.spotgroningen.nl/programma/alexis-ffrench/","2027-06-06"),
    ("Hedon","https://hedon-zwolle.nl/voorstelling/32962/big-sleep","2026-11-15"),
]
by_url={x["url"].rstrip("/").lower():x for x in feed}
for source,url,day in recovered:
    if day<=today:
        continue  # Event may already have started or been removed from programme.
    item=by_url.get(url.rstrip("/").lower())
    if not item or item["source"]!=source or item["date"]!=day:
        raise RuntimeError("Recovered live concert absent or misdated: "+url)

# Do not mistake broad venue agendas for concert-only agendas.
non_music_rejections={
    "Neushoorn":r"^(?:comedy night|uit de hoge hoed improv comedy|queens & quizzes|powerslam|family rave day|the grave rave)\b",
    "Hedon":r"^(?:bezerkus bingo|q\s*music foute feestje|jimmy carr|never too late|common ground festival|4am|night mode|vroegzat|pulse presents|emo night|rnb singalong|wasserette|club motion|40up)\b",
    "Gebouw-T":r"quiz['’]m|toppop yeah! the party",
}
bad_non_music=[
    (x["source"],x["artist"],x["url"])
    for x in feed
    if x["source"] in non_music_rejections
    and re.search(non_music_rejections[x["source"]],x["artist"],re.I)
]
if bad_non_music:
    raise RuntimeError("Non-concert entries still in published feed: "+repr(bad_non_music[:15]))

# Protect future publications against exact performances entering again
# through a different indexed/ticket-site URL.
import sys
from pathlib import Path
# This script is called as 'python diagnostics/feed_qa.py' by GitHub Actions.
# That puts diagnostics/ (not the repository root) on sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scrapers.feed_quality import deduplicate_performances, is_known_nonconcert
_, duplicate_performances = deduplicate_performances(feed)
if duplicate_performances:
    raise RuntimeError(
        "Multiple URLs for identical performances: " +
        repr([(x["artist"], x["date"], x["venue"]) for x in duplicate_performances[:15]])
    )
bad_titles=[x for x in feed if is_known_nonconcert(x)]
if bad_titles:
    raise RuntimeError(
        "Known nonconcert events leaked into feed: " +
        repr([(x["artist"], x["source"]) for x in bad_titles[:15]])
    )
print("PASS: one listing per performance, nonconcert titles excluded")

print("PASS: recovered official concerts retained, non-music entries excluded")

print("PASS: all sources present, dates valid, unique URLs, known shows correctly dated")
