#!/usr/bin/env python3
"""Migrate sources.json to use Wizard of the Coast abbreviations as standard keys.

Also updates 'source' fields across all data/*.json files and generates
data/book_name_map.json for downstream scripts.

Usage:
    python scripts/cref_migrate_sources.py           # dry-run
    python scripts/cref_migrate_sources.py --apply    # write changes
"""

import json
import sys
import re
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'data'

# ── Manual mapping: our old key -> Wizard key ──
# Built by comparing data/sources.json with sources/contrib/dnd35_sourcebooks.json
# Only entries that CHANGE are listed; entries that stay the same are implicit.
KEY_MIGRATION = {
    # Simple renames
    'AEG':   'AE',     # Arms and Equipment Guide
    'BoED':  'BE',     # Book of Exalted Deeds
    'BoVD':  'BV',     # Book of Vile Darkness
    'CPsi':  'CP',     # Complete Psionic
    'CSc':   'Ci',     # Cityscape
    'D':     'Dra',    # Dragonmarked
    'DLCS':  'DCS',    # Dragonlance Campaign Setting
    'DoE':   'DE',     # Dragons of Eberron
    'DotU':  'DrU',    # Drow of the Underdark
    'DrM':   'DM',     # Dragon Magic
    'Drac':  'Dr',     # Draconomicon
    'DSc':   'Du',     # Dungeonscape
    'ECR':   'Rav',    # Expedition to Castle Ravenloft
    'ELH':   'EL',     # Epic Level Handbook
    'FC1':   'FCI',    # Fiendish Codex I
    'FC2':   'FCII',   # Fiendish Codex II
    'Frost': 'Fr',     # Frostburn
    'G':     'Gh',     # Ghostwalk
    'HoB':   'HB',     # Heroes of Battle
    'HoH':   'HH',     # Heroes of Horror
    'LEF':   'LE',     # Lost Empires of Faerun
    'MCMF':  'Mon',    # Monster Compendium: Monsters of Faerun
    'ME':    'MoE',    # Magic of Eberron
    'MF':    'Mag',    # Magic of Faerun
    'MWAG':  'MW',     # Masters of the Wild
    'PGE':   'PE',     # Player's Guide to Eberron
    'PGF':   'PG',     # Player's Guide to Faerun
    'PHB':   'PH',     # Player's Handbook
    'PHB2':  'PH2',    # Player's Handbook II
    'RHD':   'RH',     # Red Hand of Doom
    'RTEE':  'RT',     # Return to the Temple of Elemental Evil
    'RoD':   'RD',     # Races of Destiny
    'RoE':   'RE',     # Races of Eberron
    'RoS':   'RS',     # Races of Stone
    'RoW':   'RW',     # Races of the Wild
    'RotDr': 'RDr',    # Races of the Dragon
    'SBG':   'SB',     # Stronghold Builder's Guidebook
    'SCT':   'Sh',     # Sharn: City of Towers
    'SFAG':  'SF',     # Sword and Fist
    'SSAG':  'SaS',    # Song and Silence
    'SStL':  'SSL',    # Shadowdale: The Scouring of the Land
    'Sand':  'Sa',     # Sandstorm
    'Storm': 'Sto',    # Stormwrack
    'TBAG':  'TB',     # Tome and Blood
    'TSGS':  'ShG',    # The Shattered Gates of Slaughtergarde
    'ToM':   'TM',     # Tome of Magic
    'UE':    'Una',    # Unapproachable East
    'RF':    'Rac',    # Races of Faerun

    # Swaps (old key is reused by another entry)
    'DF':    'DrF',    # Dragons of Faerun (Wizard: DrF) — frees DF for Defenders of the Faith
    'DFAG':  'DF',     # Defenders of the Faith (Wizard: DF)
    'EE':    'ElE',    # Elder Evils (Wizard: ElE) — frees EE for Exemplars of Evil
    'ExE':   'EE',     # Exemplars of Evil (Wizard: EE)
    'SS':    'ShS',    # Shining South (Wizard: ShS) — frees SS for Savage Species
    'SavS':  'SS',     # Savage Species (Wizard: SS)

    # Duplicates to merge (second entry removed, redirect to primary)
    'CArc':  'CAr',    # Complete Arcane (duplicate of CA)
    'CA':    'CAr',    # Complete Arcane -> Wizard: CAr
    'CDiv':  'CD',     # Complete Divine (duplicate of CD) — CD already matches Wizard
    'DrC':   'DC',     # Dragon Compendium (duplicate of DC) — not in Wizard, keep DC
    'U':     'Und',    # Underdark (duplicate of Und) — Wizard: Und
}

# Entries not in Wizard list, keep as-is:
# SRD, DC, FN, PHB3.0, PsiHB, W, WL
# Also already-matching: CAd, CC, CR, CS, CSW, CV, CW, DD, DMG, DMG2, EA, ECS, EDP, EH, ELQ,
# FE, FF, FP, FRCS, LD, LM, LoM, MH, MIC, MM, MM2, MM3, MM4, MM5, MP, MoI, OA, PF, PlH,
# SK, SM, SoS, SX, ToB, UA, Und, XPH


