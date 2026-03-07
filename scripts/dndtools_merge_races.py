#!/usr/bin/env python3
"""
Match & Merge -- Update data/races.json with English data from dndtools.net.

1. Match existing races by name (case-insensitive, with plural/singular variants)
2. For matched races: add new fields (size, speed, ability_adjustments,
   level_adjustment, source_book, source_page, source_url, edition, source_site),
   update desc_html if richer
3. For new races: create complete entry
4. Generate unmatched CSV for manual review

Usage:
    python scripts/dndtools_merge_races.py                  # dry-run (no changes)
    python scripts/dndtools_merge_races.py --apply           # apply changes
    python scripts/dndtools_merge_races.py --input custom.json
"""

import csv
import json
import os
import re
import sys
from difflib import SequenceMatcher

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RACES_JSON = os.path.join(REPO_ROOT, "data", "races.json")
DNDTOOLS_JSON = os.path.join(REPO_ROOT, "data", "dndtools", "races_en_parsed.json")

# Fields from dndtools that should be added to matched existing races
NEW_FIELDS = [
    "size", "speed", "ability_adjustments", "level_adjustment",
    "source_book", "source_page", "source_url", "edition", "source_site",
]


def normalize_name(name):
    """Normalize race name for matching."""
    n = name.lower().strip()
    n = n.replace("\u2019", "'")
    n = n.replace("\u2018", "'")
    n = re.sub(r"\s+", " ", n)
    return n


def name_variants(name_norm):
    """Generate name variants for matching (singular/plural, etc.)."""
    variants = [name_norm]

    # Plural → singular mappings common in D&D race names
    # "Dwarves" → "Dwarf", "Elves" → "Elf", "Gnomes" → "Gnome", etc.
    if name_norm.endswith("ves"):
        # dwarves → dwarf, elves → elf, halves → half
        variants.append(name_norm[:-3] + "f")
    if name_norm.endswith("es"):
        variants.append(name_norm[:-2])
        variants.append(name_norm[:-1])
    if name_norm.endswith("s") and not name_norm.endswith("ss"):
        variants.append(name_norm[:-1])

    # Singular → plural
    if name_norm.endswith("f"):
        variants.append(name_norm[:-1] + "ves")
    variants.append(name_norm + "s")
    variants.append(name_norm + "es")

    # "Half-Elves" ↔ "Half-Elf", "Half-Orcs" ↔ "Half-Orc"
    if "-" in name_norm:
        parts = name_norm.split("-")
        for i, part in enumerate(parts):
            new_parts = list(parts)
            if part.endswith("ves"):
                new_parts[i] = part[:-3] + "f"
                variants.append("-".join(new_parts))
            if part.endswith("es"):
                new_parts[i] = part[:-2]
                variants.append("-".join(new_parts))
                new_parts[i] = part[:-1]
                variants.append("-".join(new_parts))
            if part.endswith("s") and not part.endswith("ss"):
                new_parts[i] = part[:-1]
                variants.append("-".join(new_parts))

    return list(set(variants))


def slugify(name):
    """Create a slug from a race name."""
    s = name.lower().strip()
    s = re.sub(r"['\u2019]", "", s)
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    return s


def similarity(a, b):
    """String similarity ratio."""
    return SequenceMatcher(None, a, b).ratio()


