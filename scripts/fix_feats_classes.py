#!/usr/bin/env python3
"""
Fix feats.json and classes.json data quality issues.

Feats:
1. Remove fake "Feat Name" template entry (SRD artifact)
2. Strip trailing </div> and whitespace from desc_html

Classes:
1. Remove stub entries from complete-reference.com with hit_die=0 and tiny desc_html

Usage:
    python scripts/fix_feats_classes.py          # dry run
    python scripts/fix_feats_classes.py --apply  # apply changes
"""
import json
import re
import sys
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
FEATS_PATH = os.path.join(DATA_DIR, 'feats.json')
CLASSES_PATH = os.path.join(DATA_DIR, 'classes.json')

apply_mode = '--apply' in sys.argv


def fix_feats():
    with open(FEATS_PATH, 'r', encoding='utf-8') as f:
        feats = json.load(f)

    total = len(feats)
    print(f'=== Feats ({total} entries) ===')

    # 1. Remove "Feat Name" template
    removed = 0
    clean = []
    for f in feats:
        if f['name'] == 'Feat Name' and f.get('type') == 'Type of Feat':
            removed += 1
            print(f'  Removed fake entry: "{f["name"]}" (slug: {f["slug"]})')
        else:
            clean.append(f)
    feats = clean

    # 2. Strip trailing </div> and whitespace from desc_html
    div_stripped = 0
    for f in feats:
        desc = f.get('desc_html', '')
        if not desc:
            continue
        # Strip trailing whitespace, newlines, and </div> tags
        new_desc = re.sub(r'(\s*\n\s*)*\s*</div>\s*$', '', desc)
        if new_desc != desc:
            f['desc_html'] = new_desc
            div_stripped += 1

    print(f'  Removed: {removed} fake entries')
    print(f'  Stripped trailing </div>: {div_stripped} entries')
    print(f'  Final count: {len(feats)}')

    if apply_mode:
        with open(FEATS_PATH, 'w', encoding='utf-8') as f_out:
            json.dump(feats, f_out, ensure_ascii=False, indent=2)
        print(f'  -> Saved')


def fix_classes():
    with open(CLASSES_PATH, 'r', encoding='utf-8') as f:
        classes = json.load(f)

    total = len(classes)
    print(f'\n=== Classes ({total} entries) ===')

    # 1. Remove stub entries with hit_die=0 and tiny desc_html (< 300 chars)
    # These are entries where the source data was missing/broken
    removed = []
    clean = []
    for c in classes:
        hit_die = str(c.get('hit_die', '')).strip()
        desc_len = len(c.get('desc_html', '') or '')

        if hit_die in ('0', '0.') and desc_len < 300:
            removed.append(c['name'])
        else:
            clean.append(c)

    classes = clean

    print(f'  Removed {len(removed)} stub entries:')
    for name in sorted(removed):
        print(f'    - {name}')
    print(f'  Final count: {len(classes)}')

    if apply_mode:
        with open(CLASSES_PATH, 'w', encoding='utf-8') as f_out:
            json.dump(classes, f_out, ensure_ascii=False, indent=2)
        print(f'  -> Saved')


if __name__ == '__main__':
    fix_feats()
    fix_classes()
    if not apply_mode:
        print('\nDry run. Use --apply to save.')
