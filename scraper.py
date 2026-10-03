from datetime import datetime
import json

from scrapers.common import normalize_url, scrape_boerderij, scrape_paard, scrape_melkweg, scrape_tivolivredenburg, scrape_mezz
from scrapers.effenaar import scrape_effenaar
from scrapers.rotown import scrape_rotown
from scrapers.source013 import scrape_013
from scrapers.paradiso import scrape_paradiso
from scrapers.baroeg import scrape_baroeg


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
):
    try:
        source_concerts = scraper_function()
        print(source_name + " opgehaald:", len(source_concerts))
        all_concerts.extend(source_concerts)
    except Exception as error:
        print("ERNSTIGE " + source_name.upper() + " FOUT:", str(error))


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
