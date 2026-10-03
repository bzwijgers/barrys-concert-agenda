from pathlib import Path

SOURCE = Path("scraper.py")
text = SOURCE.read_text(encoding="utf-8")

headers = {
    "effenaar": "# ============================================================\n# EFFENAAR\n# ============================================================",
    "rotown": "# ============================================================\n# ROTOWN\n# ============================================================",
    "source013": "# ============================================================\n# 013\n# ============================================================",
    "paradiso": "# ============================================================\n# PARADISO\n# ============================================================",
    "baroeg": "# ============================================================\n# BAROEG\n# ============================================================",
    "central": "# ============================================================\n# CENTRALE DATABASE\n# ============================================================",
}

positions = {name: text.index(marker) for name, marker in headers.items()}
order = ["effenaar", "rotown", "source013", "paradiso", "baroeg", "central"]

scrapers = Path("scrapers")
scrapers.mkdir(exist_ok=True)
(scrapers / "__init__.py").write_text("", encoding="utf-8")

common = text[:positions["effenaar"]].rstrip() + "\n"
(scrapers / "common.py").write_text(common, encoding="utf-8")

for index, name in enumerate(order[:-1]):
    start = positions[name]
    end = positions[order[index + 1]]
    block = text[start:end].strip() + "\n"
    module = "from .common import *\n\n" + block
    (scrapers / f"{name}.py").write_text(module, encoding="utf-8")

central = text[positions["central"]:].lstrip()
new_main = """from datetime import datetime
import json

from scrapers.common import normalize_url
from scrapers.effenaar import scrape_effenaar
from scrapers.rotown import scrape_rotown
from scrapers.source013 import scrape_013
from scrapers.paradiso import scrape_paradiso
from scrapers.baroeg import scrape_baroeg


""" + central

SOURCE.write_text(new_main, encoding="utf-8")

# Temporary migration files remove themselves from the final branch diff.
Path("modularize_scraper.py").unlink(missing_ok=True)
Path(".github/workflows/modularize-scrapers.yml").unlink(missing_ok=True)

print("Modularization completed.")
