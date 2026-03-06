#!/usr/bin/env python3
"""Esporta entry non tradotte in formato CSV per facilitare le traduzioni.

Genera un file CSV con le entry che mancano di traduzione per un dato
campo, consentendo ai contributori di lavorare in un foglio di calcolo
(Google Sheets, Excel, LibreOffice) anziche editare JSON a mano.

Usage:
    python scripts/export_for_translation.py monsters desc_html
    python scripts/export_for_translation.py rules desc_html
    python scripts/export_for_translation.py classes desc_html
    python scripts/export_for_translation.py feats desc_html
    python scripts/export_for_translation.py spells desc_html    # solo i 32 troncati

Output: contrib/{category}_{field}.csv
"""

import csv
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
CONTRIB_DIR = ROOT / "contrib"

# Spell slugs con desc_html troncata (per filtro speciale)
TRUNCATED_SPELLS = {
    "contact-other-plane", "control-weather", "control-winds", "detect-evil",
    "detect-undead", "enthrall", "forbiddance", "gate", "guards-and-wards",
    "helping-hand", "imbue-with-spell-ability", "magic-circle-against-evil",
    "permanency", "prismatic-wall", "reincarnate", "secure-shelter",
    "shadow-conjuration", "shadow-walk", "speak-with-dead", "spell-turning",
    "spiritual-weapon", "summon-monster-ix", "summon-natures-ally-ix",
    "symbol-of-death", "telekinetic-sphere", "teleport", "transmute-rock-to-mud",
    "transport-via-plants", "tree-stride", "wall-of-iron", "wall-of-thorns", "wish",
}


def truncate(text, max_len=200):
    """Truncate text for preview column."""
    if not text:
        return ""
    text = text.replace("\n", " ").strip()
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."


def export_category(category, field):
    en_path = DATA_DIR / f"{category}.json"
    it_path = DATA_DIR / "i18n" / "it" / f"{category}.json"

    if not en_path.exists():
        print(f"Errore: {en_path} non trovato")
        sys.exit(1)

    with open(en_path, encoding="utf-8") as f:
        en_data = json.load(f)

    it_data = []
    if it_path.exists():
        with open(it_path, encoding="utf-8") as f:
            it_data = json.load(f)

    it_by_slug = {e["slug"]: e for e in it_data}

    # Filter entries
    rows = []
    for en_entry in en_data:
        slug = en_entry.get("slug", "")
        if not slug:
            continue

        en_value = en_entry.get(field, "")
        if not en_value:
            continue

        it_entry = it_by_slug.get(slug, {})
        it_value = it_entry.get(field, "")

        # For spells desc_html, only export the 32 truncated ones
        if category == "spells" and field == "desc_html":
            if slug not in TRUNCATED_SPELLS:
                continue
        # For other categories, export entries missing the field
        elif it_value and field != "desc_html":
            continue  # Already translated
        elif it_value and field == "desc_html":
            # Detect structural-only translations (labels/headers in IT, prose in EN)
            import re
            text_only = re.sub(r'<[^>]+>', '', it_value)
            en_words = re.findall(
                r'\b(the|and|of|in|at|from|with|or|by|as|to|an|is|on|for|that|this|'
                r'can|you|not|are|all|its|has|but|will|which|each|if|may|be|any|'
                r'creature|damage|attack|spell|level|hit|points|save|check|round|'
                r'ability|bonus|feet|within|against|must|succeed|effect|target)\b',
                text_only, re.IGNORECASE
            )
            total_words = len(text_only.split())
            if total_words > 0:
                en_ratio = len(en_words) / total_words
                if en_ratio < 0.05:
                    continue  # Mostly translated, skip

        rows.append({
            "slug": slug,
            "name_en": en_entry.get("name", slug),
            "name_it": it_entry.get("name", ""),
            f"{field}_en_preview": truncate(en_value, 300),
            f"{field}_it": it_value if it_value else "",
        })

    if not rows:
        print(f"Nessuna entry da tradurre per {category}/{field}")
        return

    # Write CSV
    CONTRIB_DIR.mkdir(exist_ok=True)
    out_path = CONTRIB_DIR / f"{category}_{field}.csv"

    with open(out_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"Esportate {len(rows)} entry in {out_path}")
    print(f"\nPer tradurre:")
    print(f"  1. Apri il CSV in un foglio di calcolo")
    print(f"  2. Compila la colonna '{field}_it' per ogni riga")
    print(f"  3. Salva il CSV e importa con:")
    print(f"     python scripts/import_from_csv.py {out_path} {category}")


def main():
    if len(sys.argv) < 3:
        print("Uso: python scripts/export_for_translation.py <categoria> <campo>")
        print("  Categorie: spells, feats, classes, races, monsters, equipment, rules")
        print("  Campi: desc_html, organization, table_html, benefit, ...")
        print()
        print("Esempi:")
        print("  python scripts/export_for_translation.py monsters desc_html")
        print("  python scripts/export_for_translation.py rules desc_html")
        sys.exit(1)

    category = sys.argv[1]
    field = sys.argv[2]
    export_category(category, field)


if __name__ == "__main__":
    main()
