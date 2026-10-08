from datetime import datetime
import json

from scrapers.common import normalize_url, scrape_boerderij, scrape_paard, scrape_melkweg, scrape_tivolivredenburg, scrape_mezz, scrape_patronaat
from scrapers.effenaar import scrape_effenaar
from scrapers.rotown import scrape_rotown
from scrapers.source013 import scrape_013
from scrapers.paradiso import scrape_paradiso
from scrapers.baroeg import scrape_baroeg
from scrapers.tolhuistuin import scrape_tolhuistuin
from scrapers.gebouw_t import scrape_gebouw_t
from scrapers.dbs import scrape_dbs
from scrapers.ticketswap import enrich_ticketswap_urls
from scrapers.new_venues import scrape_new_venues
from scrapers.bird import scrape_bird
from scrapers.podiuminfo_venues import scrape_podiuminfo_venues


# ============================================================
# CENTRALE DATABASE
# ============================================================

print(
    "Barry's Concert Agenda - centrale scraper"
)

print(
    "Start:",
    datetime.now().isoformat(
        timespec="seconds"
    )
)

all_concerts = []


# ============================================================
# EFFENAAR
# ============================================================

try:
    effenaar_concerts = (
        scrape_effenaar()
    )

    all_concerts.extend(
        effenaar_concerts
    )

except Exception as error:
    print(
        "ERNSTIGE EFFENAAR FOUT:",
        str(error)
    )


# ============================================================
# ROTOWN
# ============================================================

try:
    rotown_concerts = (
        scrape_rotown()
    )

    all_concerts.extend(
        rotown_concerts
    )

except Exception as error:
    print(
        "ERNSTIGE ROTOWN FOUT:",
        str(error)
    )


# ============================================================
# 013
# ============================================================
#
# LET OP:
# 013 is bewust NIET omgeven door try/except.
#
# scrape_013() bevat een beveiliging:
# - minder dan 25 programma-links -> STOP
# - minder dan 25 verwerkte concerten -> STOP
#
# Daardoor wordt concerts.json NIET overschreven
# wanneer de 013-scraper opnieuw stukloopt.
# ============================================================

source013_concerts = (
    scrape_013()
)

all_concerts.extend(
    source013_concerts
)


# ============================================================
# PARADISO
# ============================================================

try:
    paradiso_concerts = (
        scrape_paradiso()
    )

    all_concerts.extend(
        paradiso_concerts
    )

except Exception as error:
    print(
        "ERNSTIGE PARADISO FOUT:",
        str(error)
    )


# ============================================================
# BAROEG
# ============================================================

try:
    baroeg_concerts = (
        scrape_baroeg()
    )

    all_concerts.extend(
        baroeg_concerts
    )

except Exception as error:
    print(
        "ERNSTIGE BAROEG FOUT:",
        str(error)
    )


# ============================================================
# NIEUWE PODIA
# ============================================================

for source_name, scraper_function in (
    ("Boerderij", scrape_boerderij),
    ("PAARD", scrape_paard),
    ("Melkweg", scrape_melkweg),
    ("TivoliVredenburg", scrape_tivolivredenburg),
    ("MEZZ", scrape_mezz),
    ("Patronaat", scrape_patronaat),
):
    try:
        source_concerts = scraper_function()
        print(source_name + " opgehaald:", len(source_concerts))
        all_concerts.extend(source_concerts)
    except Exception as error:
        print("ERNSTIGE " + source_name.upper() + " FOUT:", str(error))


# ============================================================
# TOLHUISTUIN
# ============================================================
# Tolhuistuin-programma wordt rechtstreeks via de officiële Paradiso
# Tolhuistuin-programmapagina opgehaald in scrape_paradiso(). Zo gebruiken
# Paradiso en Tolhuistuin dezelfde bewezen eventparser en vermijden we de
# onvolledige client-side agenda van tolhuistuin.nl.


# ============================================================
# GEBOUW-T
# ============================================================

try:
    all_concerts.extend(scrape_gebouw_t())
except Exception as error:
    print("ERNSTIGE GEBOUW-T FOUT:", str(error))


# ============================================================
# dB's UTRECHT
# ============================================================

try:
    dbs_concerts = scrape_dbs()
    existing_keys = {
        (concert["artist"].strip().lower(), concert["date"])
        for concert in all_concerts
    }
    all_concerts.extend(
        concert for concert in dbs_concerts
        if (concert["artist"].strip().lower(), concert["date"]) not in existing_keys
    )
