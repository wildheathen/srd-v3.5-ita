#!/usr/bin/env python3
"""
Fix monsters.json:
1. Remove 14 garbage SRD entries (table headers/rows parsed as monsters)
2. Extract stat block fields from cref desc_html into proper top-level fields
3. Fix Anuchu CR (empty string -> 1/2 from desc)
4. Clean up desc_html for cref entries (strip stat block, keep description)
5. Normalize whitespace in extracted fields

Usage:
    python scripts/fix_monsters.py          # dry run
    python scripts/fix_monsters.py --apply  # apply changes
"""
import json
import re
import sys
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
MONSTERS_PATH = os.path.join(DATA_DIR, 'monsters.json')

# ── 14 garbage SRD entries (table rows/headers, not real monsters) ──────────
GARBAGE_SLUGS = {
    'abilities',
    'bite-damage',
    'black-dragons-by-age',
    'brass-dragons-by-age',
    'claw-damage',
    'combat',
    'damage',
    'damage-reduction',
    'dragon-breath-weapons',
    'hd',
    'hit-dice',
    'resistance-to-acid-cold-electricity',
    'resistance-to-cold-and-fire',
    'size',
}

# ── Field extraction from cref desc_html ────────────────────────────────────

FIELD_MAP = {
    'hit dice': 'hit_dice',
    'initiative': 'initiative',
    'speed': 'speed',
    'armor class': 'armor_class',
    'ac': 'armor_class',
    'base attack/grapple': 'base_attack_grapple',
    'base attack': 'base_attack_grapple',
    'attack': 'attack',
    'attacks': 'attack',
    'full attack': 'full_attack',
    'space/reach': 'space_reach',
    'face/reach': 'space_reach',
    'special attacks': 'special_attacks',
    'special qualities': 'special_qualities',
    'saves': 'saves',
    'saving throws': 'saves',
    'abilities': 'abilities',
    'skills': 'skills',
    'feats': 'feats',
    'environment': 'environment',
    'climate/terrain': 'environment',
    'organization': 'organization',
    'challenge rating': 'challenge_rating',
    'treasure': 'treasure',
    'alignment': 'alignment',
    'advancement': 'advancement',
    'level adjustment': 'level_adjustment',
}

# Fields that should NOT overwrite existing cref-level data
PRESERVE_FIELDS = {'challenge_rating', 'alignment', 'environment'}


def extract_fields_from_html(desc):
    """Extract stat block fields from cref monster desc_html."""
    fields = {}

    # Pattern: <b>Label:</b> Value  or  <strong>Label:</strong> Value
    # Handles optional colon after tag, optional colon inside tag
    pattern = r'<(?:b|strong)>\s*([^<]+?)\s*:?\s*</(?:b|strong)>\s*:?\s*([^<]+?)(?=<|$)'

    for match in re.finditer(pattern, desc, re.IGNORECASE):
        label = match.group(1).strip().rstrip(':').lower()
        value = match.group(2).strip()
        if label in FIELD_MAP and value:
            field_name = FIELD_MAP[label]
            # For attack vs full_attack: 'attack' maps to attack,
            # 'full attack' maps to full_attack - keep both
            if field_name not in fields:
                fields[field_name] = normalize_whitespace(value)

    return fields


def normalize_whitespace(text):
    """Collapse multiple spaces, strip, fix common artifacts."""
    text = re.sub(r'\s+', ' ', text).strip()
    # Fix common encoding artifacts
    text = text.replace('\u0097', '-').replace('\u0096', '-')
    text = text.replace('\u00a0', ' ')  # nbsp
    return text


