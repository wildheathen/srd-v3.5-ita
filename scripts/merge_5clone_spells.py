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


# SRD uses generic names (without wizard names) for OGL compliance.
# This maps them to the full names used on 5clone.com.
SRD_NAME_ALIASES = {
    "acid arrow":                   "melf's acid arrow",
    "animal messenger":             "animal messenger",  # different entry
    "black tentacles":              "evard's black tentacles",
    "clenched fist":                "bigby's clenched fist",
    "crushing despair":             "crushing despair",
    "crushing hand":                "bigby's crushing hand",
    "floating disk":                "tenser's floating disk",
    "forceful hand":                "bigby's forceful hand",
    "freezing sphere":              "otiluke's freezing sphere",
    "globe of invulnerability, lesser": "lesser globe of invulnerability",
    "grasping hand":                "bigby's grasping hand",
    "hideous laughter":             "tasha's hideous laughter",
    "instant summons":              "drawmij's instant summons",
    "interposing hand":             "bigby's interposing hand",
    "irresistible dance":           "otto's irresistible dance",
    "mage's disjunction":           "mordenkainen's disjunction",
    "mage's faithful hound":        "mordenkainen's faithful hound",
    "mage's lucubration":           "mordenkainen's lucubration",
    "mage's magnificent mansion":   "mordenkainen's magnificent mansion",
    "mage's private sanctum":       "mordenkainen's private sanctum",
    "mage's sword":                 "mordenkainen's sword",
    "magic aura":                   "nystul's magic aura",
    "mnemonic enhancer":            "rary's mnemonic enhancer",
    "phantom trap":                 "nystul's phantom trap",
    "resilient sphere":             "otiluke's resilient sphere",
    "secret chest":                 "leomund's secret chest",
    "secure shelter":               "leomund's secure shelter",
    "telekinetic sphere":           "otiluke's telekinetic sphere",
    "telepathic bond":              "rary's telepathic bond",
    "tiny hut":                     "leomund's tiny hut",
    "transformation":               "tenser's transformation",
    "mage armor":                   "mage armor",
}


def normalize_name(name):
    """Normalize spell name for matching: lowercase, straight apostrophes.

    Handles Unicode curly quotes AND encoding artifacts (? before 's').
    """
    n = name.lower().strip()
    n = n.replace("\u2019", "'").replace("\u2018", "'")
    # 5clone sometimes has ? instead of apostrophe (encoding artifact)
    n = re.sub(r"\?s\b", "'s", n)
    return n


# Fix typos and dirty data from 5clone school field
SCHOOL_TYPO_FIXES = {
    "Illusiione":    "Illusione",
    "Negromanzia":   "Necromanzia",
    "Tramsutazione": "Trasmutazione",
    "Transmutazione":"Trasmutazione",
    "Trasmutasione": "Trasmutazione",
    "Ubvicazuibe":   "Invocazione",
    "Invocazione Oscurità": "Invocazione",
}

# Known valid Italian school names (for swap detection)
KNOWN_SCHOOLS_IT = {
    "Abiurazione", "Ammaliamento", "Divinazione", "Evocazione",
    "Illusione", "Invocazione", "Necromanzia", "Trasmutazione", "Universale",
}

# Level-like pattern: class abbreviations followed by numbers
_LEVEL_PATTERN = re.compile(
    r'^(?:Brd|Chr|Drd|Mag|Pal|Rgr|Str|Mag/Str|Str/Mag)\s+\d', re.IGNORECASE
)


def looks_like_level(s):
    """Return True if the string looks like a level entry (e.g. 'Chr 7')."""
    return bool(_LEVEL_PATTERN.match(s.strip()))


def looks_like_school(s):
    """Return True if the string starts with a known Italian school name."""
    word = re.split(r'[\s\(\[]', s.strip(), 1)[0]
    return word in KNOWN_SCHOOLS_IT or word in SCHOOL_TYPO_FIXES


def swap_school_level_if_needed(school_it, level_it):
    """Detect and correct swapped school/level fields from 5clone data.

    Some 5clone entries have school and level swapped. E.g.:
      school_it="Chr 1, Pal 1", level_it="Trasmutazione [Legale]"
    """
    if not school_it or not level_it:
        return school_it, level_it
    s = school_it.strip()
    l = level_it.strip()
    if looks_like_level(s) and looks_like_school(l):
        return l, s
    return school_it, level_it


