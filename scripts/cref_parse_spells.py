#!/usr/bin/env python3
"""Parse spells from complete-reference.com JSON into intermediate format.

Extracts description, short_description, and Reference (book + page) from full_text.

Usage:
    python scripts/cref_parse_spells.py
"""

import json
import re
import html
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'data'
SOURCE = ROOT / 'sources' / 'contrib' / 'complete-reference.com' / 'all-spells-big.json'


def slugify(name):
    s = name.lower().strip()
    s = re.sub(r"['\u2019\u2018]", '', s)
    s = re.sub(r'[^a-z0-9]+', '-', s)
    return s.strip('-')


def flatten_nested(raw):
    """Flatten nested array-of-arrays structure."""
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
    """Extract Reference: Book Name [page] from end of full_text."""
    if not full_text:
        return None, None
    m = re.search(r'Reference:\s*(.+?)(?:</|$)', full_text)
    if not m:
        return None, None
    ref_text = m.group(1).strip()
    # Split book name and page number
    parts = re.match(r'^(.+?)\s+(\d+)\s*$', ref_text)
    if parts:
        return parts.group(1).strip(), parts.group(2)
    return ref_text, None


def clean_description(text):
    """Clean description text: unescape HTML entities, normalize whitespace."""
    if not text:
        return ''
    text = html.unescape(text)
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    # Normalize multiple newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def parse_spells():
    print(f'Loading: {SOURCE}')
    with open(SOURCE, 'r', encoding='utf-8') as f:
        raw = json.load(f)

    spells = flatten_nested(raw)
    print(f'Flattened: {len(spells)} spells')

    # Load book name map for reference resolution
    book_map_path = DATA / 'book_name_map.json'
    book_name_map = {}
    if book_map_path.exists():
        with open(book_map_path, 'r', encoding='utf-8') as f:
            book_name_map = json.load(f)

    parsed = []
    ref_books_found = set()

    for spell in spells:
        name = html.unescape(spell.get('name', '').strip())
        if not name:
            continue

        # Extract reference from full_text
        ref_book, ref_page = extract_reference(spell.get('full_text', ''))
        if ref_book:
            ref_books_found.add(ref_book)

        # Map book name to abbreviation
        source_abbr = ''
        if ref_book:
            source_abbr = book_name_map.get(ref_book, '')
            if not source_abbr:
                # Try stripping " v.3.5" etc
                stripped = re.sub(r'\s+v\.?3\.[05]$', '', ref_book)
                source_abbr = book_name_map.get(stripped, '')
            if not source_abbr:
                # Try normalizing unicode/encoding issues (Faerûn variants)
                normalized = ref_book.replace('\ufffd', 'u').replace('\u00fb', 'u').replace('\u00e9', 'e')
                for map_key, map_val in book_name_map.items():
                    norm_key = map_key.replace('\ufffd', 'u').replace('\u00fb', 'u').replace('\u00e9', 'e')
                    if normalized == norm_key:
                        source_abbr = map_val
                        break

        entry = {
            'name': name,
            'slug': slugify(name),
            'school': spell.get('school', ''),
            'subschool': spell.get('subschool', '') or None,
            'level': spell.get('level', ''),
            'components': spell.get('components', ''),
            'casting_time': spell.get('casting_time', ''),
            'range': spell.get('range', ''),
            'duration': spell.get('duration', ''),
            'saving_throw': spell.get('saving_throw', ''),
            'spell_resistance': spell.get('spell_resistance', ''),
            'description': clean_description(spell.get('description', '')),
            'short_description': spell.get('short_description', '').strip(),
            'ref_book': ref_book or '',
            'ref_page': ref_page or '',
            'source_abbr': source_abbr,
            # Combine target/effect/area
            'target_area_effect': ' / '.join(filter(None, [
                spell.get('target', ''),
                spell.get('effect', ''),
                spell.get('area', '')
            ])) or '',
        }
        parsed.append(entry)

    # Report unresolved book names
    unresolved = [b for b in ref_books_found if not book_name_map.get(b, '') and not book_name_map.get(re.sub(r'\s+v\.?3\.[05]$', '', b), '')]
    if unresolved:
        print(f'\nUnresolved book names ({len(unresolved)}):')
        for b in sorted(unresolved):
            print(f'  "{b}"')

    # Save
    output = DATA / 'cref' / 'spells_en_parsed.json'
    with open(output, 'w', encoding='utf-8') as f:
        json.dump(parsed, f, ensure_ascii=False, indent=2)
    print(f'\nSaved: {output} ({len(parsed)} spells)')

    # Stats
    has_desc = sum(1 for s in parsed if s['description'])
    has_short = sum(1 for s in parsed if s['short_description'])
    has_ref = sum(1 for s in parsed if s['ref_book'])
    has_abbr = sum(1 for s in parsed if s['source_abbr'])
    print(f'With description: {has_desc}')
    print(f'With short_description: {has_short}')
    print(f'With reference: {has_ref}')
    print(f'With resolved abbreviation: {has_abbr}')


if __name__ == '__main__':
    parse_spells()
