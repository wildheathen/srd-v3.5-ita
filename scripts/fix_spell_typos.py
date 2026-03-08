#!/usr/bin/env python3
"""Fix known typos in spell names and slugs.

Updates both data/spells.json and data/i18n/it/spells.json (overlay slugs).

Usage:
    python scripts/fix_spell_typos.py           # dry-run
    python scripts/fix_spell_typos.py --apply    # write changes
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'data'

# Typo corrections: (wrong_name, correct_name)
TYPOS = [
    ("Brillant Aura",                    "Brilliant Aura"),
    ("Curse of Licanthropy",             "Curse of Lycanthropy"),
    ("Energy Votex",                     "Energy Vortex"),
    ("Hero\u2019s Blad",                 "Hero's Blade"),      # curly apostrophe + missing 'e'
    ("Hero?s Blad",                      "Hero's Blade"),      # corrupted apostrophe
    ("Nightstalker\u2019s Trasformation","Nightstalker's Transformation"),
    ("Nightstalker's Trasformation",     "Nightstalker's Transformation"),
    ("Spell Resistence, Mass",           "Spell Resistance, Mass"),
    ("Summon Greather Elemental",        "Summon Greater Elemental"),
    ("Insigna of Blessing",             "Insignia of Blessing"),
    ("Telepathy Trap",                   "Telepathy Tap"),
    # Also fix corrupted Mage entries
    ("Mage\u2019s Disjunction",          "Mage's Disjunction"),
    ("Mage\u2019s Faithful Hound",       "Mage's Faithful Hound"),
    ("Mage\u2019s Lucubration",          "Mage's Lucubration"),
    ("Mage\u2019s Magnificent Mansion",  "Mage's Magnificent Mansion"),
    ("Mage\u2019s Private Sanctum",      "Mage's Private Sanctum"),
    ("Mage\u2019s Sword",               "Mage's Sword"),
]


def slugify(name):
    """Generate slug from name (matches project convention)."""
    s = name.lower().strip()
    s = re.sub(r"['\u2019\u2018]", '', s)  # remove apostrophes
    s = re.sub(r'[^a-z0-9]+', '-', s)
    s = s.strip('-')
    return s


def fix_typos(apply=False):
    # Load spells
    spells_path = DATA / 'spells.json'
    with open(spells_path, 'r', encoding='utf-8') as f:
        spells = json.load(f)

    # Load i18n overlay
    overlay_path = DATA / 'i18n' / 'it' / 'spells.json'
    with open(overlay_path, 'r', encoding='utf-8') as f:
        overlay = json.load(f)

    # Build typo map
    typo_map = {}
    for wrong, correct in TYPOS:
        typo_map[wrong] = correct

    # Fix spells
    spell_fixes = 0
    overlay_fixes = 0
    slug_changes = []

    for spell in spells:
        name = spell.get('name', '')
        if name in typo_map:
            old_slug = spell['slug']
            new_name = typo_map[name]
            new_slug = slugify(new_name)

            print(f'  Spell: "{name}" -> "{new_name}"')
            print(f'    Slug: "{old_slug}" -> "{new_slug}"')

            spell['name'] = new_name
            spell['slug'] = new_slug
            spell_fixes += 1
            slug_changes.append((old_slug, new_slug))

            # Fix overlay
            for entry in overlay:
                if entry.get('slug') == old_slug:
                    print(f'    Overlay slug updated: "{old_slug}" -> "{new_slug}"')
                    entry['slug'] = new_slug
                    overlay_fixes += 1

    print(f'\nSpells fixed: {spell_fixes}')
    print(f'Overlay slugs fixed: {overlay_fixes}')

    if apply:
        with open(spells_path, 'w', encoding='utf-8') as f:
            json.dump(spells, f, ensure_ascii=False, indent=2)
        print(f'Saved: {spells_path}')

        with open(overlay_path, 'w', encoding='utf-8') as f:
            json.dump(overlay, f, ensure_ascii=False, indent=2)
        print(f'Saved: {overlay_path}')
    else:
        print('\nDry run -- use --apply to write changes.')


if __name__ == '__main__':
    apply = '--apply' in sys.argv
    fix_typos(apply)
