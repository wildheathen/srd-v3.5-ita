#!/usr/bin/env python3
"""
Normalize class abbreviations in spell level fields.

Expands abbreviated class names to full names in both:
  - data/spells.json (English)
  - data/i18n/it/spells.json (Italian overlay)

Examples:
  EN: "Sor/Wiz 3" -> "Sorcerer 3, Wizard 3"
      "Clr 2, Drd 2, Brd 1" -> "Cleric 2, Druid 2, Bard 1"
  IT: "Mag/Str 3" -> "Mago 3, Stregone 3"
      "Chr 2, Drd 2, Brd 1" -> "Chierico 2, Druido 2, Bardo 1"

Usage:
  python scripts/normalize_spell_levels.py           # apply changes
  python scripts/normalize_spell_levels.py --dry-run  # preview only
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPELLS_EN = ROOT / "data" / "spells.json"
SPELLS_IT = ROOT / "data" / "i18n" / "it" / "spells.json"

# --- Abbreviation maps ---

EN_ABBREV = {
    "Brd": "Bard",
    "Clr": "Cleric",
    "Drd": "Druid",
    "Pal": "Paladin",
    "Rgr": "Ranger",
    "Wiz": "Wizard",
    "Sor": "Sorcerer",
}

IT_ABBREV = {
    "Brd": "Bardo",
    "Chr": "Chierico",
    "Drd": "Druido",
    "Pal": "Paladino",
    "Rgr": "Ranger",
    "Ass": "Assassino",
    "Mag": "Mago",
    "Str": "Stregone",
}

# Compound abbreviations: "Sor/Wiz N" -> "Sorcerer N, Wizard N"
EN_COMPOUND = {"Sor/Wiz": ("Sorcerer", "Wizard")}
IT_COMPOUND = {
    "Mag/Str": ("Mago", "Stregone"),
    "Str/Mag": ("Stregone", "Mago"),
    "Mag/str": ("Mago", "Stregone"),
}


def normalize_level(level_str, abbrev_map, compound_map):
    """Normalize a single level string.

    Returns (normalized_string, changed: bool).
    """
    if not level_str or not level_str.strip():
        return level_str, False

    # Pre-processing: replace period-space separators with comma-space
    # e.g. "Chr 5, Legge 5. Pal 4" -> "Chr 5, Legge 5, Pal 4"
    normalized = re.sub(r'\.\s+', ', ', level_str)

    # Split by comma
    segments = [s.strip() for s in normalized.split(',')]
    result_segments = []
    changed = False

    for seg in segments:
        if not seg:
            continue

        # Check compound abbreviations first (e.g. "Sor/Wiz 3")
        expanded = False
        for compound, (full1, full2) in compound_map.items():
            # Match "Compound N" or "Compound N (extra)"
            pattern = rf'^{re.escape(compound)}\s+(\d+.*)$'
            m = re.match(pattern, seg)
            if m:
                suffix = m.group(1)
                result_segments.append(f"{full1} {suffix}")
                result_segments.append(f"{full2} {suffix}")
                changed = True
                expanded = True
                break

        if expanded:
            continue

        # Check single abbreviations (e.g. "Clr 3", "Brd 1")
        # Match: AbbrevName Number [optional suffix]
        m = re.match(r'^(\S+)\s+(\d+.*)$', seg)
        if m:
            class_name = m.group(1)
            rest = m.group(2)
            if class_name in abbrev_map:
                result_segments.append(f"{abbrev_map[class_name]} {rest}")
                changed = True
            else:
                result_segments.append(seg)
        else:
            # No number suffix (edge case), keep as-is
            result_segments.append(seg)

    result = ", ".join(result_segments)

    # Also detect if period-replacement changed anything
    if result != level_str:
        changed = True

    return result, changed


def process_file(filepath, abbrev_map, compound_map, dry_run=False):
    """Process a JSON file, normalizing all level fields.

    Returns (data, stats_dict).
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    stats = {
        'total': len(data),
        'with_level': 0,
        'changed': 0,
        'compounds_expanded': 0,
        'examples': [],
    }

    for item in data:
        level = item.get('level', '')
        if not level or not level.strip():
            continue
        stats['with_level'] += 1

        new_level, was_changed = normalize_level(level, abbrev_map, compound_map)
        if was_changed:
            stats['changed'] += 1
            # Count compound expansions
            for compound in compound_map:
                if compound in level:
                    stats['compounds_expanded'] += 1
                    break
            if len(stats['examples']) < 10:
                name = item.get('name', item.get('slug', '?'))
                stats['examples'].append((name, level, new_level))
            if not dry_run:
                item['level'] = new_level

    return data, stats


def main():
    dry_run = '--dry-run' in sys.argv

    if dry_run:
        print("=== DRY RUN MODE (no files will be modified) ===\n")

    # Process English spells
    print(f"Processing {SPELLS_EN}...")
    en_data, en_stats = process_file(SPELLS_EN, EN_ABBREV, EN_COMPOUND, dry_run)
    print(f"  Total: {en_stats['total']}")
    print(f"  With level: {en_stats['with_level']}")
    print(f"  Changed: {en_stats['changed']}")
    print(f"  Sor/Wiz expanded: {en_stats['compounds_expanded']}")
    if en_stats['examples']:
        print("  Examples:")
        for name, old, new in en_stats['examples']:
            print(f"    {name}: \"{old}\" -> \"{new}\"")
    print()

    # Process Italian overlay
    print(f"Processing {SPELLS_IT}...")
    it_data, it_stats = process_file(SPELLS_IT, IT_ABBREV, IT_COMPOUND, dry_run)
    print(f"  Total: {it_stats['total']}")
    print(f"  With level: {it_stats['with_level']}")
    print(f"  Changed: {it_stats['changed']}")
    print(f"  Mag/Str expanded: {it_stats['compounds_expanded']}")
    if it_stats['examples']:
        print("  Examples:")
        for name, old, new in it_stats['examples']:
            print(f"    {name}: \"{old}\" -> \"{new}\"")
    print()

    if not dry_run:
        # Write results
        print("Writing files...")
        with open(SPELLS_EN, 'w', encoding='utf-8') as f:
            json.dump(en_data, f, ensure_ascii=False, indent=2)
            f.write('\n')
        print(f"  Wrote {SPELLS_EN}")

        with open(SPELLS_IT, 'w', encoding='utf-8') as f:
            json.dump(it_data, f, ensure_ascii=False, indent=2)
            f.write('\n')
        print(f"  Wrote {SPELLS_IT}")
        print("\nDone!")
    else:
        print("Dry run complete. No files modified.")


if __name__ == '__main__':
    main()