def normalize_school_it(school_it):
    """Normalize Italian school string: fix typos, formatting issues."""
    if not school_it:
        return None
    s = school_it.strip()

    # Discard junk: "-", "Vedi descrizione", or level-like strings
    if s in ("-", "Vedi descrizione") or looks_like_level(s):
        return None

    # Fix known typos (check full string first, then just the school name part)
    if s in SCHOOL_TYPO_FIXES:
        s = SCHOOL_TYPO_FIXES[s]

    # Fix "Ammaliamento Charme" → "Ammaliamento (Charme)" (missing parens)
    s = re.sub(r'^(Ammaliamento)\s+(Charme|Compulsione)\b', r'\1 (\2)', s)

    # Fix double-paren format: "School (Sub) (Desc)" → "School (Sub) [Desc]"
    m = re.match(r'^(.+?)\s*\(([^)]+)\)\s*\(([^)]+)\)\s*$', s)
    if m:
        s = f"{m.group(1).strip()} ({m.group(2).strip()}) [{m.group(3).strip()}]"

    # Merge multiple [Desc1], [Desc2] into [Desc1, Desc2]
    # e.g. "Ammaliamento (Compulsione) [Influenza Mentale], [Sonoro]"
    brackets = re.findall(r'\[([^\]]+)\]', s)
    if len(brackets) > 1:
        merged = ", ".join(b.strip() for b in brackets)
        # Remove all bracket groups and trailing commas/spaces
        s = re.sub(r'\s*,?\s*\[[^\]]+\]', '', s).strip()
        s = s.rstrip(",").strip()
        s = f"{s} [{merged}]"

    # Remove any trailing commas left over
    s = re.sub(r',\s*$', '', s).strip()

    # Fix typos in the school part (before any parens/brackets)
    base = re.split(r'[\s\(\[]', s, 1)[0]
    if base in SCHOOL_TYPO_FIXES:
        s = SCHOOL_TYPO_FIXES[base] + s[len(base):]

    return s


