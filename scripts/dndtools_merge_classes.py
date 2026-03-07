#!/usr/bin/env python3
"""
Match & Merge — Update data/classes.json with English data from dndtools.net.

1. Match existing classes by name (case-insensitive) with dndtools data
2. Fuzzy match (>= 0.95) as fallback
3. For matched classes: add new fields, fill empty fields, preserve existing desc_html
4. For new classes: create complete entries
5. Generate unmatched.csv for manual review

Usage:
    python scripts/dndtools_merge_classes.py                           # dry-run (no changes)
    python scripts/dndtools_merge_classes.py --apply                   # apply changes to classes.json
    python scripts/dndtools_merge_classes.py --input custom.json       # custom input file
"""

import csv
import json
import os
import re
import sys
from difflib import SequenceMatcher

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLASSES_JSON = os.path.join(REPO_ROOT, "data", "classes.json")
DNDTOOLS_JSON = os.path.join(REPO_ROOT, "data", "dndtools", "classes_en_parsed.json")

# New fields to add from dndtools (these don't exist in the current schema)
NEW_FIELDS = [
    "is_prestige", "skill_points", "class_skills",
    "source_book", "source_page", "source_url",
    "edition", "source_site",
]

# Fields that can be filled if empty in existing data
FILLABLE_FIELDS = ["hit_die", "alignment"]


def normalize_name(name):
    """Normalize class name for matching."""
    n = name.lower().strip()
    n = n.replace("\u2019", "'")  # curly apostrophe
    n = n.replace("\u2018", "'")
    n = n.replace("\u201c", '"')
    n = n.replace("\u201d", '"')
    n = re.sub(r"\s+", " ", n)
    return n


def slugify(name):
    """Create a slug from a class name."""
    s = name.lower().strip()
    s = re.sub(r"['\u2019]", "", s)
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    return s


def similarity(a, b):
    """String similarity ratio."""
    return SequenceMatcher(None, a, b).ratio()