except Exception as error:
    print("ERNSTIGE dB's FOUT:", str(error))


# ============================================================
# EXTRA POPPODIA - OFFICIELE AGENDA'S
# ============================================================
# Iedere nieuwe bron rapporteert afzonderlijk fouten en aantallen.
try:
    additional_concerts = scrape_new_venues()
    all_concerts.extend(additional_concerts)
    print("Nieuwe podia samen:", len(additional_concerts), flush=True)
except Exception as error:
    print("ERNSTIGE FOUT NIEUWE PODIA:", repr(error), flush=True)


# ============================================================
# AMARE EN BOLWERK (VEILIG GEFILTERDE CONCERTEN)
# ============================================================
try:
    all_concerts.extend(scrape_podiuminfo_venues())
except Exception as error:
    print("ERNSTIGE FOUT AMARE/BOLWERK:", str(error), flush=True)


# ============================================================
# BIRD ROTTERDAM - VOLLEDIGE LIVE-CONCERTAGENDA
# ============================================================
# Direct uit de officiële Prismic-agenda van BIRD. De beperkte
# /concerts/-landingspagina wordt bewust niet meer gebruikt.
try:
    bird_live_concerts = scrape_bird()
    all_concerts.extend(bird_live_concerts)
except Exception as error:
    print("ERNSTIGE BIRD LIVE FOUT:", str(error), flush=True)


# ============================================================
# DUBBELEN VERWIJDEREN
# ============================================================

unique_concerts = {}

for concert in all_concerts:
    key = normalize_url(
        concert["url"]
    )

    if key:
        unique_concerts[key] = concert

all_concerts = list(
    unique_concerts.values()
)


# ============================================================
# TICKETSWAP - ALLEEN EXACTE EVENTLINKS
# ============================================================

try:
    all_concerts = enrich_ticketswap_urls(all_concerts)
except Exception as error:
    print("TICKETSWAP VERRIJKING OVERGESLAGEN:", str(error))


# ============================================================
# SORTEREN
# ============================================================

all_concerts.sort(
    key=lambda concert: (
        concert["date"],
        concert["time"],
        concert["artist"].lower()
    )
)


# ============================================================
# EXTRA CONTROLE VOOR OPSLAAN
# ============================================================

source013_count_before_save = len(
    [
        concert
        for concert in all_concerts
        if concert["source"] == "013"
    ]
)

if source013_count_before_save < 25:
    raise RuntimeError(
        "VEILIGHEIDSSTOP: slechts "
        f"{source013_count_before_save} "
        "013-concerten aanwezig. "
        "concerts.json wordt NIET overschreven."
    )


# ============================================================
# CONTROLE: HERSTELDE BRONNEN MOGEN NIET STIL VERDWIJNEN
# ============================================================
# Existing future events provide a moving baseline; unlike a fixed
# minimum this safely decreases as old shows pass.
try:
    with open("concerts.json", encoding="utf-8") as existing_file:
        previously_published = json.load(existing_file)
except (OSError, ValueError, TypeError):
    previously_published = []

today_iso = datetime.now().date().isoformat()
protected_sources = (
    "TivoliVredenburg", "Hedon", "Neushoorn", "Patronaat",
    "Amare", "Bolwerk", "BIRD", "Metropool", "Gebouw-T", "dB's"
)
for protected_source in protected_sources:
    prev_count = sum(
        x.get("source") == protected_source and x.get("date", "") >= today_iso
        for x in previously_published if isinstance(x, dict)
    )
    new_count = sum(
        x.get("source") == protected_source and x.get("date", "") >= today_iso
        for x in all_concerts
    )
    minimum = max(1, int(prev_count * 0.70))
    if new_count < minimum:
        raise RuntimeError(
            "VEILIGHEIDSSTOP: " + protected_source
            + " has " + str(new_count) + " events versus "
            + str(prev_count) + " in previous feed. Refusing partial publication."
        )
    print("Coverage protection:", protected_source,
          new_count, "previous", prev_count, flush=True)