def merge_races(existing, dndtools, apply=False):
    """Merge dndtools data into existing races."""
    # Build index of existing races by normalized name and variants
    existing_by_name = {}
    for i, race in enumerate(existing):
        norm = normalize_name(race["name"])
        for variant in name_variants(norm):
            if variant not in existing_by_name:
                existing_by_name[variant] = []
            existing_by_name[variant].append(i)

    # Track results
    matched = []       # (existing_idx, dndtools_race, match_type)
    unmatched_dt = []  # dndtools races with no match in existing

    for dt_race in dndtools:
        dt_name = normalize_name(dt_race["name"])
        found = False

        # Try direct match and variants
        for variant in name_variants(dt_name):
            if variant in existing_by_name:
                for idx in existing_by_name[variant]:
                    matched.append((idx, dt_race, "name"))
                found = True
                break

        if not found:
            # Try fuzzy match (>0.90 similarity)
            best_sim = 0
            best_candidate = ""
            best_idx = None
            for ex_name, indices in existing_by_name.items():
                sim = similarity(dt_name, ex_name)
                if sim > best_sim:
                    best_sim = sim
                    best_candidate = ex_name
                    best_idx = indices

            if best_sim >= 0.90 and best_idx:
                for idx in best_idx:
                    matched.append((idx, dt_race, "fuzzy"))
                found = True
            else:
                unmatched_dt.append({
                    "name": dt_race["name"],
                    "source": dt_race.get("source", ""),
                    "source_book": dt_race.get("source_book", ""),
                    "best_candidate": best_candidate,
                    "similarity": round(best_sim, 3),
                })

    # Apply updates to matched races
    changes = []
    for ex_idx, dt_race, match_type in matched:
        ex_race = existing[ex_idx]
        race_changes = []

        # Add new fields that don't exist yet
        for field in NEW_FIELDS:
            dt_val = dt_race.get(field, "")
            ex_val = ex_race.get(field, "")
            if dt_val and not ex_val:
                display_val = str(dt_val)[:60]
                race_changes.append((field, "", display_val))
                if apply:
                    ex_race[field] = dt_val

        # Update desc_html if existing is empty and dndtools has content
        dt_desc = dt_race.get("desc_html", "")
        ex_desc = ex_race.get("desc_html", "")
        if dt_desc and not ex_desc:
            race_changes.append(("desc_html", "(empty)", dt_desc[:60] + "..."))
            if apply:
                ex_race["desc_html"] = dt_desc

        # Update traits if existing is empty and dndtools has content
        dt_traits = dt_race.get("traits", [])
        ex_traits = ex_race.get("traits", [])
        if dt_traits and not ex_traits:
            race_changes.append(("traits", "(empty)", f"{len(dt_traits)} traits"))
            if apply:
                ex_race["traits"] = dt_traits

        if race_changes:
            changes.append((ex_race["name"], ex_race.get("source", ""), race_changes))

    # New races to add (from unmatched dndtools races)
    new_races = []
    for um in unmatched_dt:
        dt_race = None
        for r in dndtools:
            if r["name"] == um["name"] and r.get("source", "") == um["source"]:
                dt_race = r
                break
        if not dt_race:
            continue

        new_race = {
            "name": dt_race["name"],
            "slug": slugify(dt_race["name"]),
            "size": dt_race.get("size", ""),
            "speed": dt_race.get("speed", ""),
            "ability_adjustments": dt_race.get("ability_adjustments", "None"),
            "level_adjustment": dt_race.get("level_adjustment", ""),
            "space": dt_race.get("space", ""),
            "reach": dt_race.get("reach", ""),
            "traits": dt_race.get("traits", []),
            "desc_html": dt_race.get("desc_html", ""),
            "source": dt_race.get("source", ""),
            "source_book": dt_race.get("source_book", ""),
            "source_page": dt_race.get("source_page", ""),
            "source_url": dt_race.get("source_url", ""),
            "edition": dt_race.get("edition", "3.5"),
            "source_site": "dndtools.net",
        }
        new_races.append(new_race)

    if apply:
        existing.extend(new_races)

    return {
        "matched_count": len(set(idx for idx, _, _ in matched)),
        "changes": changes,
        "unmatched_dt": unmatched_dt,
        "new_races": new_races,
    }


def main():
    args = sys.argv[1:]
    apply = "--apply" in args
    input_file = DNDTOOLS_JSON

    for i, arg in enumerate(args):
        if arg == "--input" and i + 1 < len(args):
            input_file = args[i + 1]

    print("D&D Tools Race Merger")
    print(f"Existing: {RACES_JSON}")
    print(f"Dndtools: {input_file}")
    print(f"Mode: {'APPLY' if apply else 'DRY-RUN'}")
    print()

    # Load data
    with open(RACES_JSON, "r", encoding="utf-8") as f:
        existing = json.load(f)
    print(f"Existing races: {len(existing)}")

    with open(input_file, "r", encoding="utf-8") as f:
        dndtools = json.load(f)
    print(f"Dndtools races: {len(dndtools)}")

    # Merge
    result = merge_races(existing, dndtools, apply=apply)

    print(f"\n{'='*60}")
    print("RESULTS")
    print(f"{'='*60}")
    print(f"Matched:           {result['matched_count']}")
    print(f"Changes needed:    {len(result['changes'])}")
    print(f"New races:         {len(result['new_races'])}")
    print(f"Unmatched (dndtools): {len(result['unmatched_dt'])}")

    # Show changes
    if result["changes"]:
        print(f"\nChanges (all):")
        for name, source, field_changes in result["changes"]:
            print(f"\n  {name} ({source}):")
            for field, old, new in field_changes:
                print(f"    + {field}: {new}")

    # Show new races
    if result["new_races"]:
        print(f"\nNew races ({len(result['new_races'])}):")
        for race in result["new_races"]:
            print(f"  {race['name']} ({race['source']}) - "
                  f"{race['size']}, LA {race.get('level_adjustment', '?')}")

    # Write unmatched CSV
    if result["unmatched_dt"]:
        csv_file = os.path.join(REPO_ROOT, "unmatched_races_dndtools.csv")
        with open(csv_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["name", "source", "source_book",
                            "best_candidate", "similarity"]
            )
            writer.writeheader()
            writer.writerows(result["unmatched_dt"])
        print(f"\nUnmatched dndtools races written to: {csv_file}")

    # Apply changes
    if apply:
        # Sort by name
        existing.sort(key=lambda r: r["name"].lower())

        with open(RACES_JSON, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2, ensure_ascii=False)
        print(f"\nUpdated {RACES_JSON}")
        print(f"Total races: {len(existing)}")
    else:
        print(f"\nDry-run complete. Use --apply to write changes.")


if __name__ == "__main__":
    main()
