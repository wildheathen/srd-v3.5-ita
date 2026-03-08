#!/usr/bin/env python3
"""Parse and merge classes from complete-reference.com into data/classes.json.

Enriches existing classes with reference info and adds ~196 new classes.

Usage:
    python scripts/cref_merge_classes.py           # dry-run
    python scripts/cref_merge_classes.py --apply    # write changes
"""

import json
import re
import html
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'data'
SOURCE = ROOT / 'sources' / 'contrib' / 'complete-reference.com' / 'all-classes.json'


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


def clean_full_text(full_text):
    """Extract desc_html from full_text, stripping Reference."""
    if not full_text:
        return ''
    # Remove Reference line
    text = re.sub(r'<h5>\s*Reference:.*?</h5>', '', full_text)
    text = re.sub(r'Reference:\s*[^<]*', '', text)
    # Clean up
    text = html.unescape(text)
    return text.strip()


def merge_classes(apply=False):
    # Load current
    classes_path = DATA / 'classes.json'
    with open(classes_path, 'r', encoding='utf-8') as f:
        current = json.load(f)

    # Load new
    with open(SOURCE, 'r', encoding='utf-8') as f:
        raw = json.load(f)
    new_classes = flatten_nested(raw)

    # Load book name map
    book_map_path = DATA / 'book_name_map.json'
    book_name_map = {}
    if book_map_path.exists():
        with open(book_map_path, 'r', encoding='utf-8') as f:
            book_name_map = json.load(f)

    # Deduplicate new classes by normalized name
    new_by_norm = {}
    for c in new_classes:
        name = html.unescape(c.get('name', '').strip())
        if name:
            n = normalize(name)
            new_by_norm[n] = c

    # Build current lookup
    current_by_norm = {}
    for c in current:
        n = normalize(c['name'])
        current_by_norm[n] = c

    print(f'Current classes: {len(current)}')
    print(f'New classes (deduplicated): {len(new_by_norm)}')

    # Enrich existing + collect new
    enriched = 0
    new_added = []
    existing_slugs = {c['slug'] for c in current}

    for nnorm, new in new_by_norm.items():
        target = current_by_norm.get(nnorm)
        name = html.unescape(new.get('name', '').strip())

        ref_book, ref_page = extract_reference(new.get('full_text', ''))

        if target:
            changed = False
            # Fill source_book if missing
            if not target.get('source_book') and ref_book:
                target['source_book'] = ref_book
                changed = True
            # Fill source_page if missing
            if not target.get('source_page') and ref_page:
                target['source_page'] = ref_page
                changed = True
            # Fill reference if missing
            if not target.get('reference') and ref_page:
                target['reference'] = f"p. {ref_page}"
                changed = True
            # Fill desc_html if missing
            if not target.get('desc_html') and new.get('full_text'):
                target['desc_html'] = clean_full_text(new['full_text'])
                changed = True
            # Fill hit_die if missing
            if not target.get('hit_die') and new.get('hit_die'):
                target['hit_die'] = str(new['hit_die'])
                changed = True
            # Fill alignment if missing
            if not target.get('alignment') and new.get('alignment'):
                target['alignment'] = new['alignment']
                changed = True
            if changed:
                enriched += 1
        else:
            # New class
            slug = slugify(name)
            if slug in existing_slugs:
                slug = slug + '-2'
            existing_slugs.add(slug)

            # Resolve source abbreviation
            source_abbr = ''
            if ref_book:
                source_abbr = book_name_map.get(ref_book, '')
                if not source_abbr:
                    stripped = re.sub(r'\s+v\.?3\.[05]$', '', ref_book)
                    source_abbr = book_name_map.get(stripped, '')

            new_entry = {
                'name': name,
                'slug': slug,
                'hit_die': str(new.get('hit_die', '')) if new.get('hit_die') else '',
                'alignment': new.get('alignment', ''),
                'table_html': '',
                'desc_html': clean_full_text(new.get('full_text', '')),
                'source': source_abbr,
                'is_prestige': new.get('type', '').lower() == 'prestige',
                'skill_points': '',
                'class_skills': [],
                'source_book': ref_book or '',
                'source_page': ref_page or '',
                'source_url': '',
                'edition': '3.5',
                'source_site': 'complete-reference.com',
            }
            current.append(new_entry)
            new_added.append(name)

    # Sort by name
    current.sort(key=lambda c: c['name'].lower())

    print(f'\nEnriched: {enriched}')
    print(f'New classes added: {len(new_added)}')
    print(f'Total after merge: {len(current)}')

    if new_added:
        print(f'\nNew classes (first 20):')
        for name in sorted(new_added)[:20]:
            print(f'  {name}')
        if len(new_added) > 20:
            print(f'  ... and {len(new_added) - 20} more')

    if apply:
        with open(classes_path, 'w', encoding='utf-8') as f:
            json.dump(current, f, ensure_ascii=False, indent=2)
        print(f'\nSaved: {classes_path}')
    else:
        print('\nDry run -- use --apply to write changes.')


if __name__ == '__main__':
    apply = '--apply' in sys.argv
    merge_classes(apply)