def extract_description_text(desc):
    """
    Extract the prose description from desc_html, stripping the stat block rows.
    Returns cleaned HTML suitable for desc_html.

    The stat block fields (Hit Dice through Level Adjustment/Advancement) are
    extracted into separate fields. Everything AFTER the last standard stat-block
    row (Advancement / Level Adjustment) is kept as the description.
    """
    # Find the end of the last "tail" stat-block field row
    # These are the fields that typically come last in a D&D stat block
    TAIL_FIELDS = [
        'advancement', 'level adjustment', 'level adj',
        'treasure', 'alignment', 'challenge rating',
        'organization', 'environment', 'climate/terrain',
    ]

    last_tail_end = 0
    for label in TAIL_FIELDS:
        for tag in ['b', 'strong']:
            pattern = rf'<{tag}>\s*{re.escape(label)}\s*:?\s*</{tag}>'
            for m in re.finditer(pattern, desc, re.IGNORECASE):
                pos = m.end()
                tr_end = desc.find('</tr>', pos)
                if tr_end > 0:
                    end = tr_end + 5  # len('</tr>')
                else:
                    td_end = desc.find('</td>', pos)
                    end = td_end + 5 if td_end > 0 else pos
                if end > last_tail_end:
                    last_tail_end = end

    if last_tail_end == 0:
        return desc  # Can't find stat block, return as-is

    remainder = desc[last_tail_end:].strip()

    if not remainder:
        return ''

    # Strip leading container closing tags
    remainder = re.sub(
        r'^(\s*</?tr[^>]*>\s*|\s*</?td[^>]*>\s*|\s*</?table[^>]*>\s*|\s*</?div[^>]*>\s*)+',
        '', remainder, flags=re.IGNORECASE
    )
    # Strip trailing container closing tags
    remainder = re.sub(
        r'(\s*</table>\s*</td>\s*</tr>\s*</table>|\s*</div>)+\s*$',
        '', remainder, flags=re.IGNORECASE
    )

    return remainder.strip()


def clean_cr(cr_value):
    """Normalize challenge rating values."""
    if not cr_value:
        return cr_value
    cr = str(cr_value).strip()
    # Remove leading zeros
    cr = re.sub(r'^0+(\d)', r'\1', cr)
    # Common fractions
    cr = cr.replace('\u00bd', '1/2').replace('\u00bc', '1/4')
    # Normalize 'varies'/'Varies'/'None' -> 'Varies'
    if cr.lower() in ('varies', 'none'):
        return 'Varies'
    # Strip parenthetical notes and alternatives: "5 (noble 8)" -> "5"
    match = re.match(r'^(\d+(?:/\d+)?)', cr)
    if match:
        return match.group(1)
    return cr


def clean_html(html):
    """
    Strip MSWord/inline styles from desc_html that break dark themes.
    Removes style attributes, MSWord classes, and unnecessary wrapper elements.
    """
    if not html:
        return html

    # Remove all style="..." attributes
    html = re.sub(r'\s*style="[^"]*"', '', html, flags=re.IGNORECASE)
    # Remove class="MsoNormal" and similar MSWord classes
    html = re.sub(r'\s*class="[^"]*Mso[^"]*"', '', html, flags=re.IGNORECASE)
    html = re.sub(r'\s*class="Section1"', '', html, flags=re.IGNORECASE)
    # Remove empty span tags: <span>text</span> -> text
    html = re.sub(r'<span\s*>(.*?)</span>', r'\1', html, flags=re.DOTALL)
    # Remove bgcolor attributes
    html = re.sub(r'\s*bgcolor="[^"]*"', '', html, flags=re.IGNORECASE)
    # Remove valign, width, border, cellspacing, cellpadding attributes
    html = re.sub(r'\s*(?:valign|width|border|cellspacing|cellpadding|noshade|size)="[^"]*"', '', html, flags=re.IGNORECASE)
    # Clean up empty attribute lists
    html = re.sub(r'<(\w+)\s+>', r'<\1>', html)
    return html


