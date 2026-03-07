#!/usr/bin/env python3
"""
Match & Merge — Update data/feats.json with English data from dndtools.net.

1. Match existing feats by name (case-insensitive) with dndtools data
2. Fill empty fields for existing feats (prerequisites, benefit, normal, special)
3. Add dndtools metadata (source_book, source_page, source_url, edition, required_for)
4. Add new feats not already present
5. Generate data/dndtools/unmatched_feats_en.csv for manual review

Usage:
    python scripts/dndtools_merge_feats.py                    # dry-run (no changes)
    python scripts/dndtools_merge_feats.py --apply            # apply changes to feats.json
    python scripts/dndtools_merge_feats.py --input custom.json # custom input file
"""

import csv
import json
import os
import re
import sys
from difflib import SequenceMatcher

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FEATS_JSON = os.path.join(REPO_ROOT, "data", "feats.json")
DNDTOOLS_JSON = os.path.join(REPO_ROOT, "data", "dndtools", "feats_en_parsed.json")
UNMATCHED_CSV = os.path.join(REPO_ROOT, "data", "dndtools", "unmatched_feats_en.csv")

# Fields to fill from dndtools when empty in existing data.
# These are NOT overwritten if already populated.
FILLABLE_FIELDS = [
    "prerequisites", "benefit", "normal", "special", "desc_html",
]

# Fields always added/updated from dndtools (metadata enrichment)
METADATA_FIELDS = [
    "source_book", "source_page", "source_url", "edition", "source_site",
]


def normalize_name(name):
    """Normalize feat name for matching."""
    n = name.lower().strip()
    # Normalize unicode quotes/apostrophes
    n = n.replace("\u2019", "'")   # right single curly
    n = n.replace("\u2018", "'")   # left single curly
    n = n.replace("\u201c", '"')   # left double curly
    n = n.replace("\u201d", '"')   # right double curly
    n = re.sub(r"\s+", " ", n)
    return n


def slugify(name):
    """Create a slug from a feat name."""
    s = name.lower().strip()
    s = re.sub(r"['\u2019]", "", s)
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    return s


def similarity(a, b):
    """String similarity ratio."""
    return SequenceMatcher(None, a, b).ratio()


def merge_feats(existing, dndtools, apply=False):
    """Merge dndtools data into existing feats.

    Returns a result dict with stats and details.
    """
    # Build index of existing feats by normalized name
    existing_by_name = {}
    for i, feat in enumerate(existing):
        norm = normalize_name(feat["name"])
        if norm not in existing_by_name:
            existing_by_name[norm] = []
        existing_by_name[norm].append(i)

    # Track results
    matched = []        # (existing_idx, dndtools_feat, match_type)
    unmatched_en = []   # dndtools feats with no match in existing
    updated_fields = {} # field -> count of updates

    for dt_feat in dndtools:
        dt_name = normalize_name(dt_feat["name"])
        found = False

        # 1. Direct name match
        if dt_name in existing_by_name:
            for idx in existing_by_name[dt_name]:
                matched.append((idx, dt_feat, "exact"))
            found = True

        # 2. Try fuzzy match (high confidence, >= 0.95)
        if not found:
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
                    matched.append((idx, dt_feat, "fuzzy"))
                found = True
            else:
                unmatched_en.append({
                    "name": dt_feat["name"],
                    "type": dt_feat.get("type", ""),
                    "source_book": dt_feat.get("source_book", ""),
                    "edition": dt_feat.get("edition", ""),
                    "best_candidate": best_candidate,
                    "similarity": round(best_sim, 3),
                })

    # Apply updates to matched feats
    changes = []
    for ex_idx, dt_feat, match_type in matched:
        ex_feat = existing[ex_idx]
        feat_changes = []

        # 1. Add dndtools metadata fields (always update)
        for field in METADATA_FIELDS:
            dt_val = dt_feat.get(field, "")
            if dt_val:
                old_val = ex_feat.get(field, "")
                if old_val != dt_val:
                    feat_changes.append((field, old_val, dt_val))
                    if apply:
                        ex_feat[field] = dt_val

        # 2. Add required_for list (always update — additive)
        dt_required = dt_feat.get("required_for", [])
        if dt_required:
            old_required = ex_feat.get("required_for", [])
            if old_required != dt_required:
                feat_changes.append(("required_for",
                                     str(old_required) if old_required else "[]",
                                     str(dt_required)))
                if apply:
                    ex_feat["required_for"] = dt_required

        # 3. Fill empty structural fields (DO NOT overwrite if populated)
        for field in FILLABLE_FIELDS:
            ex_val = ex_feat.get(field) or ""
            dt_val = dt_feat.get(field) or ""
            # Fill only if existing is empty and dndtools has data
            if not ex_val and dt_val:
                display = dt_val[:80] + ("..." if len(dt_val) > 80 else "")
                feat_changes.append((field, ex_val, display))
                if apply:
                    ex_feat[field] = dt_val
                updated_fields[field] = updated_fields.get(field, 0) + 1

        # 4. Add alt_name for fuzzy matches (different name in dndtools)
        if match_type == "fuzzy":
            dt_original_name = dt_feat.get("name", "")
            if dt_original_name and dt_original_name != ex_feat.get("name", ""):
                existing_alt = ex_feat.get("alt_name", "")
                if existing_alt != dt_original_name:
                    feat_changes.append(("alt_name", existing_alt, dt_original_name))
                    if apply:
                        ex_feat["alt_name"] = dt_original_name

        if feat_changes:
            changes.append((ex_feat["name"], ex_feat.get("source", ""), feat_changes))

    # Find existing feats not matched by any dndtools feat
    matched_indices = set(idx for idx, _, _ in matched)
    unmatched_existing = []
    for i, feat in enumerate(existing):
        if i not in matched_indices:
            unmatched_existing.append({
                "name": feat["name"],
                "source": feat.get("source", ""),
            })

    # New feats to add (from unmatched dndtools feats)
    new_feats = []
    for um in unmatched_en:
        # Find the original dndtools feat
        dt_feat = None
        for f in dndtools:
            if f["name"] == um["name"] and f.get("source_book", "") == um["source_book"]:
                dt_feat = f
                break
        if not dt_feat:
            continue

        new_feat = {
            "name": dt_feat["name"],
            "slug": slugify(dt_feat["name"]),
            "type": dt_feat.get("type", ""),
            "prerequisites": dt_feat.get("prerequisites"),
            "benefit": dt_feat.get("benefit"),
            "normal": dt_feat.get("normal"),
            "special": dt_feat.get("special"),
            "desc_html": dt_feat.get("desc_html", ""),
            "source": "dndtools",
            "source_book": dt_feat.get("source_book", ""),
            "source_page": dt_feat.get("source_page", ""),
            "source_url": dt_feat.get("source_url", ""),
            "edition": dt_feat.get("edition", "3.5"),
            "source_site": "dndtools.net",
            "required_for": dt_feat.get("required_for", []),
        }
        new_feats.append(new_feat)

    if apply:
        existing.extend(new_feats)

    return {
        "matched_count": len(set(idx for idx, _, _ in matched)),
        "changes": changes,
        "updated_fields": updated_fields,
        "unmatched_en": unmatched_en,
        "unmatched_existing": unmatched_existing,
        "new_feats": new_feats,
    }


