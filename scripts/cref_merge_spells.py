#!/usr/bin/env python3
"""Merge parsed complete-reference.com spells into data/spells.json.

Adds short_description, description, and enriches reference info.
Handles named spell variants (Bigby's, Melf's, etc.) as alt_name aliases.

Usage:
    python scripts/cref_merge_spells.py           # dry-run
    python scripts/cref_merge_spells.py --apply    # write changes
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'data'

# Named spell variants: named_version -> SRD de-named version
# These are the same spell, just with the wizard's name prefix in non-SRD books
NAMED_ALIASES = {
    "Bigby's Clenched Fist":               "Clenched Fist",
    "Bigby's Crushing Hand":               "Crushing Hand",
    "Bigby's Forceful Hand":               "Forceful Hand",
    "Bigby's Grasping Hand":               "Grasping Hand",
    "Bigby's Interposing Hand":            "Interposing Hand",
    "Drawmij's Instant Summons":           "Instant Summons",
    "Evard's Black Tentacles":             "Black Tentacles",
    "Leomund's Secret Chest":              "Secret Chest",
    "Leomund's Secure Shelter":            "Secure Shelter",
    "Leomund's Tiny Hut":                  "Tiny Hut",
    "Melf's Acid Arrow":                   "Acid Arrow",
    "Mordenkainen's Disjunction":          "Mage's Disjunction",
    "Mordenkainen's Faithful Hound":       "Mage's Faithful Hound",
    "Mordenkainen's Lucubration":          "Mage's Lucubration",
    "Mordenkainen's Magnificent Mansion":  "Mage's Magnificent Mansion",
    "Mordenkainen's Private Sanctum":      "Mage's Private Sanctum",
    "Mordenkainen's Sword":                "Mage's Sword",
    "Nystul's Magic Aura":                 "Magic Aura",
    "Otiluke's Freezing Sphere":           "Freezing Sphere",
    "Otiluke's Resilient Sphere":          "Resilient Sphere",
    "Otiluke's Telekinetic Sphere":        "Telekinetic Sphere",
    "Otto's Irresistible Dance":           "Irresistible Dance",
    "Rary's Mnemonic Enhancer":            "Mnemonic Enhancer",
    "Rary's Telepathic Bond":              "Telepathic Bond",
    "Tasha's Hideous Laughter":            "Hideous Laughter",
    "Tenser's Floating Disk":              "Floating Disk",
    "Tenser's Transformation":             "Transformation",
    "Nightstalker's Transformation":       "Nightstalker's Transformation",
    # Variant names that map to existing entries
    "Spell Resistance, Mass":              "Spell Resistance, Mass",
    "Summon Greater Elemental":            "Summon Greater Elemental",
    "Telepathy Tap":                       "Telepathy Tap",
}


def normalize(name):
    """Normalize name for matching."""
    s = name.lower().strip()
    # Normalize unicode quotes/apostrophes
    s = s.replace('\u2019', "'").replace('\u2018', "'").replace('\u201c', '"').replace('\u201d', '"')
    s = re.sub(r'[^a-z0-9]', '', s)
    return s


def slugify(name):
    s = name.lower().strip()
    s = re.sub(r"['\u2019\u2018]", '', s)
    s = re.sub(r'[^a-z0-9]+', '-', s)
    return s.strip('-')


def merge_spells(apply=False):
    # Load current spells
    spells_path = DATA / 'spells.json'
    with open(spells_path, 'r', encoding='utf-8') as f:
        current = json.load(f)

    # Load parsed cref spells
    parsed_path = DATA / 'cref' / 'spells_en_parsed.json'
    with open(parsed_path, 'r', encoding='utf-8') as f:
        parsed = json.load(f)

    # Build lookup for current spells
    current_by_norm = {}
    for spell in current:
        n = normalize(spell['name'])
        current_by_norm[n] = spell

    # Also build lookup by SRD de-named versions (for alias matching)
    alias_norm = {}
    for named, srd_name in NAMED_ALIASES.items():
        alias_norm[normalize(named)] = normalize(srd_name)

    # Stats
    enriched = 0
    alt_names_added = 0
    new_spells = []
    unmatched = []

    for p in parsed:
        pname = p['name']
        pnorm = normalize(pname)

        # Try direct match
        target = current_by_norm.get(pnorm)

        # Try alias match
        if not target and pnorm in alias_norm:
            srd_norm = alias_norm[pnorm]
            target = current_by_norm.get(srd_norm)
            if target:
                # Add alt_name
                existing_alts = target.get('alt_name', '')
                if pname not in existing_alts:
                    if existing_alts:
                        target['alt_name'] = existing_alts + ' / ' + pname
                    else:
                        target['alt_name'] = pname
                    alt_names_added += 1

        if target:
            changed = False
            # Add short_description if missing
            if not target.get('short_description') and p.get('short_description'):
                target['short_description'] = p['short_description']
                changed = True

            # Add description (plain text) if missing
            if not target.get('description') and p.get('description'):
                target['description'] = p['description']
                changed = True

            # Enrich reference if missing
            if not target.get('reference') and p.get('ref_page'):
                target['reference'] = f"p. {p['ref_page']}"
                changed = True

            if not target.get('manual_name') and p.get('ref_book'):
                target['manual_name'] = p['ref_book']
                changed = True

            # Fill source abbreviation if generic
            if target.get('source') in ('', 'SRD', 'dndtools') and p.get('source_abbr'):
                # Don't overwrite specific sources
                pass  # keep existing source

            if changed:
                enriched += 1
        else:
            unmatched.append(p)

    # Add genuinely new spells
    existing_slugs = {s['slug'] for s in current}
    for p in unmatched:
        slug = slugify(p['name'])
        # Avoid slug collisions
        if slug in existing_slugs:
            slug = slug + '-2'
        existing_slugs.add(slug)

        new_spell = {
            'name': p['name'],
            'slug': slug,
            'school': p.get('school', ''),
            'subschool': p.get('subschool') or None,
            'descriptor': None,
            'level': p.get('level', ''),
            'components': p.get('components', ''),
            'casting_time': p.get('casting_time', ''),
            'range': p.get('range', ''),
            'target_area_effect': p.get('target_area_effect', ''),
            'duration': p.get('duration', ''),
            'saving_throw': p.get('saving_throw', ''),
            'spell_resistance': p.get('spell_resistance', ''),
            'description': p.get('description', ''),
            'short_description': p.get('short_description', ''),
            'desc_html': f"<p>{p.get('description', '')}</p>" if p.get('description') else '',
            'source': p.get('source_abbr', ''),
            'manual_name': p.get('ref_book', ''),
            'reference': f"p. {p['ref_page']}" if p.get('ref_page') else '',
            'edition': '3.5',
            'source_url': '',
            'source_site': 'complete-reference.com',
        }
        current.append(new_spell)
        new_spells.append(new_spell)

    # Sort by name
    current.sort(key=lambda s: s['name'].lower())

    # Report
    print(f'\n=== Spell Merge ===')
    print(f'Current spells: {len(current) - len(new_spells)}')
    print(f'Parsed spells: {len(parsed)}')
    print(f'Enriched: {enriched}')
    print(f'Alt names added: {alt_names_added}')
    print(f'New spells added: {len(new_spells)}')
    print(f'Total after merge: {len(current)}')

    if new_spells:
        print(f'\nNew spells:')
        for s in new_spells:
            print(f'  {s["name"]} ({s["manual_name"]})')

    if unmatched and not new_spells:
        print(f'\nUnmatched (not added):')
        for u in unmatched:
            print(f'  {u["name"]}')

    if apply:
        with open(spells_path, 'w', encoding='utf-8') as f:
            json.dump(current, f, ensure_ascii=False, indent=2)
        print(f'\nSaved: {spells_path}')
    else:
        print('\nDry run -- use --apply to write changes.')


if __name__ == '__main__':
    apply = '--apply' in sys.argv
    merge_spells(apply)
