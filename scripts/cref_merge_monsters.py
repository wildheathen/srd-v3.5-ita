#!/usr/bin/env python3
"""Parse and merge monsters from complete-reference.com into data/monsters.json.

Enriches existing monsters and adds ~1614 new ones.

Usage:
    python scripts/cref_merge_monsters.py           # dry-run
    python scripts/cref_merge_monsters.py --apply    # write changes
"""

import json
import re
import html
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'data'
SOURCE_DIR = ROOT / 'sources' / 'contrib' / 'complete-reference.com'


def normalize(name):
    s = name.lower().strip()
    s = s.replace('\u2019', "'").replace('\u2018', "'")
    s = re.sub(r'[^a-z0-9]', '', s)
    return s


def slugify(name):
    s = name.lower().strip()
    s = re.sub(r"['\u2019\u2018]", '', s)
    s = re.sub(r'[^a-z0-9]+', '-', s)
    return s.strip('-')


def flatten_nested(raw):
    result = []
    for item in raw:
        if isinstance(item, list):
            for sub in item:
                if isinstance(sub, list):
                    result.extend(sub)
                elif isinstance(sub, dict):
                    result.append(sub)
        elif isinstance(item, dict):
            result.append(item)
    return result


def clean_cr(cr_str):
    """Clean challenge rating string."""
    if not cr_str:
        return ''
    cr = cr_str.strip()
    # Remove leading zeros for whole numbers
    cr = re.sub(r'^0+(\d)', r'\1', cr)
    # Remove trailing junk
    cr = re.sub(r'\s*[-]+\s*$', '', cr)
    return cr.strip()


def clean_alignment(align):
    """Clean alignment string."""
    if not align:
        return ''
    a = align.strip()
    # Remove "Usually " prefix
    a = re.sub(r'^Usually\s+', '', a, flags=re.IGNORECASE)
    # Remove "Often " prefix
    a = re.sub(r'^Often\s+', '', a, flags=re.IGNORECASE)
    # Remove "Always " prefix
    a = re.sub(r'^Always\s+', '', a, flags=re.IGNORECASE)
    return a.strip()


def merge_monsters(apply=False):
    # Load current
    monsters_path = DATA / 'monsters.json'
    with open(monsters_path, 'r', encoding='utf-8') as f:
        current = json.load(f)

    # Load all 4 parts
    all_new = []
    for part in range(1, 5):
        fpath = SOURCE_DIR / f'monsters-part{part}.json'
        with open(fpath, 'r', encoding='utf-8') as f:
            raw = json.load(f)
        items = flatten_nested(raw)
        all_new.extend(items)
        print(f'Part {part}: {len(items)} monsters')

    print(f'Total new: {len(all_new)}')

    # Deduplicate by normalized name
    new_by_norm = {}
    for m in all_new:
        name = html.unescape(m.get('name', '').strip())
        if name:
            n = normalize(name)
            new_by_norm[n] = m

    print(f'Deduplicated: {len(new_by_norm)}')

    # Build current lookup
    current_by_norm = {}
    for m in current:
        n = normalize(m['name'])
        current_by_norm[n] = m

    print(f'Current monsters: {len(current)}')

    # Process
    enriched = 0
    new_added = []
    existing_slugs = {m['slug'] for m in current}

    for nnorm, new in new_by_norm.items():
        target = current_by_norm.get(nnorm)
        name = html.unescape(new.get('name', '').strip())

        if target:
            changed = False
            # Enrich with structured fields
            if not target.get('challenge_rating') and new.get('challenge_rating'):
                target['challenge_rating'] = clean_cr(new['challenge_rating'])
                changed = True
            if not target.get('alignment') and new.get('alignment'):
                target['alignment'] = clean_alignment(new['alignment'])
                changed = True
            if not target.get('environment') and new.get('environment'):
                target['environment'] = new['environment'].strip()
                changed = True
            if not target.get('family') and new.get('family'):
                target['family'] = new['family'].strip()
                changed = True
            # Fill desc_html if missing
            if not target.get('desc_html') and new.get('full_text'):
                target['desc_html'] = html.unescape(new['full_text'])
                changed = True
            if changed:
                enriched += 1
        else:
            # New monster
            slug = slugify(name)
            if slug in existing_slugs:
                slug = slug + '-2'
            if slug in existing_slugs:
                slug = slug[:-2] + '-3'
            existing_slugs.add(slug)

            new_entry = {
                'name': name,
                'type': (new.get('type', '') or '').strip(),
                'slug': slug,
                'desc_html': html.unescape(new.get('full_text', '')),
                'source': 'complete-reference.com',
                'challenge_rating': clean_cr(new.get('challenge_rating', '')),
                'alignment': clean_alignment(new.get('alignment', '')),
                'environment': (new.get('environment', '') or '').strip(),
                'family': (new.get('family', '') or '').strip(),
            }
            current.append(new_entry)
            new_added.append(name)

    # Sort by name
    current.sort(key=lambda m: m['name'].lower())

    print(f'\nEnriched: {enriched}')
    print(f'New monsters added: {len(new_added)}')
    print(f'Total after merge: {len(current)}')

    if new_added:
        print(f'\nNew monsters (first 20):')
        for name in sorted(new_added)[:20]:
            print(f'  {name}')
        if len(new_added) > 20:
            print(f'  ... and {len(new_added) - 20} more')

    if apply:
        with open(monsters_path, 'w', encoding='utf-8') as f:
            json.dump(current, f, ensure_ascii=False, indent=2)
        print(f'\nSaved: {monsters_path}')
    else:
        print('\nDry run -- use --apply to write changes.')


if __name__ == '__main__':
    apply = '--apply' in sys.argv
    merge_monsters(apply)