def main():
    args = sys.argv[1:]
    apply = "--apply" in args
    input_file = DNDTOOLS_JSON

    for i, arg in enumerate(args):
        if arg == "--input" and i + 1 < len(args):
            input_file = args[i + 1]

    print(f"D&D Tools Feat Merger")
    print(f"Existing: {FEATS_JSON}")
    print(f"Dndtools: {input_file}")
    print(f"Mode: {'APPLY' if apply else 'DRY-RUN'}")
    print()

    # Load data
    with open(FEATS_JSON, "r", encoding="utf-8") as f:
        existing = json.load(f)
    print(f"Existing feats: {len(existing)}")

    with open(input_file, "r", encoding="utf-8") as f:
        dndtools = json.load(f)
    print(f"Dndtools feats: {len(dndtools)}")

    # Merge
    result = merge_feats(existing, dndtools, apply=apply)

    print(f"\n{'='*60}")
    print(f"RESULTS")
    print(f"{'='*60}")
    print(f"Matched:           {result['matched_count']}")
    print(f"Changes needed:    {len(result['changes'])}")
    print(f"New feats:         {len(result['new_feats'])}")
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
                old_display = str(old)[:40] + "..." if len(str(old)) > 40 else old
                new_display = str(new)[:40] + "..." if len(str(new)) > 40 else new
                print(f"    {field}: '{old_display}' -> '{new_display}'")

    # Show sample new feats
    if result["new_feats"]:
        print(f"\nSample new feats (first 10):")
        for feat in result["new_feats"][:10]:
            print(f"  {feat['name']} ({feat['source_book']}) [{feat['type']}] - {feat['edition']}")

    # Write unmatched CSV
    if result["unmatched_en"]:
        os.makedirs(os.path.dirname(UNMATCHED_CSV), exist_ok=True)
        with open(UNMATCHED_CSV, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["name", "type", "source_book", "edition",
                            "best_candidate", "similarity"]
            )
            writer.writeheader()
            writer.writerows(result["unmatched_en"])
        print(f"\nUnmatched EN feats written to: {UNMATCHED_CSV}")

    if result["unmatched_existing"]:
        unmatched_exist_csv = os.path.join(
            REPO_ROOT, "data", "dndtools", "unmatched_feats_existing.csv"
        )
        with open(unmatched_exist_csv, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["name", "source"])
            writer.writeheader()
            writer.writerows(result["unmatched_existing"])
        print(f"Unmatched existing feats written to: {unmatched_exist_csv}")

    # Apply changes
    if apply:
        # Sort by name
        existing.sort(key=lambda f: f["name"].lower())

        with open(FEATS_JSON, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2, ensure_ascii=False)
        print(f"\nUpdated {FEATS_JSON}")
        print(f"Total feats: {len(existing)}")
    else:
        print(f"\nDry-run complete. Use --apply to write changes.")


if __name__ == "__main__":
    main()
