#!/usr/bin/env python3
"""
Merge scraped 5clone.com spell data into the Crystal Ball data files.

This script:
1. Reads the scraped data from sources/contrib/5clone_spells_raw.json
2. Matches existing SRD spells by English name
3. Updates existing spells with source/reference info
4. Creates skeleton entries for new spells
5. Updates data/spells.json, data/i18n/it/spells.json, and data/sources.json

Usage:
    python scripts/merge_5clone_spells.py              # full merge
    python scripts/merge_5clone_spells.py --dry-run    # preview without writing
    python scripts/merge_5clone_spells.py --stats      # show statistics only
"""

import argparse
import json
import re
import unicodedata
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
I18N_DIR = DATA_DIR / "i18n" / "it"
CONTRIB = REPO_ROOT / "sources" / "contrib"

SCRAPED_FILE = CONTRIB / "5clone_spells_raw.json"
SPELLS_FILE = DATA_DIR / "spells.json"
SPELLS_IT_FILE = I18N_DIR / "spells.json"
SOURCES_FILE = DATA_DIR / "sources.json"

# Full manual info for sources.json
MANUAL_INFO = {
    "PHB":  {"name_en": "Player's Handbook",       "name_it": "Manuale del Giocatore 3.5",          "abbreviation": "PHB", "abbreviation_it": "MdG"},
    "CW":   {"name_en": "Complete Warrior",         "name_it": "Perfetto Combattente",               "abbreviation": "CW",  "abbreviation_it": "PC"},
    "CD":   {"name_en": "Complete Divine",           "name_it": "Perfetto Sacerdote",                 "abbreviation": "CD",  "abbreviation_it": "PS"},
    "CA":   {"name_en": "Complete Arcane",           "name_it": "Perfetto Arcanista",                 "abbreviation": "CA",  "abbreviation_it": "PA"},
    "CAd":  {"name_en": "Complete Adventurer",       "name_it": "Perfetto Avventuriero",              "abbreviation": "CAd", "abbreviation_it": "PAv"},
    "RoS":  {"name_en": "Races of Stone",            "name_it": "Razze di Pietra",                    "abbreviation": "RoS", "abbreviation_it": "RdP"},
    "RoD":  {"name_en": "Races of Destiny",          "name_it": "Razze del Destino",                  "abbreviation": "RoD", "abbreviation_it": "RdD"},
    "BoED": {"name_en": "Book of Exalted Deeds",     "name_it": "Libro delle Imprese Eroiche",        "abbreviation": "BoED","abbreviation_it": "LIE"},
    "PlH":  {"name_en": "Planar Handbook",           "name_it": "Atlante Planare",                    "abbreviation": "PlH", "abbreviation_it": "AP"},
    "Drac": {"name_en": "Draconomicon",              "name_it": "Draconomicon",                       "abbreviation": "Drac","abbreviation_it": "Drac"},
    "LM":   {"name_en": "Libris Mortis",             "name_it": "Liber Mortis",                       "abbreviation": "LM",  "abbreviation_it": "LM"},
    "LoM":  {"name_en": "Lords of Madness",           "name_it": "Signori della Follia",               "abbreviation": "LoM", "abbreviation_it": "SdF"},
    "HoH":  {"name_en": "Heroes of Horror",           "name_it": "Eroi dell'Orrore",                   "abbreviation": "HoH", "abbreviation_it": "EdO"},
    "FC1":  {"name_en": "Fiendish Codex I",           "name_it": "Codex Immondo I: Orde dell'Abisso",  "abbreviation": "FC1", "abbreviation_it": "CI1"},
}


def slugify(text):
    """Generate a URL-friendly slug from text."""
    text = text.strip().lower()
    # Normalize unicode
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    # Replace non-alphanumeric with hyphens
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    return text


