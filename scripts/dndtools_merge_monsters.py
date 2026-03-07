#!/usr/bin/env python3
"""
Match & Merge -- Update data/monsters.json with English data from dndtools.net.

1. Match existing monsters by name (case-insensitive)
2. For matched monsters: add source_book, source_page, source_url, edition,
   source_site. Don't overwrite existing fields.
3. For new (unmatched dndtools) monsters: create complete entry
4. Generate unmatched CSV for manual review

Usage:
    python scripts/dndtools_merge_monsters.py                  # dry-run
    python scripts/dndtools_merge_monsters.py --apply           # apply changes
    python scripts/dndtools_merge_monsters.py --input custom.json
"""

import csv
import json
import os
import re
import sys
from difflib import SequenceMatcher

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MONSTERS_JSON = os.path.join(REPO_ROOT, "data", "monsters.json")
DNDTOOLS_JSON = os.path.join(REPO_ROOT, "data", "dndtools", "monsters_en_parsed.json")

# Fields to add from dndtools to existing entries (metadata only, don't overwrite data)
METADATA_FIELDS = [
    "source_book", "source_page", "source_url", "edition", "source_site",
]

# All stat block fields for creating new entries
STAT_FIELDS = [
    "type", "hit_dice", "initiative", "speed", "armor_class",
    "base_attack_grapple", "attack", "full_attack", "space_reach",
    "special_attacks", "special_qualities", "saves", "abilities",
    "skills", "feats", "environment", "organization", "challenge_rating",
    "treasure", "alignment", "advancement", "level_adjustment",
    "desc_html",
]


def normalize_name(name):
    """Normalize monster name for matching."""
    n = name.lower().strip()
    n = n.replace("\u2019", "'")
    n = n.replace("\u2018", "'")
    n = n.replace("\u2013", "-")  # en dash
    n = n.replace("\u2014", "-")  # em dash
    n = re.sub(r"\s+", " ", n)
    return n


def name_variants(name_norm):
    """Generate name variants for matching."""
    variants = [name_norm]

    # Common variant: "Planetouched, Aasimar" <-> "Aasimar"
    if "," in name_norm:
        # Try the part after the comma
        parts = name_norm.split(",")
        variants.append(parts[-1].strip())
        variants.append(parts[0].strip())

    # "Chain Devil (Kyton)" <-> "Chain Devil" or "Kyton"
    paren_match = re.match(r"^(.*?)\s*\(([^)]+)\)\s*$", name_norm)
    if paren_match:
        variants.append(paren_match.group(1).strip())
        variants.append(paren_match.group(2).strip())

    # Plural/singular
    if name_norm.endswith("s") and not name_norm.endswith("ss"):
        variants.append(name_norm[:-1])
    variants.append(name_norm + "s")

    return list(set(variants))


def slugify(name):
    """Create a slug from a monster name."""
    s = name.lower().strip()
    s = re.sub(r"['\u2019]", "", s)
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    return s


def similarity(a, b):
    """String similarity ratio."""
    return SequenceMatcher(None, a, b).ratio()


