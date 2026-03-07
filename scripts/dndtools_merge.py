#!/usr/bin/env python3
"""
Match & Merge — Update data/spells.json with English data from dndtools.net.

1. Match existing spells by name (case-insensitive) with dndtools data
2. Fill empty EN fields for existing spells
3. Fix Italian data in EN fields (manual_name, reference)
4. Add new spells not already present
5. Generate unmatched.csv for manual review

Usage:
    python scripts/dndtools_merge.py                           # dry-run (no changes)
    python scripts/dndtools_merge.py --apply                   # apply changes to spells.json
    python scripts/dndtools_merge.py --input custom.json       # custom input file
"""

import csv
import json
import os
import re
import sys
from difflib import SequenceMatcher

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPELLS_JSON = os.path.join(REPO_ROOT, "data", "spells.json")
DNDTOOLS_JSON = os.path.join(REPO_ROOT, "spells_en_final.json")

# Map dndtools source abbreviations to the ones used in existing data
# (we keep existing abbreviations for existing spells)
SOURCE_MAP_DNDTOOLS_TO_EXISTING = {
    "PHB": "PHB",
    "CArc": "CA",
    "CDiv": "CD",
    "CAd": "CAd",
    "DMG": "DMG",
    "SC": "SC",
    "PHB2": "PHB2",
}

# EN book names for updating manual_name
EN_BOOK_NAMES = {
    "PHB": "Player's Handbook v.3.5",
    "CA": "Complete Arcane",
    "CD": "Complete Divine",
    "CAd": "Complete Adventurer",
    "SC": "Spell Compendium",
    "PHB2": "Player's Handbook II",
    "DMG": "Dungeon Master's Guide v.3.5",
    "CArc": "Complete Arcane",
    "CDiv": "Complete Divine",
}

# Fields to fill from dndtools when empty in existing data
FILLABLE_FIELDS = [
    "school", "subschool", "descriptor", "level",
    "components", "casting_time", "range", "target_area_effect",
    "duration", "saving_throw", "spell_resistance", "desc_html",
]


def normalize_name(name):
    """Normalize spell name for matching."""
    # Lowercase, strip extra whitespace
    n = name.lower().strip()
    # Remove common variations
    n = n.replace("\u2019", "'")  # curly apostrophe
    n = n.replace("\u2018", "'")
    n = n.replace("\u201c", '"')
    n = n.replace("\u201d", '"')
    n = re.sub(r"\s+", " ", n)
    return n


# OGL name mappings: dndtools uses proper names, SRD strips them
# Map: "Proper's Spell" → SRD name variants to try
OGL_POSSESSIVE_PREFIXES = [
    "bigby's ", "drawmij's ", "evard's ", "leomund's ", "melf's ",
    "mordenkainen's ", "nystul's ", "otiluke's ", "otto's ", "rary's ",
    "tasha's ", "tenser's ",
]

# Special OGL renames where the SRD uses "Mage's X" instead of "Proper's X"
OGL_MAGE_MAP = {
    "mordenkainen's disjunction": "mage's disjunction",
    "mordenkainen's faithful hound": "mage's faithful hound",
    "mordenkainen's lucubration": "mage's lucubration",
    "mordenkainen's magnificent mansion": "mage's magnificent mansion",
    "mordenkainen's private sanctum": "mage's private sanctum",
    "mordenkainen's sword": "mage's sword",
}


def ogl_variants(name_norm):
    """Generate OGL name variants for a normalized spell name.
    Returns a list of alternative names to try for matching."""
    variants = []

    # Check mage's map first (specific renames)
    if name_norm in OGL_MAGE_MAP:
        variants.append(OGL_MAGE_MAP[name_norm])

    # Strip possessive prefix: "bigby's clenched fist" → "clenched fist"
    for prefix in OGL_POSSESSIVE_PREFIXES:
        if name_norm.startswith(prefix):
            stripped = name_norm[len(prefix):]
            variants.append(stripped)
            break

    return variants


def slugify(name):
    """Create a slug from a spell name."""
    s = name.lower().strip()
    s = re.sub(r"['\u2019]", "", s)
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    return s


def similarity(a, b):
    """String similarity ratio."""
    return SequenceMatcher(None, a, b).ratio()


def format_level(level_str):
    """Convert dndtools level format to existing format.
    dndtools: 'Sorcerer 6, Wizard 6, Warmage 6'
    existing: 'Sor/Wiz 6'  (abbreviated)
    We keep the dndtools format as-is since it's more complete.
    """
    return level_str


