import unittest
from unittest.mock import patch
from datetime import date

from scrapers.new_venues import (
    discover, parse_event, date_from_text, VENUES
)


class AdditionalVenueTests(unittest.TestCase):
    def test_doornroosje_primary_event_and_no_false_cancellation(self):
        html = """<html><head>
        <meta property="og:title" content="Sharp Pins // Doornroosje Nijmegen // dinsdag 10 november 2026">
        <meta property="og:description" content="Sharp Pins komt dinsdag 10 november naar Nijmegen">
        </head><body>
        <nav>Verberg geannuleerde of verplaatste events</nav>
        <main>Sharp Pins locatie: Doornroosje - Paarse zaal
        datum: dinsdag 10 november 2026 zaal open: 19:30 uur start: 20:00 uur</main>
        <section>Tips za 23.01.2027 andere artiesten</section>
        </body></html>"""
        item = parse_event(html, "https://www.doornroosje.nl/event/sharp-pins/",
                           "Doornroosje", "Nijmegen")
        self.assertIsNotNone(item)
        self.assertEqual(item['artist'], 'Sharp Pins')
        self.assertEqual(item['date'], '2026-11-10')
        self.assertEqual(item['time'], '20:00')

    def test_hedon_primary_date_precedes_recommendations(self):
        html = """<html><head><meta property="og:title" content="ESCA$H - Hedon Zwolle">
        </head><body><main>ESCA$H Datum do 17 dec. Zaal open 20:00
        Aanvang 19:30 Prijs 13,50 Locatie Hedon - Kleine zaal</main>
        <aside><time datetime="2026-10-22">Andere show</time></aside>
        </body></html>"""
        item = parse_event(html,"https://hedon-zwolle.nl/voorstelling/33084/escah",
                           "Hedon","Zwolle")
        self.assertEqual((item['date'],item['time']),('2026-12-17','19:30'))

    def test_dynamo_host_www_alias_in_discovery(self):
        html = '<a href="https://dynamo-eindhoven.nl/evenement/the-hara/">The Hara</a>'
        urls = discover(html,"https://www.dynamo-eindhoven.nl/evenementen/","/evenement/")
        self.assertEqual(urls,['https://dynamo-eindhoven.nl/evenement/the-hara'])

    def test_metropool_title_description_not_artist(self):
        html = """<html><head><meta property="og:title"
        content="Khemmis - Moderne doommetal ontmoet compromisloze deathmetal">
        <meta property="og:description" content="Khemmis op zondag 11 oktober naar Hengelo">
        </head><body>11 okt Hengelo Khemmis Tijdschema Muziekcafé open 17:00
        Zaal open 19:30 Aanvang voorprogramma 20:00 Aanvang hoofdact 21:15
        </body></html>"""
        item = parse_event(html,"https://metropool.nl/agenda/khemmis",
                           "Metropool","Hengelo")
        self.assertEqual((item['artist'],item['date'],item['time']),
                         ('Khemmis','2026-10-11','20:00'))

    def test_year_rollover(self):
        with patch('scrapers.new_venues.date') as fake_date:
            fake_date.today.return_value=date(2026,10,8)
            fake_date.side_effect=date
            self.assertEqual(date_from_text("woensdag 7 april 2027"),"2027-04-07")


if __name__ == "__main__":
    unittest.main()
