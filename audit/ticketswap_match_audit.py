"""Audits precise coverage and near misses from downloaded TicketSwap XML sitemaps."""
import json
from collections import defaultdict,Counter
from pathlib import Path
from audit.publish_ticketswap_sitemaps import words,score,DATE_RE,ALIASES

data=json.loads(Path("concerts.json").read_text(encoding="utf-8"))
links=json.loads(Path("/tmp/barrys-public-ticketswap-event-links.json").read_text(encoding="utf-8"))
by_date=defaultdict(list)
for url in links:
    m=DATE_RE.search(url.rstrip("/").split("/")[-1])
    if m:by_date[m.group(1)].append(url)
summary=Counter()
examples=defaultdict(list)
for concert in data:
    if concert.get("ticketSwapUrl"):
        summary["already_has_link"]+=1;continue
    day=concert.get("date","")
    artist=words(concert.get("artist",""));city=words(concert.get("city",""));venue=words(concert.get("venue",""))
    city |= ALIASES.get(concert.get("city","").strip().lower(),set())
    matches=[]
    for link in by_date.get(day,[]):
        terms=words(link.split("/")[-1])
        common=artist&terms
        place=bool(city&terms or venue&terms)
        if common and place:
            matches.append((len(common),len(artist),len(city&terms),len(venue&terms),link))
    summary["unmatched"]+=1
    if matches:
        best=sorted(matches,reverse=True)[0]
        artist_hit,artist_count,city_hit,venue_hit,link=best
        if artist_hit >= max(1,(artist_count+1)//2):
            key="possible_half_artist"
        else:
            key="possible_partial_artist"
        summary[key]+=1
        if len(examples[key])<35:
            examples[key].append({
                "artist":concert["artist"],"venue":concert["venue"],"city":concert["city"],
                "date":day,"overlap":[artist_hit,artist_count,city_hit,venue_hit],
                "ticketSwap":link
            })
    elif len(examples["no_artist_place_match"])<15:
        examples["no_artist_place_match"].append({k:concert.get(k) for k in ("artist","date","city","venue")})
print("TICKETSWAP COVERAGE AUDIT",dict(summary),flush=True)
for kind,vals in examples.items():
    print("MATCH TYPE",kind,"EXAMPLES",len(vals),flush=True)
    for x in vals[:28]:
        print("EXAMPLE",json.dumps(x,ensure_ascii=False),flush=True)
