#!/usr/bin/env python3
"""
Parse the 5clone.com index pages (saved locally) to extract spell names
in Italian and English, plus their detail page URLs.

Produces: sources/contrib/5clone_spell_urls.json

Usage:
    python scripts/parse_5clone_index.py
"""

import json
import re
from pathlib import Path

from bs4 import BeautifulSoup

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTRIB = REPO_ROOT / "sources" / "contrib"
DATA_DIR = REPO_ROOT / "data"

ITA_INDEX = CONTRIB / "D&D 3.5 - incantesimi ita.html"
ENG_INDEX = CONTRIB / "D&D 3.5 - incantesimi ing.html"

OUTPUT = CONTRIB / "5clone_spell_urls.json"


def extract_spell_links(html_path, url_pattern):
    """Extract spell names and URLs from an index page."""
    with open(html_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    links = soup.find_all("a", href=True)
    spells = []
    seen = set()
    for a in links:
        href = a["href"]
        # Must contain the pattern AND have a /NNNNN-slug-name suffix (not just anchors)
        if url_pattern in href:
            match = re.search(r"/(\d+)-[^/#]+$", href)
            if not match:
                continue
            name = a.get_text(strip=True)
            if name and href not in seen:
                seen.add(href)
                entry_id = int(match.group(1))
                spells.append({
                    "name": name,
                    "url": href,
                    "id": entry_id,
                })
    return spells


def main():
    if not ITA_INDEX.exists():
        print(f"ERROR: File non trovato: {ITA_INDEX}")
        print("Salva la pagina indice italiana da 5clone.com in questa posizione.")
        return

    if not ENG_INDEX.exists():
        print(f"ERROR: File non trovato: {ENG_INDEX}")
        print("Salva la pagina indice inglese da 5clone.com in questa posizione.")
        return

    print("Parsing Italian index...")
    ita_spells = extract_spell_links(ITA_INDEX, "75-incantesimi-ita-35")
    print(f"  Found {len(ita_spells)} Italian spells")

    print("Parsing English index...")
    eng_spells = extract_spell_links(ENG_INDEX, "74-incantesimi-ing-35")
    print(f"  Found {len(eng_spells)} English spells")

    # Load existing spells.json to check matches
    spells_path = DATA_DIR / "spells.json"
    existing = {}
    if spells_path.exists():
        with open(spells_path, "r", encoding="utf-8") as f:
            for s in json.load(f):
                existing[s["name"].lower().strip()] = s["slug"]

    # Build English name lookup (lowercase -> original)
    eng_by_lower = {}
    for s in eng_spells:
        eng_by_lower[s["name"].lower().strip()] = s

    # Report SRD matches
    matched_srd = 0
    for s in eng_spells:
        if s["name"].lower().strip() in existing:
            matched_srd += 1

    print(f"\n  English spells matching existing SRD: {matched_srd}/{len(eng_spells)}")
    print(f"  New spells (not in SRD): {len(eng_spells) - matched_srd}")

    # Save combined data
    result = {
        "ita_spells": ita_spells,
        "eng_spells": eng_spells,
        "stats": {
            "ita_count": len(ita_spells),
            "eng_count": len(eng_spells),
            "srd_matches": matched_srd,
            "new_spells": len(eng_spells) - matched_srd,
        },
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\nSaved to {OUTPUT}")
    print(f"\nProssimo passo: esegui scripts/scrape_5clone.py sul tuo PC")
    print("per scaricare le pagine dettaglio con riferimento manuale e descrizione.")


if __name__ == "__main__":
    main()