def merge_monsters(existing, dndtools, apply=False):
    """Merge dndtools data into existing monsters."""
    # Build index of existing monsters by normalized name and variants
    existing_by_name = {}
    for i, monster in enumerate(existing):
        norm = normalize_name(monster["name"])
        for variant in name_variants(norm):
            if variant not in existing_by_name:
                existing_by_name[variant] = []
            existing_by_name[variant].append(i)

    # Track results
    matched = []       # (existing_idx, dndtools_monster, match_type)
    unmatched_dt = []  # dndtools monsters with no match

    for dt_monster in dndtools:
        dt_name = normalize_name(dt_monster["name"])
        found = False

        # Try direct match and variants
        for variant in name_variants(dt_name):
            if variant in existing_by_name:
                for idx in existing_by_name[variant]:
                    matched.append((idx, dt_monster, "name"))
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
                    matched.append((idx, dt_monster, "fuzzy"))
                found = True
            else:
                unmatched_dt.append({
                    "name": dt_monster["name"],
                    "source": dt_monster.get("source", ""),
                    "source_book": dt_monster.get("source_book", ""),
                    "challenge_rating": dt_monster.get("challenge_rating", ""),
                    "best_candidate": best_candidate,
                    "similarity": round(best_sim, 3),
                })

    # Apply updates to matched monsters
    changes = []
    for ex_idx, dt_monster, match_type in matched:
        ex_monster = existing[ex_idx]
        monster_changes = []

        # Add metadata fields only (don't overwrite existing stat data)
        for field in METADATA_FIELDS:
            dt_val = dt_monster.get(field, "")
            ex_val = ex_monster.get(field, "")
            if dt_val and not ex_val:
                display_val = str(dt_val)[:60]
                monster_changes.append((field, "", display_val))
                if apply:
                    ex_monster[field] = dt_val

        if monster_changes:
            changes.append((
                ex_monster["name"],
                ex_monster.get("source", ""),
                monster_changes,
            ))

    # New monsters to add (from unmatched dndtools monsters)
    new_monsters = []
    for um in unmatched_dt:
        dt_monster = None
        for m in dndtools:
            if (m["name"] == um["name"]
                    and m.get("source", "") == um["source"]):
                dt_monster = m
                break
        if not dt_monster:
            continue

        new_monster = {
            "name": dt_monster["name"],
            "slug": slugify(dt_monster["name"]),
        }

        # Copy all stat fields
        for field in STAT_FIELDS:
            new_monster[field] = dt_monster.get(field, "")

        # Copy metadata
        for field in METADATA_FIELDS:
            new_monster[field] = dt_monster.get(field, "")

        new_monster["source"] = dt_monster.get("source", "")
        new_monsters.append(new_monster)

    if apply:
        existing.extend(new_monsters)

    return {
        "matched_count": len(set(idx for idx, _, _ in matched)),
        "changes": changes,
        "unmatched_dt": unmatched_dt,
        "new_monsters": new_monsters,
    }


def main():
    args = sys.argv[1:]
    apply = "--apply" in args
    input_file = DNDTOOLS_JSON

    for i, arg in enumerate(args):
        if arg == "--input" and i + 1 < len(args):
            input_file = args[i + 1]

    print("D&D Tools Monster Merger")
    print(f"Existing: {MONSTERS_JSON}")
    print(f"Dndtools: {input_file}")
    print(f"Mode: {'APPLY' if apply else 'DRY-RUN'}")
    print()

    # Load data
    with open(MONSTERS_JSON, "r", encoding="utf-8") as f:
        existing = json.load(f)
    print(f"Existing monsters: {len(existing)}")

    with open(input_file, "r", encoding="utf-8") as f:
        dndtools = json.load(f)
    print(f"Dndtools monsters: {len(dndtools)}")

    # Merge
    result = merge_monsters(existing, dndtools, apply=apply)

    print(f"\n{'='*60}")
    print("RESULTS")
    print(f"{'='*60}")
    print(f"Matched:              {result['matched_count']}")
    print(f"Changes needed:       {len(result['changes'])}")
    print(f"New monsters:         {len(result['new_monsters'])}")
    print(f"Unmatched (dndtools): {len(result['unmatched_dt'])}")

    # Show changes
    if result["changes"]:
        print(f"\nChanges (first 15):")
        for name, source, field_changes in result["changes"][:15]:
            print(f"\n  {name} ({source}):")
            for field, old, new in field_changes:
                print(f"    + {field}: {new}")

    # Show new monsters
    if result["new_monsters"]:
        print(f"\nNew monsters ({len(result['new_monsters'])}):")
        for monster in result["new_monsters"]:
            cr = monster.get("challenge_rating", "?")
            mtype = monster.get("type", "?")[:40]
            print(f"  {monster['name']} (CR {cr}) - {mtype}")

    # Show unmatched
    if result["unmatched_dt"]:
        print(f"\nUnmatched dndtools monsters:")
        for um in result["unmatched_dt"]:
            print(f"  {um['name']} ({um['source']}) - "
                  f"best: '{um['best_candidate']}' "
                  f"({um['similarity']})")

    # Write unmatched CSV
    if result["unmatched_dt"]:
        csv_file = os.path.join(REPO_ROOT, "unmatched_monsters_dndtools.csv")
        with open(csv_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["name", "source", "source_book",
                            "challenge_rating", "best_candidate", "similarity"]
            )
            writer.writeheader()
            writer.writerows(result["unmatched_dt"])
        print(f"\nUnmatched dndtools monsters written to: {csv_file}")

    # Apply changes
    if apply:
        # Sort by name
        existing.sort(key=lambda m: m["name"].lower())

        with open(MONSTERS_JSON, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2, ensure_ascii=False)
        print(f"\nUpdated {MONSTERS_JSON}")
        print(f"Total monsters: {len(existing)}")
    else:
        print(f"\nDry-run complete. Use --apply to write changes.")


if __name__ == "__main__":
    main()
