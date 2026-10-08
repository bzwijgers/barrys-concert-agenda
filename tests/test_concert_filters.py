"""Avoid false negatives when artist descriptions mention nightlife/classics."""
import unittest
from scrapers.new_venues import parse_event


def page(title, description, day, artist=None):
    import html
    import json
    event = {"@context": "https://schema.org", "@type": "MusicEvent",
             "name": artist or title.split(" | ")[0].split(" - ")[0],
             "startDate": day + "T20:30:00+01:00"}
    return (
        '<html><head><meta property="og:title" content="' + html.escape(title, quote=True) +
        '"><meta property="og:description" content="' + html.escape(description, quote=True) +
        '"><script type="application/ld+json">' + json.dumps(event) +
        '</script></head><body><h1>' + html.escape(artist or title) + '</h1></body></html>'
    )


class PreventFalseExclusions(unittest.TestCase):
    def test_hedon_real_band_mentioning_illegal_rave(self):
        html=page("BIG SLEEP - Hedon Zwolle",
                  "De band ontstond na een illegale rave in een bos.",
                  "2027-11-15", "BIG SLEEP")
        item=parse_event(html,"https://hedon-zwolle.nl/voorstelling/32962/big-sleep",
                         "Hedon","Zwolle")
        self.assertIsNotNone(item)
        self.assertEqual((item["artist"],item["date"]),("BIG SLEEP","2027-11-15"))

    def test_spot_pop_tribute_with_classics_in_bio(self):
        html=page("Timebox | SPOT Groningen",
                  "Britse klassiekers uit de jaren zestig: Beatles en Rolling Stones.",
                  "2027-11-27","Timebox")
        item=parse_event(html,"https://www.spotgroningen.nl/programma/timebox/",
                         "SPOT Groningen","Groningen")
        self.assertIsNotNone(item)
        self.assertEqual(item["artist"],"Timebox")

    def test_helling_indie_artist_with_rave_reviews(self):
        html=page("The Indie Band | De Helling",
                  "De band krijgt rave reviews voor hun debuut.",
                  "2027-12-01","The Indie Band")
        item=parse_event(html,"https://dehelling.nl/agenda/the-indie-band/",
                         "De Helling","Utrecht")
        self.assertIsNotNone(item)

    def test_hedon_actual_workshop_excluded(self):
        html=page("Hedon Academy workshop - Hedon Zwolle","Workshop voor technici",
                  "2027-11-15","Hedon Academy workshop")
        self.assertIsNone(parse_event(html,"https://hedon-zwolle.nl/voorstelling/111/workshop",
                                      "Hedon","Zwolle"))

    def test_spot_explicit_classical_series_excluded(self):
        html=page("Klassieke Muziek 3 - SPOT Groningen","Les over klassieke muziek",
                  "2027-11-27","Klassieke Muziek 3")
        self.assertIsNone(parse_event(html,"https://www.spotgroningen.nl/programma/klassieke-muziek-3/",
                                      "SPOT Groningen","Groningen"))

    def test_neushoorn_comedy_and_wrestling_excluded(self):
        for label,slug in (("Comedy Night","comedy-night"),("Powerslam @ De Harmonie","powerslam-de-harmonie"),("Family Rave Day","family-rave-day")):
            with self.subTest(label=label):
                html=page(label+" | Neushoorn", "Evenement", "2027-11-15", label)
                item=parse_event(html,"https://www.neushoorn.nl/events/"+slug,
                                 "Neushoorn","Leeuwarden")
                self.assertIsNone(item)

    def test_neushoorn_real_band_stays(self):
        html=page("Wodan Boys | Neushoorn", "Een krachtige live rockband",
                  "2027-11-15","Wodan Boys")
        self.assertIsNotNone(parse_event(html,"https://www.neushoorn.nl/events/wodan-boys",
                                         "Neushoorn","Leeuwarden"))

    def test_hedon_comedy_artist_excluded(self):
        html=page("Jimmy Carr - Hedon Zwolle","Comedyshow",
                  "2027-12-05","Jimmy Carr")
        self.assertIsNone(parse_event(html,"https://hedon-zwolle.nl/voorstelling/32496/jimmy-carr-theater-de-spiegel",
                                      "Hedon","Zwolle"))

if __name__=="__main__":
    unittest.main()
