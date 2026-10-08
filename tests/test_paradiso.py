import unittest
from scrapers.paradiso import paradiso_parse_event

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

if __name__ == "__main__":
    unittest.main()