def main():
    apply_mode = '--apply' in sys.argv

    with open(MONSTERS_PATH, 'r', encoding='utf-8') as f:
        monsters = json.load(f)

    total_before = len(monsters)
    print(f'Loaded {total_before} monsters')

    # ── Step 1: Remove garbage SRD entries ──────────────────────────────────
    garbage_found = []
    clean_monsters = []
    for m in monsters:
        if m['slug'] in GARBAGE_SLUGS:
            garbage_found.append(m['name'])
        else:
            clean_monsters.append(m)

    print(f'\nStep 1: Remove garbage SRD entries')
    print(f'  Found {len(garbage_found)}/{len(GARBAGE_SLUGS)} garbage entries')
    for name in garbage_found:
        print(f'    - {name}')

    monsters = clean_monsters

    # ── Step 2: Extract stat fields from cref desc_html ─────────────────────
    cref_enriched = 0
    fields_added = 0
    cref_count = 0

    for m in monsters:
        if m.get('source') != 'complete-reference.com':
            continue
        cref_count += 1

        desc = m.get('desc_html', '')
        if not desc:
            continue

        extracted = extract_fields_from_html(desc)
        if not extracted:
            continue

        monster_fields_added = 0
        for field_name, value in extracted.items():
            # Don't overwrite existing non-empty values for preserved fields
            if field_name in PRESERVE_FIELDS:
                existing = m.get(field_name)
                if existing and str(existing).strip():
                    continue

            # Don't overwrite existing non-empty values from SRD
            existing = m.get(field_name)
            if not existing or not str(existing).strip():
                m[field_name] = value
                monster_fields_added += 1

        if monster_fields_added > 0:
            cref_enriched += 1
            fields_added += monster_fields_added

    print(f'\nStep 2: Extract stat fields from cref desc_html')
    print(f'  cref entries: {cref_count}')
    print(f'  Enriched: {cref_enriched} monsters')
    print(f'  Fields added: {fields_added} total')

    # ── Step 3: Fix specific issues ─────────────────────────────────────────
    fixes = 0
    for m in monsters:
        # Fix Anuchu CR
        if m['slug'] == 'anuchu' and (not m.get('challenge_rating') or m['challenge_rating'] == ''):
            m['challenge_rating'] = '1/2'
            fixes += 1
            print(f'\nStep 3: Fixed Anuchu CR -> 1/2')

        # Normalize all CRs
        if m.get('challenge_rating'):
            old_cr = m['challenge_rating']
            new_cr = clean_cr(old_cr)
            if new_cr != old_cr:
                m['challenge_rating'] = new_cr
                fixes += 1

    print(f'\nStep 3: Applied {fixes} specific fixes')

    # ── Step 4: Clean up alignment values ───────────────────────────────────
    alignment_cleaned = 0
    for m in monsters:
        al = m.get('alignment', '')
        if not al:
            continue
        # Strip "Usually ", "Often ", "Always " prefix for consistency
        new_al = re.sub(r'^(Usually|Often|Always|Typically)\s+', '', al, flags=re.IGNORECASE).strip()
        # Normalize whitespace
        new_al = normalize_whitespace(new_al)
        if new_al != al:
            m['alignment'] = new_al
            alignment_cleaned += 1

    print(f'\nStep 4: Cleaned {alignment_cleaned} alignment values')

    # ── Step 5: Strip stat block from cref desc_html ───────────────────────
    desc_cleaned = 0
    desc_emptied = 0
    for m in monsters:
        if m.get('source') != 'complete-reference.com':
            continue
        desc = m.get('desc_html', '')
        if not desc:
            continue

        new_desc = extract_description_text(desc)
        if new_desc != desc:
            # Check if the cleaned desc has meaningful content
            clean_text = re.sub(r'<[^>]+>', ' ', new_desc)
            clean_text = re.sub(r'\s+', ' ', clean_text).strip()
            if len(clean_text) > 20:
                m['desc_html'] = new_desc
                desc_cleaned += 1
            else:
                # Very little text remaining - set to empty
                m['desc_html'] = ''
                desc_emptied += 1

    print(f'\nStep 5: Strip stat block from cref desc_html')
    print(f'  Cleaned: {desc_cleaned} monsters (stat block removed, desc kept)')
    print(f'  Emptied: {desc_emptied} monsters (no meaningful desc after stat block)')

    # ── Step 6: Clean inline styles from desc_html ─────────────────────────
    html_cleaned = 0
    for m in monsters:
        desc = m.get('desc_html', '')
        if not desc:
            continue
        new_desc = clean_html(desc)
        if new_desc != desc:
            m['desc_html'] = new_desc
            html_cleaned += 1

    print(f'\nStep 6: Cleaned inline styles from desc_html')
    print(f'  Cleaned: {html_cleaned} monsters')

    # ── Summary ─────────────────────────────────────────────────────────────
    total_after = len(monsters)
    print(f'\n=== Summary ===')
    print(f'  Before: {total_before} monsters')
    print(f'  After:  {total_after} monsters')
    print(f'  Removed: {total_before - total_after} garbage entries')
    print(f'  Enriched: {cref_enriched} cref monsters with stat fields')

    # Stats
    has_cr = sum(1 for m in monsters if m.get('challenge_rating'))
    has_hit_dice = sum(1 for m in monsters if m.get('hit_dice'))
    has_ac = sum(1 for m in monsters if m.get('armor_class'))
    print(f'\n  Monsters with challenge_rating: {has_cr}/{total_after}')
    print(f'  Monsters with hit_dice: {has_hit_dice}/{total_after}')
    print(f'  Monsters with armor_class: {has_ac}/{total_after}')

    if apply_mode:
        with open(MONSTERS_PATH, 'w', encoding='utf-8') as f:
            json.dump(monsters, f, ensure_ascii=False, indent=2)
        print(f'\n-> Saved to {MONSTERS_PATH}')
    else:
        print(f'\nDry run. Use --apply to save changes.')


if __name__ == '__main__':
    main()