def load_json(path):
    """Load JSON file, return empty list/dict if not found."""
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_json(path, data):
    """Save JSON with consistent formatting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  Saved: {path}")


def main():
    parser = argparse.ArgumentParser(description="Merge 5clone spell data")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing files")
    parser.add_argument("--stats", action="store_true", help="Show statistics only")
    args = parser.parse_args()

    if not SCRAPED_FILE.exists():
        print(f"ERROR: {SCRAPED_FILE} non trovato.")
        print("Esegui prima: python scripts/scrape_5clone.py")
        return

    # Fix known typos/errors from 5clone.com
    SOURCE_FIXES = {
        "Manuale del Giocatere 3.5": ("PHB", "Manuale del Giocatore 3.5"),
        "Visione del Paradiso": ("BoED", "Libro delle Imprese Eroiche"),
    }

    # Load data
    scraped = load_json(SCRAPED_FILE)

    # Apply source fixes
    for entry in scraped:
        mn = entry.get("manual_name", "")
        if mn in SOURCE_FIXES:
            code, fixed_name = SOURCE_FIXES[mn]
            entry["source_code"] = code
            entry["manual_name"] = fixed_name
    spells = load_json(SPELLS_FILE)
    spells_it = load_json(SPELLS_IT_FILE)
    sources = load_json(SOURCES_FILE)
    if isinstance(sources, list):
        sources = {}

    # Build lookup tables
    spells_by_name = {}  # lowercase EN name -> index in spells list
    for i, s in enumerate(spells):
        spells_by_name[s["name"].lower().strip()] = i

    spells_it_by_slug = {s["slug"]: s for s in spells_it}

    # Statistics
    stats = {
        "total_scraped": len(scraped),
        "matched_existing": 0,
        "new_spells": 0,
        "updated_source": 0,
        "updated_reference": 0,
        "updated_it_name": 0,
        "updated_summary": 0,
        "updated_school": 0,
        "updated_level": 0,
        "sources_found": {},
        "no_name_en": 0,
    }

    new_spells = []

    for entry in scraped:
        name_en = entry.get("name_en", "").strip()
        name_it = entry.get("name_it", "").strip()
        source_code = entry.get("source_code", "")
        manual_name = entry.get("manual_name", "")
        page = entry.get("page")
        summary_it = entry.get("summary_it", "").strip()
        school_it = entry.get("school_it", "").strip()
        level_it = entry.get("level_it", "").strip()

        if not name_en:
            stats["no_name_en"] += 1
            # Use index_name as fallback for Italian name
            if not name_it:
                name_it = entry.get("index_name", "")
            continue

        # Track source distribution
        sc = source_code or "unknown"
        stats["sources_found"][sc] = stats["sources_found"].get(sc, 0) + 1

        # Try to match existing spell
        key = name_en.lower().strip()
        if key in spells_by_name:
            idx = spells_by_name[key]
            spell = spells[idx]
            stats["matched_existing"] += 1

            # Update source if more specific than SRD
            if source_code and spell.get("source", "SRD") == "SRD":
                spell["source"] = source_code
                stats["updated_source"] += 1

            # Add manual_name (full Italian manual name)
            if manual_name:
                spell["manual_name"] = manual_name

            # Add reference (page number)
            if page:
                spell["reference"] = f"pag. {page}"
                stats["updated_reference"] += 1

            # Update Italian overlay
            slug = spell["slug"]
            if slug not in spells_it_by_slug:
                spells_it_by_slug[slug] = {"slug": slug}

            if name_it:
                spells_it_by_slug[slug]["name"] = name_it
                stats["updated_it_name"] += 1

            if summary_it:
                spells_it_by_slug[slug]["summary_it"] = summary_it
                spell["summary_it"] = summary_it
                stats["updated_summary"] += 1

            if school_it:
                spells_it_by_slug[slug]["school_it"] = school_it
                stats["updated_school"] += 1

            if level_it:
                spells_it_by_slug[slug]["level_it"] = level_it
                stats["updated_level"] += 1

        else:
            # New spell - create skeleton entry
            slug = slugify(name_en)

            # Avoid duplicate slugs
            base_slug = slug
            counter = 2
            existing_slugs = {s["slug"] for s in spells}
            while slug in existing_slugs:
                slug = f"{base_slug}-{counter}"
                counter += 1

            new_spell = {
                "name": name_en,
                "slug": slug,
                "school": "",
                "subschool": None,
                "descriptor": None,
                "level": "",
                "components": "",
                "casting_time": "",
                "range": "",
                "target_area_effect": "",
                "duration": "",
                "saving_throw": "",
                "spell_resistance": "",
                "desc_html": "",
                "source": source_code or "unknown",
                "manual_name": manual_name or "",
                "reference": f"pag. {page}" if page else "",
                "summary_it": summary_it,
            }
            new_spells.append(new_spell)
            existing_slugs.add(slug)

            # Add Italian overlay for new spell
            it_entry = {"slug": slug}
            if name_it:
                it_entry["name"] = name_it
            if summary_it:
                it_entry["summary_it"] = summary_it
            if school_it:
                it_entry["school_it"] = school_it
            if level_it:
                it_entry["level_it"] = level_it
            spells_it_by_slug[slug] = it_entry

            stats["new_spells"] += 1

    # Print statistics
    print("=" * 60)
    print("STATISTICHE MERGE")
    print("=" * 60)
    print(f"  Incantesimi scraped:        {stats['total_scraped']}")
    print(f"  Match con SRD esistenti:    {stats['matched_existing']}")
    print(f"  Nuovi incantesimi:          {stats['new_spells']}")
    print(f"  Senza nome inglese:         {stats['no_name_en']}")
    print(f"  Source aggiornate:          {stats['updated_source']}")
    print(f"  Riferimenti aggiunti:       {stats['updated_reference']}")
    print(f"  Nomi IT aggiunti:           {stats['updated_it_name']}")
    print(f"  Descrizioni sommarie:       {stats['updated_summary']}")
    print(f"  Scuole IT aggiunte:         {stats['updated_school']}")
    print(f"  Livelli IT aggiunti:        {stats['updated_level']}")
    print()
    print("  Distribuzione per manuale:")
    for src, count in sorted(stats["sources_found"].items(), key=lambda x: -x[1]):
        name = MANUAL_INFO.get(src, {}).get("name_it", src)
        print(f"    {src:6s} ({name}): {count}")

    if args.stats:
        return

    if args.dry_run:
        print("\n[DRY RUN] Nessun file modificato.")
        return

    # Merge new spells into spells list
    spells.extend(new_spells)
    # Sort alphabetically by name
    spells.sort(key=lambda s: s["name"].lower())

    # Rebuild Italian overlay list
    spells_it = sorted(spells_it_by_slug.values(), key=lambda s: s["slug"])

    # Update sources.json
    for code, info in MANUAL_INFO.items():
        if code not in sources:
            sources[code] = info

    # Save all files
    print("\nSalvataggio file:")
    save_json(SPELLS_FILE, spells)
    save_json(SPELLS_IT_FILE, spells_it)
    save_json(SOURCES_FILE, sources)

    total = len(spells)
    print(f"\nTotale incantesimi in spells.json: {total}")
    print("Done!")


if __name__ == "__main__":
    main()