def merge_spells(existing, dndtools, apply=False):
    """Merge dndtools data into existing spells."""
    # Build index of existing spells by normalized name
    existing_by_name = {}
    for i, spell in enumerate(existing):
        norm = normalize_name(spell["name"])
        if norm not in existing_by_name:
            existing_by_name[norm] = []
        existing_by_name[norm].append(i)

    # Track results
    matched = []       # (existing_idx, dndtools_spell, match_type)
    unmatched_en = []   # dndtools spells with no match in existing
    updated_fields = {} # field -> count of updates

    for dt_spell in dndtools:
        dt_name = normalize_name(dt_spell["name"])
        found = False

        if dt_name in existing_by_name:
            # Direct match
            for idx in existing_by_name[dt_name]:
                matched.append((idx, dt_spell, "exact"))
            found = True
        else:
            # Try OGL name variants (e.g., "Bigby's Clenched Fist" → "Clenched Fist")
            for variant in ogl_variants(dt_name):
                if variant in existing_by_name:
                    for idx in existing_by_name[variant]:
                        matched.append((idx, dt_spell, "ogl"))
                    found = True
                    break

        if not found:
            # Try high-similarity fuzzy match (catches typos, >0.95)
            best_sim = 0
            best_candidate = ""
            best_idx = None
            for ex_name, indices in existing_by_name.items():
                sim = similarity(dt_name, ex_name)
                if sim > best_sim:
                    best_sim = sim
                    best_candidate = ex_name
                    best_idx = indices

            if best_sim >= 0.95 and best_idx:
                # Typo match — high confidence
                for idx in best_idx:
                    matched.append((idx, dt_spell, "fuzzy"))
                found = True
            else:
                unmatched_en.append({
                    "name": dt_spell["name"],
                    "source": dt_spell.get("source", ""),
                    "source_book": dt_spell.get("source_book", ""),
                    "best_candidate": best_candidate,
                    "similarity": round(best_sim, 3),
                })

    # Apply updates to matched spells
    changes = []
    for ex_idx, dt_spell, match_type in matched:
        ex_spell = existing[ex_idx]
        spell_changes = []

        # 1. Update manual_name to English
        dt_source = dt_spell.get("source", "")
        ex_source = ex_spell.get("source", "")
        en_book_name = dt_spell.get("source_book", "") or EN_BOOK_NAMES.get(dt_source, "")
        if en_book_name and ex_spell.get("manual_name", "") != en_book_name:
            old_val = ex_spell.get("manual_name", "")
            spell_changes.append(("manual_name", old_val, en_book_name))
            if apply:
                ex_spell["manual_name"] = en_book_name

        # 2. Update reference to English format
        dt_page = dt_spell.get("source_page", "")
        if dt_page:
            new_ref = f"p. {dt_page}"
            old_ref = ex_spell.get("reference", "")
            if old_ref != new_ref:
                spell_changes.append(("reference", old_ref, new_ref))
                if apply:
                    ex_spell["reference"] = new_ref

        # 3. Fill empty structural fields
        for field in FILLABLE_FIELDS:
            ex_val = ex_spell.get(field, "")
            dt_val = dt_spell.get(field, "")
            # Fill if existing is empty and dndtools has data
            if not ex_val and dt_val:
                spell_changes.append((field, ex_val, dt_val[:80] + ("..." if len(dt_val) > 80 else "")))
                if apply:
                    ex_spell[field] = dt_val
                updated_fields[field] = updated_fields.get(field, 0) + 1

        # 4. Add alt_name for OGL/fuzzy matches (different name in dndtools)
        if match_type in ("ogl", "fuzzy"):
            dt_original_name = dt_spell.get("name", "")
            if dt_original_name and dt_original_name != ex_spell.get("name", ""):
                existing_alt = ex_spell.get("alt_name", "")
                if existing_alt != dt_original_name:
                    spell_changes.append(("alt_name", existing_alt, dt_original_name))
                    if apply:
                        ex_spell["alt_name"] = dt_original_name

        if spell_changes:
            changes.append((ex_spell["name"], ex_source, spell_changes))

    # Find existing spells not matched by any dndtools spell
    matched_indices = set(idx for idx, _, _ in matched)
    unmatched_existing = []
    for i, spell in enumerate(existing):
        if i not in matched_indices:
            # Only report non-PHB spells without desc_html
            if not spell.get("desc_html"):
                unmatched_existing.append({
                    "name": spell["name"],
                    "source": spell.get("source", ""),
                })

    # New spells to add (from unmatched dndtools spells)
    new_spells = []
    for um in unmatched_en:
        # Find the original dndtools spell
        dt_spell = None
        for s in dndtools:
            if s["name"] == um["name"] and s.get("source", "") == um["source"]:
                dt_spell = s
                break
        if not dt_spell:
            continue

        new_spell = {
            "name": dt_spell["name"],
            "slug": slugify(dt_spell["name"]),
            "school": dt_spell.get("school", ""),
            "subschool": dt_spell.get("subschool"),
            "descriptor": dt_spell.get("descriptor"),
            "level": dt_spell.get("level", ""),
            "components": dt_spell.get("components", ""),
            "casting_time": dt_spell.get("casting_time", ""),
            "range": dt_spell.get("range", ""),
            "target_area_effect": dt_spell.get("target_area_effect", ""),
            "duration": dt_spell.get("duration", ""),
            "saving_throw": dt_spell.get("saving_throw", ""),
            "spell_resistance": dt_spell.get("spell_resistance", ""),
            "desc_html": dt_spell.get("desc_html", ""),
            "source": SOURCE_MAP_DNDTOOLS_TO_EXISTING.get(dt_spell.get("source", ""), dt_spell.get("source", "")),
            "manual_name": dt_spell.get("source_book", ""),
            "reference": f"p. {dt_spell['source_page']}" if dt_spell.get("source_page") else "",
            "summary_it": "",
        }
        new_spells.append(new_spell)

    if apply:
        existing.extend(new_spells)

    return {
        "matched_count": len(set(idx for idx, _, _ in matched)),
        "changes": changes,
        "updated_fields": updated_fields,
        "unmatched_en": unmatched_en,
        "unmatched_existing": unmatched_existing,
        "new_spells": new_spells,
    }