def parse_school_it(school_it):
    """Normalize and parse Italian school string into components.

    Examples:
        "Trasmutazione"                                 → (school, None, None)
        "Invocazione [Forza]"                           → (school, None, descriptor)
        "Evocazione (Guarigione)"                       → (school, subschool, None)
        "Ammaliamento (Compulsione) [Influenza Mentale]" → (school, subschool, descriptor)
    """
    school_it = normalize_school_it(school_it)
    if not school_it:
        return None, None, None
    m = re.match(r'^(.+?)(?:\s*\(([^)]+)\))?\s*(?:\[([^\]]+)\])?\s*$', school_it)
    if not m:
        return school_it, None, None
    school = m.group(1).strip()
    subschool = m.group(2).strip() if m.group(2) else None
    descriptor = m.group(3).strip() if m.group(3) else None
    return school, subschool, descriptor


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

    # Build lookup tables (normalized: lowercase + straight apostrophes)
    spells_by_name = {}  # normalized EN name -> index in spells list
    for i, s in enumerate(spells):
        spells_by_name[normalize_name(s["name"])] = i

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

        # Detect and fix swapped school/level fields
        school_it, level_it = swap_school_level_if_needed(school_it, level_it)

        if not name_en:
            stats["no_name_en"] += 1
            # Use index_name as fallback for Italian name
            if not name_it:
                name_it = entry.get("index_name", "")
            continue

        # Track source distribution
        sc = source_code or "unknown"
        stats["sources_found"][sc] = stats["sources_found"].get(sc, 0) + 1

        # Try to match existing spell (normalized + SRD alias fallback)
        key = normalize_name(name_en)
        # Direct match or reverse alias: find SRD name that maps to this 5clone name
        matched_key = key if key in spells_by_name else None
        if not matched_key:
            for srd_name, full_name in SRD_NAME_ALIASES.items():
                if normalize_name(full_name) == key:
                    if srd_name in spells_by_name:
                        matched_key = srd_name
                        break
                    # Also try with normalized apostrophes
                    norm_srd = normalize_name(srd_name)
                    if norm_srd in spells_by_name:
                        matched_key = norm_srd
                        break

        if matched_key:
            idx = spells_by_name[matched_key]
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
                sch, sub, desc = parse_school_it(school_it)
                if sch:
                    spells_it_by_slug[slug]["school"] = sch
                else:
                    # Normalization returned None → remove stale junk from overlay
                    spells_it_by_slug[slug].pop("school", None)
                if sub:
                    spells_it_by_slug[slug]["subschool"] = sub
                else:
                    spells_it_by_slug[slug].pop("subschool", None)
                if desc:
                    spells_it_by_slug[slug]["descriptor"] = desc
                else:
                    spells_it_by_slug[slug].pop("descriptor", None)
                stats["updated_school"] += 1

            if level_it:
                spells_it_by_slug[slug]["level"] = level_it
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
                sch, sub, desc = parse_school_it(school_it)
                if sch:
                    it_entry["school"] = sch
                if sub:
                    it_entry["subschool"] = sub
                if desc:
                    it_entry["descriptor"] = desc
            if level_it:
                it_entry["level"] = level_it
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

    # ── Deduplicate SRD generic names vs wizard-named duplicates ──────
    # The SRD uses generic names (e.g. "Mage's Disjunction") while 5clone
    # uses full names ("Mordenkainen's Disjunction"). Previous merges may
    # have created both. Merge the 5clone data into the SRD entry and
    # remove the duplicate.
    spells_by_norm = {}
    for i, s in enumerate(spells):
        spells_by_norm[normalize_name(s["name"])] = i

    slugs_to_remove = set()
    dedup_count = 0
    for srd_name, full_name in SRD_NAME_ALIASES.items():
        srd_norm = normalize_name(srd_name)
        full_norm = normalize_name(full_name)
        if srd_norm in spells_by_norm and full_norm in spells_by_norm and srd_norm != full_norm:
            srd_idx = spells_by_norm[srd_norm]
            dup_idx = spells_by_norm[full_norm]
            srd_spell = spells[srd_idx]
            dup_spell = spells[dup_idx]

            # Transfer data from 5clone duplicate to SRD entry
            if dup_spell.get("source") and dup_spell["source"] != "unknown":
                srd_spell["source"] = dup_spell["source"]
            for field in ("manual_name", "reference", "summary_it"):
                if dup_spell.get(field) and not srd_spell.get(field):
                    srd_spell[field] = dup_spell[field]

            # Transfer Italian overlay from duplicate slug to SRD slug
            dup_slug = dup_spell["slug"]
            srd_slug = srd_spell["slug"]
            if dup_slug in spells_it_by_slug:
                dup_it = spells_it_by_slug[dup_slug]
                if srd_slug not in spells_it_by_slug:
                    spells_it_by_slug[srd_slug] = {"slug": srd_slug}
                for k, v in dup_it.items():
                    if k != "slug" and v:
                        spells_it_by_slug[srd_slug][k] = v
                del spells_it_by_slug[dup_slug]

            slugs_to_remove.add(dup_spell["slug"])
            dedup_count += 1

    # Also deduplicate encoding variants: "Fox?s Cunning" vs "Fox's Cunning"
    # Group spells by normalized name, merge duplicates
    by_norm = {}
    for s in spells:
        nn = normalize_name(s["name"])
        by_norm.setdefault(nn, []).append(s)

    for nn, group in by_norm.items():
        if len(group) < 2:
            continue
        # Prefer the entry with more data (non-empty school, source != SRD)
        group.sort(key=lambda s: (
            s.get("source", "SRD") != "SRD",  # non-SRD first
            bool(s.get("school")),
            bool(s.get("desc_html")),
        ), reverse=True)
        keep = group[0]
        for dup in group[1:]:
            # Transfer data from dup to keep
            for field in ("source", "manual_name", "reference", "summary_it"):
                if dup.get(field) and not keep.get(field):
                    keep[field] = dup[field]
            if dup.get("source") and dup["source"] != "SRD" and keep.get("source") == "SRD":
                keep["source"] = dup["source"]
            if dup.get("manual_name") and not keep.get("manual_name"):
                keep["manual_name"] = dup["manual_name"]
            # Transfer i18n overlay
            dup_slug = dup["slug"]
            keep_slug = keep["slug"]
            if dup_slug in spells_it_by_slug:
                dup_it = spells_it_by_slug[dup_slug]
                if keep_slug not in spells_it_by_slug:
                    spells_it_by_slug[keep_slug] = {"slug": keep_slug}
                for k, v in dup_it.items():
                    if k != "slug" and v:
                        spells_it_by_slug[keep_slug][k] = v
                del spells_it_by_slug[dup_slug]
            slugs_to_remove.add(dup_slug)
            dedup_count += 1

    if dedup_count:
        spells = [s for s in spells if s["slug"] not in slugs_to_remove]
        print(f"\n  Duplicati rimossi: {dedup_count}")

    # Sort alphabetically by name
    spells.sort(key=lambda s: s["name"].lower())

    # Post-merge cleanup: remove junk school values from overlay entries
    # that weren't touched by this merge (e.g. leftover meta-entries)
    junk_schools = {"-", "Vedi descrizione"}
    cleaned_schools = 0
    for slug, entry in spells_it_by_slug.items():
        sch = entry.get("school", "")
        if sch in junk_schools or looks_like_level(sch):
            entry.pop("school", None)
            entry.pop("subschool", None)
            entry.pop("descriptor", None)
            cleaned_schools += 1
    if cleaned_schools:
        print(f"  Scuole sporche ripulite: {cleaned_schools}")

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
