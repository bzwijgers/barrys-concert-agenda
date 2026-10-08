import unittest
from scrapers.paradiso import paradiso_parse_event, paradiso_event_key

class ParadisoParserTests(unittest.TestCase):
    def test_excelsior_ignores_recommendations(self):
        html = """<html><head><title>30 Jaar Excelsior Recordings in Tolhuistuin, Amsterdam | Paradiso</title></head><body>
        <h1>30 Jaar Excelsior Recordings</h1><div>zondag 27 december 2026</div>
        <div>In Tolhuistuin - Club, Zonzij, Club</div><div>Zaal open: 15:00, Hoofdprogramma: 16:00</div>
        <section>Programma <h2>This Is Lorelei</h2><div>In Tolhuistuin</div><div>23 februari</div>
        <script>{"startDate":"2027-02-23T19:30:00+01:00"}</script></section></body></html>"""
        r = paradiso_parse_event(html, "https://www.paradiso.nl/nl/programma/30-jaar-excelsior-recordings/2902321")
        self.assertEqual(("30 Jaar Excelsior Recordings","Tolhuistuin","Tolhuistuin","2026-12-27","16:00"),
                         (r["artist"],r["venue"],r["source"],r["date"],r["time"]))

    def test_honey_im_home(self):
        html = """<html><head><title>Honey I'm Home | Paradiso</title></head><body><h1>Honey I'm Home</h1>
        <div>woensdag 30 december 2026</div><div>In Tolhuistuin - Club</div>
        <div>Zaal open: 19:00, Hoofdprogramma: 20:30</div></body></html>"""
        r = paradiso_parse_event(html, "https://www.paradiso.nl/nl/programma/honey-im-home/2841259")
        self.assertEqual(("Honey I'm Home","Tolhuistuin","2026-12-30","20:30"),
                         (r["artist"],r["venue"],r["date"],r["time"]))

    def test_fat_freddys_drop(self):
        html = """<html><head><title>Fat Freddy's Drop + DJ Logg Cabin | Paradiso</title></head><body>
        <h1>Fat Freddy's Drop + DJ Logg Cabin</h1><div>maandag 12 oktober 2026</div>
        <div>In Paradiso - Grote Zaal</div><div>Zaal open: 19:00, Voorprogramma: 19:30, Hoofdprogramma: 20:30</div>
        </body></html>"""
        r = paradiso_parse_event(html, "https://www.paradiso.nl/nl/programma/fat-freddys-drop/2654360")
        self.assertEqual(("Fat Freddy's Drop + DJ Logg Cabin","Paradiso","2026-10-12","20:30"),
                         (r["artist"],r["venue"],r["date"],r["time"]))


    def test_this_is_the_kit_2027(self):
        html = """<html><head><title>This Is the Kit in Tolhuistuin op 7 mei 2027 | Paradiso</title></head><body>
        <h1>This Is the Kit</h1>
        <div>vrijdag 7 mei 2027</div><div>In Tolhuistuin - Club</div>
        <div>Zaal open: 19:00, Hoofdprogramma: 20:30</div>
        <section><h2>Aanbevolen</h2><div>In Paradiso</div><div>3 oktober 2027</div></section>
        </body></html>"""
        result = paradiso_parse_event(
            html, "https://www.paradiso.nl/nl/programma/this-is-the-kit/2931706"
        )
        self.assertIsNotNone(result)
        self.assertEqual(
            ("This Is the Kit", "Tolhuistuin", "Tolhuistuin", "2027-05-07", "20:30"),
            (result["artist"], result["venue"], result["source"], result["date"], result["time"]),
        )


    def test_songhoy_blues_not_lost(self):
        html = """<html><head><title>Songhoy Blues | Paradiso</title></head><body>
        <h1>Songhoy Blues</h1><div>zaterdag 10 oktober 2026</div>
        <div>In Tolhuistuin - Club</div>
        <div>Zaal open: 19:30, Hoofdprogramma: 20:30</div></body></html>"""
        result = paradiso_parse_event(
            html, "https://www.paradiso.nl/nl/programma/songhoy-blues/2884193"
        )
        self.assertEqual(
            ("Songhoy Blues", "Tolhuistuin", "2026-10-10", "20:30"),
            (result["artist"], result["venue"], result["date"], result["time"]),
        )

    def test_nl_en_urls_share_event_id(self):
        dutch = "https://www.paradiso.nl/nl/programma/tones-presents-juls-ade/2941966"
        english = "https://www.paradiso.nl/en/program/tones-presents-juls-ade/2941966"
        self.assertEqual(paradiso_event_key(dutch), paradiso_event_key(english))

    def test_english_paradiso_date_and_main_time(self):
        html = """<html><head><title>Tones Presents: Juls - ADE | Paradiso</title></head>
        <body><h1>Tones Presents: Juls - ADE</h1><div>Thursday 22 October 2026</div>
        <div>In Paradiso - Main Hall</div><div>Doors: 18:45, Main programme: 20:15</div></body></html>"""
        event = paradiso_parse_event(
            html, "https://www.paradiso.nl/en/program/tones-presents-juls-ade/2941966"
        )
        self.assertEqual(
            ("Tones Presents: Juls - ADE", "2026-10-22", "20:15", "Paradiso"),
            (event["artist"], event["date"], event["time"], event["source"]),
        )

if __name__ == "__main__":
    unittest.main()