def main():
    args = sys.argv[1:]
    apply = "--apply" in args
    input_file = DNDTOOLS_JSON

    for i, arg in enumerate(args):
        if arg == "--input" and i + 1 < len(args):
            input_file = args[i + 1]

    print(f"D&D Tools Spell Merger")
    print(f"Existing: {SPELLS_JSON}")
    print(f"Dndtools: {input_file}")
    print(f"Mode: {'APPLY' if apply else 'DRY-RUN'}")
    print()

    # Load data
    with open(SPELLS_JSON, "r", encoding="utf-8") as f:
        existing = json.load(f)
    print(f"Existing spells: {len(existing)}")

    with open(input_file, "r", encoding="utf-8") as f:
        dndtools = json.load(f)
    print(f"Dndtools spells: {len(dndtools)}")

    # Merge
    result = merge_spells(existing, dndtools, apply=apply)

    print(f"\n{'='*60}")
    print(f"RESULTS")
    print(f"{'='*60}")
    print(f"Matched:           {result['matched_count']}")
    print(f"Changes needed:    {len(result['changes'])}")
    print(f"New spells:        {len(result['new_spells'])}")
    print(f"Unmatched (EN):    {len(result['unmatched_en'])}")
    print(f"Unmatched (exist): {len(result['unmatched_existing'])}")

    if result["updated_fields"]:
        print(f"\nFields filled:")
        for field, count in sorted(result["updated_fields"].items(), key=lambda x: -x[1]):
            print(f"  {field}: {count}")

    # Show sample changes
    if result["changes"]:
        print(f"\nSample changes (first 10):")
        for name, source, field_changes in result["changes"][:10]:
            print(f"\n  {name} ({source}):")
            for field, old, new in field_changes:
                old_display = old[:40] + "..." if len(str(old)) > 40 else old
                new_display = new[:40] + "..." if len(str(new)) > 40 else new
                print(f"    {field}: '{old_display}' -> '{new_display}'")

    # Show sample new spells
    if result["new_spells"]:
        print(f"\nSample new spells (first 10):")
        for spell in result["new_spells"][:10]:
            print(f"  {spell['name']} ({spell['source']}) - {spell['school']}")

    # Write unmatched CSV
    if result["unmatched_en"]:
        csv_file = os.path.join(REPO_ROOT, "unmatched_en.csv")
        with open(csv_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["name", "source", "source_book", "best_candidate", "similarity"])
            writer.writeheader()
            writer.writerows(result["unmatched_en"])
        print(f"\nUnmatched EN spells written to: {csv_file}")

    if result["unmatched_existing"]:
        csv_file = os.path.join(REPO_ROOT, "unmatched_existing.csv")
        with open(csv_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["name", "source"])
            writer.writeheader()
            writer.writerows(result["unmatched_existing"])
        print(f"Unmatched existing spells written to: {csv_file}")

    # Apply changes
    if apply:
        # Sort by name
        existing.sort(key=lambda s: s["name"].lower())

        with open(SPELLS_JSON, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2, ensure_ascii=False)
        print(f"\nUpdated {SPELLS_JSON}")
        print(f"Total spells: {len(existing)}")
    else:
        print(f"\nDry-run complete. Use --apply to write changes.")


if __name__ == "__main__":
    main()
