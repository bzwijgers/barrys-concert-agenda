"""The next venue integrations, explicitly staged until separately live-validated.

Never advertise these as active feeds: production uses only verified scrapers.
"""
from dataclasses import dataclass

@dataclass(frozen=True)
class Candidate:
    name: str
    city: str
    country: str
    official_agenda: str
    kind: str = "venue"

CANDIDATES = (
    Candidate("Burgerweeshuis", "Deventer", "NL", "https://www.burgerweeshuis.nl"),
    Candidate("EKKO", "Utrecht", "NL", "https://www.ekko.nl"),
    Candidate("Gebr. de Nobel", "Leiden", "NL", "https://gebrdenobel.nl"),
    Candidate("Grenswerk", "Venlo", "NL", "https://www.grenswerk.nl"),
    Candidate("Iduna", "Drachten", "NL", "https://www.iduna.nl"),
    Candidate("Musicon", "Den Haag", "NL", "https://musicon.nl"),
    Candidate("Q-Factory", "Amsterdam", "NL", "https://www.q-factory-amsterdam.nl"),
    Candidate("Simplon", "Groningen", "NL", "https://www.simplon.nl"),
    Candidate("Sound Dog", "Breda", "NL", "https://sounddogbreda.nl/evenementen/"),
    Candidate("VERA", "Groningen", "NL", "https://www.vera-groningen.nl"),
    Candidate("Victorie", "Alkmaar", "NL", "https://www.podiumvictorie.nl"),
    Candidate("Ancienne Belgique", "Brussel", "BE", "https://www.abconcerts.be/nl/agenda"),
    Candidate("Trix", "Antwerpen", "BE", "https://www.trixonline.be"),
    Candidate("Biebob", "Vosselaar", "BE", "https://www.biebob.be"),
    Candidate("De Roma", "Antwerpen", "BE", "https://www.deroma.be"),
    Candidate("OLT Rivierenhof", "Deurne", "BE", "https://www.oltrivierenhof.be"),
    Candidate("Live Nation België", "België", "BE", "https://www.livenation.be", "promoter"),
)

def validate_registry():
    names = [c.name.casefold() for c in CANDIDATES]
    if len(names) != len(set(names)):
        raise ValueError("Duplicate candidate sources")
    if sum(c.country == "NL" for c in CANDIDATES) != 11:
        raise ValueError("Expected 11 Dutch candidate sources")
    if sum(c.country == "BE" and c.kind == "venue" for c in CANDIDATES) != 5:
        raise ValueError("Expected 5 Belgian venue sources")
    if sum(c.kind == "promoter" for c in CANDIDATES) != 1:
        raise ValueError("Expected Live Nation promoter source")
    if not all(c.official_agenda.startswith("https://") for c in CANDIDATES):
        raise ValueError("All sources must use HTTPS")
    return True
