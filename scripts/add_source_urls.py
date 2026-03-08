#!/usr/bin/env python3
"""
Add source_url from dndtools parsed data to spells.json.

The dndtools merge script (dndtools_merge.py) discards source_url during merge.
This script reads the parsed dndtools data and copies source_url back into
spells.json, matching by slug.

Usage:
  python scripts/add_source_urls.py           # apply changes
  python scripts/add_source_urls.py --dry-run  # preview only
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPELLS_FILE = ROOT / "data" / "spells.json"
DNDTOOLS_PARSED = ROOT / "data" / "dndtools" / "spells_en_parsed.json"


def slugify(name):
    """Create a slug from a spell name (matches dndtools_merge.py)."""
    s = name.lower().strip()
    s = re.sub(r"['\u2019]", "", s)
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    return s


def main():
    dry_run = '--dry-run' in sys.argv

    if dry_run:
        print("=== DRY RUN MODE (no files will be modified) ===\n")

    # Load dndtools parsed data
    print(f"Loading {DNDTOOLS_PARSED}...")
    with open(DNDTOOLS_PARSED, 'r', encoding='utf-8') as f:
        dndtools = json.load(f)

    # Build slug -> source_url map from dndtools
    # Some spells may have duplicate slugs (different source books),
    # keep the first (or prefer 3.5 edition)
    url_map = {}
    for dt in dndtools:
        slug = slugify(dt['name'])
        url = dt.get('source_url', '')
        if url and slug not in url_map:
            url_map[slug] = url

    print(f"  {len(dndtools)} dndtools entries -> {len(url_map)} unique slugs with URLs")

    # Load spells.json
    print(f"Loading {SPELLS_FILE}...")
    with open(SPELLS_FILE, 'r', encoding='utf-8') as f:
        spells = json.load(f)

    # Also build a name-based map for fuzzy matching (dndtools name -> url)
    name_map = {}
    for dt in dndtools:
        url = dt.get('source_url', '')
        if url:
            name_lower = dt['name'].lower()
            if name_lower not in name_map:
                name_map[name_lower] = url

    # Match and add source_url
    added = 0
    already_had = 0
    no_match = 0
    alt_matched = 0
    examples = []
    unmatched = []

    for spell in spells:
        slug = spell.get('slug', '')
        if not slug:
            continue

        if spell.get('source_url'):
            already_had += 1
            continue

        if slug in url_map:
            if not dry_run:
                spell['source_url'] = url_map[slug]
            added += 1
            if len(examples) < 5:
                examples.append((spell['name'], url_map[slug]))
        else:
            # Try alt_name (e.g. "Acid Arrow" has alt_name "Melf's Acid Arrow")
            alt = spell.get('alt_name', '')
            alt_slug = slugify(alt) if alt else ''
            if alt_slug and alt_slug in url_map:
                if not dry_run:
                    spell['source_url'] = url_map[alt_slug]
                added += 1
                alt_matched += 1
                if len(examples) < 10:
                    examples.append((spell['name'], f"(via alt_name '{alt}') {url_map[alt_slug]}"))
            else:
                no_match += 1
                unmatched.append(spell['name'])

    print(f"\nResults:")
    print(f"  Total spells: {len(spells)}")
    print(f"  Already had source_url: {already_had}")
    print(f"  Added source_url: {added} ({alt_matched} via alt_name)")
    print(f"  No dndtools match: {no_match}")

    if examples:
        print(f"\n  Examples:")
        for name, url in examples:
            print(f"    {name} -> {url}")

    if unmatched:
        print(f"\n  Unmatched ({len(unmatched)}):")
        for name in unmatched[:15]:
            print(f"    {name}")
        if len(unmatched) > 15:
            print(f"    ... and {len(unmatched) - 15} more")

    if not dry_run:
        print(f"\nWriting {SPELLS_FILE}...")
        with open(SPELLS_FILE, 'w', encoding='utf-8') as f:
            json.dump(spells, f, ensure_ascii=False, indent=2)
            f.write('\n')
        print("Done!")
    else:
        print("\nDry run complete. No files modified.")


if __name__ == '__main__':
    main()
