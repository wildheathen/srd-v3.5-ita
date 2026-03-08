#!/usr/bin/env python3
"""Enrich existing feats with reference info from complete-reference.com.

Only enriches existing feats (no new additions). Extracts Reference (book + page)
from full_text and fills missing source_page.

Usage:
    python scripts/cref_merge_feats.py           # dry-run
    python scripts/cref_merge_feats.py --apply    # write changes
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


def extract_reference(full_text):
    if not full_text:
        return None, None
    m = re.search(r'Reference:\s*(.+?)(?:</|$)', full_text)
    if not m:
        return None, None
    ref_text = m.group(1).strip()
    parts = re.match(r'^(.+?)\s+(\d+)\s*$', ref_text)
    if parts:
        return parts.group(1).strip(), parts.group(2)
    return ref_text, None


def merge_feats(apply=False):
    # Load current feats
    feats_path = DATA / 'feats.json'
    with open(feats_path, 'r', encoding='utf-8') as f:
        feats = json.load(f)

    # Load book name map
    book_map_path = DATA / 'book_name_map.json'
    book_name_map = {}
    if book_map_path.exists():
        with open(book_map_path, 'r', encoding='utf-8') as f:
            book_name_map = json.load(f)

    # Load both feat sources and merge (featsGashren has prerequisites)
    new_feats = {}
    for fname in ['CleanedFeats.json', 'featsGashren.json']:
        fpath = SOURCE_DIR / fname
        with open(fpath, 'r', encoding='utf-8') as f:
            raw = json.load(f)
        items = flatten_nested(raw)
        for item in items:
            name = html.unescape(item.get('name', '').strip())
            if name:
                n = normalize(name)
                # featsGashren overwrites CleanedFeats (richer data)
                new_feats[n] = item

    print(f'Current feats: {len(feats)}')
    print(f'New feat entries (deduplicated): {len(new_feats)}')

    # Build current lookup
    current_by_norm = {}
    for feat in feats:
        n = normalize(feat['name'])
        current_by_norm[n] = feat

    # Enrich
    enriched = 0
    ref_added = 0
    page_added = 0

    for feat in feats:
        fnorm = normalize(feat['name'])
        new = new_feats.get(fnorm)
        if not new:
            continue

        changed = False

        # Extract reference from full_text
        ref_book, ref_page = extract_reference(new.get('full_text', ''))

        # Fill source_page if missing
        if not feat.get('source_page') and ref_page:
            feat['source_page'] = ref_page
            page_added += 1
            changed = True

        # Fill reference if missing
        if not feat.get('reference') and ref_page:
            feat['reference'] = f"p. {ref_page}"
            ref_added += 1
            changed = True

        # Fill source_book if missing
        if not feat.get('source_book') and ref_book:
            feat['source_book'] = ref_book
            changed = True

        if changed:
            enriched += 1

    print(f'\nEnriched feats: {enriched}')
    print(f'References added: {ref_added}')
    print(f'Source pages added: {page_added}')

    if apply:
        with open(feats_path, 'w', encoding='utf-8') as f:
            json.dump(feats, f, ensure_ascii=False, indent=2)
        print(f'\nSaved: {feats_path}')
    else:
        print('\nDry run -- use --apply to write changes.')


if __name__ == '__main__':
    apply = '--apply' in sys.argv
    merge_feats(apply)