def merge_classes(existing, dndtools, apply=False):
    """Merge dndtools data into existing classes."""
    # Build index of existing classes by normalized name
    existing_by_name = {}
    for i, cls in enumerate(existing):
        norm = normalize_name(cls["name"])
        if norm not in existing_by_name:
            existing_by_name[norm] = []
        existing_by_name[norm].append(i)

    # Track results
    matched = []        # (existing_idx, dndtools_class, match_type)
    unmatched_en = []   # dndtools classes with no match in existing
    updated_fields = {} # field -> count of updates

    for dt_cls in dndtools:
        dt_name = normalize_name(dt_cls["name"])
        found = False

        # Direct match by name
        if dt_name in existing_by_name:
            for idx in existing_by_name[dt_name]:
                matched.append((idx, dt_cls, "exact"))
            found = True

        if not found:
            # Fuzzy match (>= 0.95 similarity)
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
                for idx in best_idx:
                    matched.append((idx, dt_cls, "fuzzy"))
                found = True
            else:
                unmatched_en.append({
                    "name": dt_cls["name"],
                    "source_book": dt_cls.get("source_book", ""),
                    "source": dt_cls.get("source", ""),
                    "edition": dt_cls.get("edition", ""),
                    "is_prestige": dt_cls.get("is_prestige", False),
                    "best_candidate": best_candidate,
                    "similarity": round(best_sim, 3),
                })

    # Apply updates to matched classes
    changes = []
    for ex_idx, dt_cls, match_type in matched:
        ex_cls = existing[ex_idx]
        cls_changes = []

        # 1. Add new fields from dndtools
        for field in NEW_FIELDS:
            dt_val = dt_cls.get(field)
            if dt_val is not None and dt_val != "" and dt_val != []:
                old_val = ex_cls.get(field)
                if old_val is None or old_val == "" or old_val == []:
                    display_val = str(dt_val)
                    if len(display_val) > 80:
                        display_val = display_val[:80] + "..."
                    cls_changes.append((field, str(old_val), display_val))
                    if apply:
                        ex_cls[field] = dt_val
                    updated_fields[field] = updated_fields.get(field, 0) + 1

        # 2. Fill empty structural fields
        for field in FILLABLE_FIELDS:
            ex_val = ex_cls.get(field, "")
            dt_val = dt_cls.get(field, "")
            if not ex_val and dt_val:
                cls_changes.append((field, ex_val, dt_val))
                if apply:
                    ex_cls[field] = dt_val
                updated_fields[field] = updated_fields.get(field, 0) + 1

        # 3. Do NOT overwrite existing table_html if already populated
        ex_table = ex_cls.get("table_html", "")
        dt_table = dt_cls.get("table_html", "")
        if not ex_table and dt_table:
            cls_changes.append(("table_html", "(empty)", f"({len(dt_table)} chars)"))
            if apply:
                ex_cls["table_html"] = dt_table
            updated_fields["table_html"] = updated_fields.get("table_html", 0) + 1

        # 4. Do NOT overwrite existing desc_html — save as desc_html_dndtools
        ex_desc = ex_cls.get("desc_html", "")
        dt_desc = dt_cls.get("desc_html", "")
        if dt_desc:
            if ex_desc:
                # Save dndtools version separately for manual review
                old_dndtools = ex_cls.get("desc_html_dndtools", "")
                if not old_dndtools:
                    cls_changes.append(("desc_html_dndtools", "(none)", f"({len(dt_desc)} chars)"))
                    if apply:
                        ex_cls["desc_html_dndtools"] = dt_desc
                    updated_fields["desc_html_dndtools"] = updated_fields.get("desc_html_dndtools", 0) + 1
            else:
                # No existing desc_html — use dndtools version directly
                cls_changes.append(("desc_html", "(empty)", f"({len(dt_desc)} chars)"))
                if apply:
                    ex_cls["desc_html"] = dt_desc
                updated_fields["desc_html"] = updated_fields.get("desc_html", 0) + 1

        # 5. Add alt_name for fuzzy matches
        if match_type == "fuzzy":
            dt_original_name = dt_cls.get("name", "")
            if dt_original_name and dt_original_name != ex_cls.get("name", ""):
                existing_alt = ex_cls.get("alt_name", "")
                if existing_alt != dt_original_name:
                    cls_changes.append(("alt_name", existing_alt, dt_original_name))
                    if apply:
                        ex_cls["alt_name"] = dt_original_name

        if cls_changes:
            changes.append((ex_cls["name"], ex_cls.get("source", ""), cls_changes))

    # Find existing classes not matched by any dndtools class
    matched_indices = set(idx for idx, _, _ in matched)
    unmatched_existing = []
    for i, cls in enumerate(existing):
        if i not in matched_indices:
            unmatched_existing.append({
                "name": cls["name"],
                "source": cls.get("source", ""),
            })

    # New classes to add (from unmatched dndtools classes)
    new_classes = []
    for um in unmatched_en:
        # Find the original dndtools class
        dt_cls = None
        for c in dndtools:
            if c["name"] == um["name"] and c.get("source_book", "") == um["source_book"]:
                dt_cls = c
                break
        if not dt_cls:
            continue

        new_cls = {
            "name": dt_cls["name"],
            "slug": dt_cls.get("slug", "") or slugify(dt_cls["name"]),
            "hit_die": dt_cls.get("hit_die", ""),
            "alignment": dt_cls.get("alignment", ""),
            "table_html": dt_cls.get("table_html", ""),
            "desc_html": dt_cls.get("desc_html", ""),
            "source": dt_cls.get("source", ""),
            "is_prestige": dt_cls.get("is_prestige", False),
            "skill_points": dt_cls.get("skill_points", ""),
            "class_skills": dt_cls.get("class_skills", []),
            "source_book": dt_cls.get("source_book", ""),
            "source_page": dt_cls.get("source_page", ""),
            "source_url": dt_cls.get("source_url", ""),
            "edition": dt_cls.get("edition", "3.5"),
            "source_site": "dndtools.net",
        }
        new_classes.append(new_cls)

    if apply:
        existing.extend(new_classes)

    return {
        "matched_count": len(set(idx for idx, _, _ in matched)),
        "changes": changes,
        "updated_fields": updated_fields,
        "unmatched_en": unmatched_en,
        "unmatched_existing": unmatched_existing,
        "new_classes": new_classes,
    }