def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f'  Saved: {path}')


def migrate_sources(apply=False):
    """Migrate sources.json keys to Wizard abbreviations."""
    sources = load_json(DATA / 'sources.json')
    wizard_books = load_json(ROOT / 'sources' / 'contrib' / 'dnd35_sourcebooks.json')
    wiz_list = wizard_books.get('sourcebooks', wizard_books) if isinstance(wizard_books, dict) else wizard_books
    if isinstance(wiz_list, dict):
        wiz_list = wiz_list.get('sourcebooks', [])

    # Build new sources dict
    new_sources = {}
    merged_keys = set()  # track duplicate merges

    for old_key, val in sources.items():
        new_key = KEY_MIGRATION.get(old_key, old_key)

        # Handle duplicates: if new_key already exists, merge (keep richer entry)
        if new_key in new_sources:
            existing = new_sources[new_key]
            # Merge: fill empty fields from the duplicate
            for field in ['name_en', 'name_it', 'abbreviation_it']:
                if not existing.get(field) and val.get(field):
                    existing[field] = val[field]
            merged_keys.add(f'{old_key} -> {new_key} (merged)')
            continue

        # Update the abbreviation field to match the new key
        new_val = dict(val)
        new_val['abbreviation'] = new_key
        new_sources[new_key] = new_val

    # Add new Wizard books not in our sources
    wiz_by_key = {b['key']: b['title'] for b in wiz_list}
    new_books = []
    for wiz_key, title in wiz_by_key.items():
        if wiz_key not in new_sources:
            new_sources[wiz_key] = {
                'name_en': title,
                'name_it': '',
                'abbreviation': wiz_key,
                'abbreviation_it': ''
            }
            new_books.append(f'{wiz_key}: {title}')

    # Report
    changes = [(old, new) for old, new in KEY_MIGRATION.items() if old != new and old in sources]
    print(f'\n=== Sources Migration ===')
    print(f'Key renames: {len([c for c in changes if c[0] not in merged_keys])}')
    print(f'Duplicates merged: {len(merged_keys)}')
    print(f'New books added: {len(new_books)}')
    print(f'Total entries: {len(sources)} -> {len(new_sources)}')

    if merged_keys:
        print(f'\nMerged duplicates:')
        for m in sorted(merged_keys):
            print(f'  {m}')

    if new_books:
        print(f'\nNew books:')
        for b in sorted(new_books):
            print(f'  {b}')

    if changes:
        print(f'\nKey changes:')
        for old, new in sorted(changes, key=lambda x: x[0]):
            name = sources[old]['name_en']
            print(f'  {old:8s} -> {new:6s} ({name})')

    # Migrate source fields in data JSON files
    # Build old->new mapping for source field values
    source_field_map = {old: new for old, new in KEY_MIGRATION.items() if old in sources}
    # Also include identity mappings to catch exact matches
    data_files = ['spells.json', 'feats.json', 'classes.json', 'monsters.json',
                  'skills.json', 'races.json', 'equipment.json']

    total_source_updates = 0
    file_updates = {}

    for fname in data_files:
        fpath = DATA / fname
        if not fpath.exists():
            continue
        data = load_json(fpath)
        count = 0
        for entry in data:
            old_source = entry.get('source', '')
            if old_source in source_field_map:
                new_source = source_field_map[old_source]
                if old_source != new_source:
                    entry['source'] = new_source
                    count += 1
        if count > 0:
            file_updates[fname] = (data, count)
            total_source_updates += count

    print(f'\nSource field updates across data files: {total_source_updates}')
    for fname, (_, count) in sorted(file_updates.items()):
        print(f'  {fname}: {count} entries updated')

    # Generate book_name_map.json
    # Maps full book names (as they appear in Reference fields) -> our new abbreviation
    book_name_map = {}
    for key, val in new_sources.items():
        name = val.get('name_en', '')
        if name:
            book_name_map[name] = key
            # Also add common variants
            # Strip " v.3.5", " v3.5", " 3.5" suffixes
            stripped = re.sub(r'\s+v\.?3\.[05]$', '', name)
            if stripped != name:
                book_name_map[stripped] = key
            # Strip subtitle after ":"
            if ':' in name:
                base = name.split(':')[0].strip()
                book_name_map[base] = key

    print(f'\nBook name map entries: {len(book_name_map)}')

    if apply:
        save_json(DATA / 'sources.json', new_sources)
        for fname, (data, _) in file_updates.items():
            save_json(DATA / fname, data)
        save_json(DATA / 'book_name_map.json', book_name_map)
        print('\nAll changes applied!')
    else:
        print('\nDry run — use --apply to write changes.')

    return new_sources, source_field_map, book_name_map


if __name__ == '__main__':
    apply = '--apply' in sys.argv
    migrate_sources(apply=apply)