# ============================================================
# PARADISO: STOP BIJ ONVOLLEDIGE FEED
# ============================================================
# Paradiso + Tolhuistuin hoort een substantieel toekomstig programma
# te leveren. Sla nooit een gedeeltelijke scrape over de goede feed op.
paradiso_combined = [
    concert for concert in all_concerts
    if concert["source"] in ("Paradiso", "Tolhuistuin")
]
# Vergelijk met de vorige GEPUBLICEERDE feed, maar tel alleen shows
# die op de huidige datum nog moeten plaatsvinden. Daarmee voorkomen we
# zowel een plotselinge scraper-uitval als een onterechte vaste ondergrens
# naarmate de kalender vordert.
previous_paradiso_count = 0
try:
    with open("concerts.json", "r", encoding="utf-8") as old_file:
        previous_concerts = json.load(old_file)
    today_string = datetime.now().date().isoformat()
    previous_paradiso_count = sum(
        1 for old_concert in previous_concerts
        if old_concert.get("source") in ("Paradiso", "Tolhuistuin")
        and old_concert.get("date", "") >= today_string
    )
except (OSError, ValueError, TypeError) as error:
    print("Paradiso vorige-feedcontrole niet beschikbaar:", error)

minimum_expected = max(1, int(previous_paradiso_count * 0.75))
print(
    "Paradiso/Tolhuistuin feedcontrole:",
    len(paradiso_combined), "nieuw; ",
    previous_paradiso_count, "vorige; minimaal", minimum_expected,
)
if len(paradiso_combined) < minimum_expected:
    raise RuntimeError(
        "VEILIGHEIDSSTOP: Paradiso/Tolhuistuin teruggevallen naar "
        + str(len(paradiso_combined))
        + " vanaf " + str(previous_paradiso_count)
        + " toekomstige concerten; concerts.json blijft ongewijzigd."
    )

# Een bekend, officieel bevestigd concert moet ook daadwerkelijk in de
# volledige feed staan. De datumcontrole maakt de bewaking automatisch
# niet-actief zodra het concert heeft plaatsgevonden.
known_paradiso_events = {
    "https://www.paradiso.nl/nl/programma/songhoy-blues/2884193":
        ("2026-10-10", "Tolhuistuin"),
    "https://www.paradiso.nl/nl/programma/this-is-the-kit/2931706":
        ("2027-05-07", "Tolhuistuin"),
}
present_paradiso = {normalize_url(c["url"]): c for c in paradiso_combined}
for required_url, (required_date, required_source) in known_paradiso_events.items():
    if required_date < datetime.now().date().isoformat():
        continue
    event = present_paradiso.get(normalize_url(required_url))
    if not event or event["date"] != required_date or event["source"] != required_source:
        raise RuntimeError(
            "VEILIGHEIDSSTOP: bevestigd Paradiso-programma ontbreekt of "
            "heeft verkeerde datum/locatie: " + required_url
        )

# ============================================================
# JSON OPSLAAN
# ============================================================

with open(
    "concerts.json",
    "w",
    encoding="utf-8"
) as file:

    json.dump(
        all_concerts,
        file,
        ensure_ascii=False,
        indent=2
    )


# ============================================================
# RESULTAAT
# ============================================================

effenaar_count = len(
    [
        concert
        for concert in all_concerts
        if concert["source"] == "Effenaar"
    ]
)

rotown_count = len(
    [
        concert
        for concert in all_concerts
        if concert["source"] == "Rotown"
    ]
)

source013_count = len(
    [
        concert
        for concert in all_concerts
        if concert["source"] == "013"
    ]
)

paradiso_count = len(
    [
        concert
        for concert in all_concerts
        if concert["source"] == "Paradiso"
    ]
)

baroeg_count = len(
    [
        concert
        for concert in all_concerts
        if concert["source"] == "Baroeg"
    ]
)


print()
print(
    "============================================================"
)
print("CENTRAAL RESULTAAT")
print(
    "============================================================"
)

print(
    "Effenaar:",
    effenaar_count
)

print(
    "Rotown:",
    rotown_count
)

print(
    "013:",
    source013_count
)

print(
    "Paradiso:",
    paradiso_count
)

print(
    "Baroeg:",
    baroeg_count
)

for source_name in ("Boerderij", "PAARD", "Melkweg", "TivoliVredenburg"):
    print(source_name + ":", len([concert for concert in all_concerts if concert["source"] == source_name]))

print(
    "Totaal:",
    len(all_concerts)
)

print()
print(
    "Bestand gemaakt: concerts.json"
)

print(
    "Centrale scraper gereed."
)
