#!/usr/bin/env python3
"""
Backfill missing tables from English spell descriptions into Italian overlay.

For Italian spells that have desc_html but are missing tables present in the
English version, this script extracts the table HTML from EN and appends it
to the IT desc_html.

Tables contain mostly numerical/technical data (levels, DCs, dice) that is
understandable regardless of language.

Usage:
  python scripts/backfill_tables.py           # apply changes
  python scripts/backfill_tables.py --dry-run  # preview only
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPELLS_EN = ROOT / "data" / "spells.json"
SPELLS_IT = ROOT / "data" / "i18n" / "it" / "spells.json"


def extract_tables(html):
    """Extract all <table>...</table> blocks from HTML."""
    if not html:
        return []
    # Match <table ...>...</table> including nested content
    tables = re.findall(r'<table[^>]*>.*?</table>', html, re.DOTALL | re.IGNORECASE)
    return tables


def main():
    dry_run = '--dry-run' in sys.argv

    if dry_run:
        print("=== DRY RUN MODE (no files will be modified) ===\n")

    # Load data
    print(f"Loading {SPELLS_EN}...")
    with open(SPELLS_EN, 'r', encoding='utf-8') as f:
        en_spells = json.load(f)

    print(f"Loading {SPELLS_IT}...")
    with open(SPELLS_IT, 'r', encoding='utf-8') as f:
        it_spells = json.load(f)

    # Build EN map by slug
    en_map = {s['slug']: s for s in en_spells}

    # Find and fix missing tables
    backfilled = 0
    skipped = 0

    for it_spell in it_spells:
        slug = it_spell.get('slug', '')
        it_desc = it_spell.get('desc_html', '')

        if not it_desc:
            continue

        # Check if IT already has tables
        if '<table' in it_desc.lower():
            continue

        # Check if EN has tables
        en_spell = en_map.get(slug, {})
        en_desc = en_spell.get('desc_html', '')
        if not en_desc or '<table' not in en_desc.lower():
            continue

        # Extract tables from EN
        tables = extract_tables(en_desc)
        if not tables:
            skipped += 1
            continue

        # Append tables to IT desc_html
        name = it_spell.get('name', slug)
        print(f"  {name}: appending {len(tables)} table(s)")

        if not dry_run:
            # Add a separator and the tables
            tables_html = '\n'.join(tables)
            it_spell['desc_html'] = it_desc.rstrip() + '\n' + tables_html

        backfilled += 1

    print(f"\nResults:")
    print(f"  IT spells with desc_html: {sum(1 for s in it_spells if s.get('desc_html'))}")
    print(f"  Tables backfilled: {backfilled}")
    print(f"  Skipped (regex failed): {skipped}")

    if not dry_run and backfilled > 0:
        print(f"\nWriting {SPELLS_IT}...")
        with open(SPELLS_IT, 'w', encoding='utf-8') as f:
            json.dump(it_spells, f, ensure_ascii=False, indent=2)
            f.write('\n')
        print("Done!")
    elif dry_run:
        print("\nDry run complete. No files modified.")
    else:
        print("\nNo changes needed.")


if __name__ == '__main__':
    main()