def main():
    args = sys.argv[1:]
    apply = "--apply" in args
    input_file = DNDTOOLS_JSON

    for i, arg in enumerate(args):
        if arg == "--input" and i + 1 < len(args):
            input_file = args[i + 1]

    print(f"D&D Tools Class Merger")
    print(f"Existing: {CLASSES_JSON}")
    print(f"Dndtools: {input_file}")
    print(f"Mode: {'APPLY' if apply else 'DRY-RUN'}")
    print()

    # Load data
    with open(CLASSES_JSON, "r", encoding="utf-8") as f:
        existing = json.load(f)
    print(f"Existing classes: {len(existing)}")

    with open(input_file, "r", encoding="utf-8") as f:
        dndtools = json.load(f)
    print(f"Dndtools classes: {len(dndtools)}")

    # Merge
    result = merge_classes(existing, dndtools, apply=apply)

    print(f"\n{'='*60}")
    print(f"RESULTS")
    print(f"{'='*60}")
    print(f"Matched:           {result['matched_count']}")
    print(f"Changes needed:    {len(result['changes'])}")
    print(f"New classes:       {len(result['new_classes'])}")
    print(f"Unmatched (EN):    {len(result['unmatched_en'])}")
    print(f"Unmatched (exist): {len(result['unmatched_existing'])}")

    if result["updated_fields"]:
        print(f"\nFields updated:")
        for field, count in sorted(result["updated_fields"].items(), key=lambda x: -x[1]):
            print(f"  {field}: {count}")

    # Show sample changes
    if result["changes"]:
        print(f"\nSample changes (first 10):")
        for name, source, field_changes in result["changes"][:10]:
            print(f"\n  {name} ({source}):")
            for field, old, new in field_changes:
                old_display = str(old)[:40] + "..." if len(str(old)) > 40 else old
                new_display = str(new)[:40] + "..." if len(str(new)) > 40 else new
                print(f"    {field}: '{old_display}' -> '{new_display}'")

    # Show sample new classes
    if result["new_classes"]:
        print(f"\nSample new classes (first 15):")
        for cls in result["new_classes"][:15]:
            ptype = "prestige" if cls.get("is_prestige") else "base"
            print(f"  {cls['name']} ({cls['source']}) [{ptype}] - {cls.get('edition','?')}")

    # Show sample unmatched existing
    if result["unmatched_existing"]:
        print(f"\nExisting classes without dndtools match:")
        for cls in result["unmatched_existing"]:
            print(f"  {cls['name']} ({cls['source']})")

    # Write unmatched CSV for manual review
    if result["unmatched_en"]:
        csv_file = os.path.join(REPO_ROOT, "unmatched_classes_en.csv")
        with open(csv_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "name", "source_book", "source", "edition",
                "is_prestige", "best_candidate", "similarity"
            ])
            writer.writeheader()
            writer.writerows(result["unmatched_en"])
        print(f"\nUnmatched EN classes written to: {csv_file}")

    if result["unmatched_existing"]:
        csv_file = os.path.join(REPO_ROOT, "unmatched_classes_existing.csv")
        with open(csv_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["name", "source"])
            writer.writeheader()
            writer.writerows(result["unmatched_existing"])
        print(f"Unmatched existing classes written to: {csv_file}")

    # Apply changes
    if apply:
        # Sort by name
        existing.sort(key=lambda c: c["name"].lower())

        with open(CLASSES_JSON, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2, ensure_ascii=False)
        print(f"\nUpdated {CLASSES_JSON}")
        print(f"Total classes: {len(existing)}")
    else:
        print(f"\nDry-run complete. Use --apply to write changes.")


if __name__ == "__main__":
    main()
