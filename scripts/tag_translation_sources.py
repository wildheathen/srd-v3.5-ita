#!/usr/bin/env python3
"""
Tag existing Italian translations with source and review status.

Adds two fields to each overlay entry that has translated content:
  - translation_source: "manual" | "auto" | "ocr" | "pdf"
  - reviewed: boolean (default false)

Does NOT overwrite existing tags.

Usage:
  python scripts/tag_translation_sources.py           # apply changes
  python scripts/tag_translation_sources.py --dry-run  # preview only
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
I18N_IT = ROOT / "data" / "i18n" / "it"


def tag_entries(data, rules, dry_run=False):
    """Tag entries based on rules.

    rules: list of (predicate_fn, source_value) tuples.
    First matching rule wins.

    Returns count of entries tagged.
    """
    tagged = 0
    for entry in data:
        # Skip if already tagged
        if 'translation_source' in entry:
            continue

        # Check if entry has any translated content worth tagging
        has_content = (
            entry.get('desc_html', '').strip() or
            entry.get('benefit', '').strip() or
            entry.get('traits', '')  # races have traits
        )
        if not has_content:
            continue

        # Find matching rule
        source = None
        for predicate, src_value in rules:
            if predicate(entry):
                source = src_value
                break

        if source:
            if not dry_run:
                entry['translation_source'] = source
                entry['reviewed'] = False
            tagged += 1

    return tagged


def process_spells(dry_run=False):
    """Tag Italian spell translations."""
    filepath = I18N_IT / "spells.json"
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    rules = [
        # 591 spells from "Manuale del Giocatore 3.5" — OCR source
        (lambda e: e.get('manual_name') == 'Manuale del Giocatore 3.5', 'ocr'),
        # 2 from "Perfetto Arcanista"
        (lambda e: e.get('manual_name') == 'Perfetto Arcanista', 'ocr'),
        # 11 with desc_html but no manual_name — likely OCR too
        (lambda e: e.get('desc_html', '').strip() and not e.get('manual_name'), 'ocr'),
    ]

    tagged = tag_entries(data, rules, dry_run)
    print(f"  Spells: {tagged} entries tagged")

    if not dry_run and tagged > 0:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write('\n')

    return tagged


def process_feats(dry_run=False):
    """Tag Italian feat translations."""
    filepath = I18N_IT / "feats.json"
    if not filepath.exists():
        print("  Feats: file not found, skipping")
        return 0

    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    rules = [
        # Feats with benefit text — from manual translation (SRD core set)
        (lambda e: e.get('benefit', '').strip(), 'manual'),
    ]

    tagged = tag_entries(data, rules, dry_run)
    print(f"  Feats: {tagged} entries tagged")

    if not dry_run and tagged > 0:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write('\n')

    return tagged


def process_monsters(dry_run=False):
    """Tag Italian monster translations."""
    filepath = I18N_IT / "monsters.json"
    if not filepath.exists():
        print("  Monsters: file not found, skipping")
        return 0

    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    rules = [
        # Monsters with desc_html — from SRD parse (parse_srd.py)
        (lambda e: e.get('desc_html', '').strip(), 'manual'),
    ]

    tagged = tag_entries(data, rules, dry_run)
    print(f"  Monsters: {tagged} entries tagged")

    if not dry_run and tagged > 0:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write('\n')

    return tagged


def process_races(dry_run=False):
    """Tag Italian race translations."""
    filepath = I18N_IT / "races.json"
    if not filepath.exists():
        print("  Races: file not found, skipping")
        return 0

    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    rules = [
        # Races with traits — from SRD translation (manual)
        (lambda e: e.get('traits', ''), 'manual'),
    ]

    tagged = tag_entries(data, rules, dry_run)
    print(f"  Races: {tagged} entries tagged")

    if not dry_run and tagged > 0:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write('\n')

    return tagged


def process_classes(dry_run=False):
    """Tag Italian class translations."""
    filepath = I18N_IT / "classes.json"
    if not filepath.exists():
        print("  Classes: file not found, skipping")
        return 0

    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    rules = [
        # Classes with desc_html — from SRD parse (manual)
        (lambda e: e.get('desc_html', '').strip(), 'manual'),
    ]

    tagged = tag_entries(data, rules, dry_run)
    print(f"  Classes: {tagged} entries tagged")

    if not dry_run and tagged > 0:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write('\n')

    return tagged


def main():
    dry_run = '--dry-run' in sys.argv

    if dry_run:
        print("=== DRY RUN MODE (no files will be modified) ===\n")

    print("Tagging Italian translations with source metadata...\n")

    total = 0
    total += process_spells(dry_run)
    total += process_feats(dry_run)
    total += process_monsters(dry_run)
    total += process_races(dry_run)
    total += process_classes(dry_run)

    print(f"\nTotal entries tagged: {total}")

    if dry_run:
        print("\nDry run complete. No files modified.")
    else:
        print("\nDone!")


if __name__ == '__main__':
    main()
