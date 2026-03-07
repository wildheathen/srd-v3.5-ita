#!/usr/bin/env python3
"""Analyze spells.json: remove summary_it field and extract unique filter values."""

import json
import re
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
SPELLS_PATH = os.path.join(DATA_DIR, "spells.json")

with open(SPELLS_PATH, "r", encoding="utf-8") as f:
    spells = json.load(f)

print(f"Total spells: {len(spells)}")
print()

# --- Step 1: Remove summary_it field ---
count_had_summary_it = 0
for spell in spells:
    if "summary_it" in spell:
        count_had_summary_it += 1
        del spell["summary_it"]

print(f"=== STEP 1: Remove summary_it ===")
print(f"Spells that had 'summary_it' field: {count_had_summary_it}")

# Save back
with open(SPELLS_PATH, "w", encoding="utf-8") as f:
    json.dump(spells, f, ensure_ascii=False, indent=2)
    f.write("\n")

print(f"Saved updated spells.json (summary_it removed)")
print()

# --- Step 2: Extract unique values ---

# Unique sources
sources = set()
for spell in spells:
    if spell.get("source"):
        sources.add(spell["source"])

print(f"=== UNIQUE SOURCES ({len(sources)}) ===")
for s in sorted(sources):
    # Count spells per source
    count = sum(1 for sp in spells if sp.get("source") == s)
    manual = next((sp.get("manual_name", "") for sp in spells if sp.get("source") == s), "")
    print(f"  {s} ({count}) — {manual}")

print()

# Unique class/domain abbreviations from level field
class_names = set()
for spell in spells:
    level_str = spell.get("level", "")
    if not level_str:
        continue
    # Split by comma, then extract class name (everything before the last space+number)
    parts = [p.strip() for p in level_str.split(",")]
    for part in parts:
        # Match patterns like "Sor/Wiz 3", "Clr 5", "Brd 2", "Domain 1"
        match = re.match(r"^(.+?)\s+(\d+)$", part.strip())
        if match:
            class_names.add(match.group(1).strip())
        else:
            # Some might not have a level number
            class_names.add(part.strip())

print(f"=== UNIQUE CLASS/DOMAIN NAMES IN LEVEL FIELD ({len(class_names)}) ===")
for c in sorted(class_names):
    count = sum(1 for sp in spells if c in (sp.get("level") or ""))
    print(f"  {c} ({count})")

print()

# Unique schools
schools = set()
for spell in spells:
    if spell.get("school"):
        schools.add(spell["school"])

print(f"=== UNIQUE SCHOOLS ({len(schools)}) ===")
for s in sorted(schools):
    count = sum(1 for sp in spells if sp.get("school") == s)
    print(f"  {s} ({count})")

print()

# Unique subschools
subschools = set()
for spell in spells:
    val = spell.get("subschool")
    if val:
        subschools.add(val)

print(f"=== UNIQUE SUBSCHOOLS ({len(subschools)}) ===")
for s in sorted(subschools):
    count = sum(1 for sp in spells if sp.get("subschool") == s)
    print(f"  {s} ({count})")

# Count nulls
null_count = sum(1 for sp in spells if not sp.get("subschool"))
print(f"  (null/empty: {null_count})")

print()

# Unique descriptors
descriptors = set()
for spell in spells:
    val = spell.get("descriptor")
    if val:
        # Some spells have multiple descriptors like "Fire, Light"
        # Show individual ones too
        descriptors.add(val)

print(f"=== UNIQUE DESCRIPTOR VALUES ({len(descriptors)}) ===")
for d in sorted(descriptors):
    count = sum(1 for sp in spells if sp.get("descriptor") == d)
    print(f"  {d} ({count})")

# Count nulls
null_count = sum(1 for sp in spells if not sp.get("descriptor"))
print(f"  (null/empty: {null_count})")

print()

# Also extract individual descriptor tokens (split by comma)
descriptor_tokens = set()
for spell in spells:
    val = spell.get("descriptor")
    if val:
        for token in val.split(","):
            token = token.strip()
            # Also handle " or " and " and " separators
            for sub in re.split(r"\s+or\s+|\s+and\s+", token):
                descriptor_tokens.add(sub.strip())

print(f"=== UNIQUE INDIVIDUAL DESCRIPTOR TOKENS ({len(descriptor_tokens)}) ===")
for d in sorted(descriptor_tokens):
    print(f"  {d}")
