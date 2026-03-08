#!/usr/bin/env python3
"""
Parse Italian spell descriptions from PDF SRD HTML files and merge into overlay.

Sources: sources/pdf-ita/10-incantesimi/incantesimi_*.html
Target:  data/i18n/it/spells.json

The PDF SRD spells use structured HTML with .spell-block divs, h3 headings,
and field/desc classes. This script extracts full spell data and merges it
into the existing overlay, adding desc_html where missing.
"""

import json
import re
import sys
from pathlib import Path
from difflib import SequenceMatcher

ROOT = Path(__file__).resolve().parent.parent
SOURCES_DIR = ROOT / "sources" / "pdf-ita" / "10-incantesimi"
DATA_DIR = ROOT / "data"
OVERLAY_PATH = DATA_DIR / "i18n" / "it" / "spells.json"
BASE_PATH = DATA_DIR / "spells.json"

# Mapping from PDF SRD Italian spell names to EN slugs
# Only needed for names that differ from the overlay
IT_NAME_TO_SLUG = {
    "ANALIZZARE DWEOMER": "analyze-dweomer",
    "ANIMALE MESSAGGERO": "animal-messenger",
    "AURA MAGICA": "magic-aura",
    "CAMUFFARE SE STESSO": "disguise-self",
    "CAPANNA": "tiny-hut",
    "DANZA IRRESISTIBILE": "irresistible-dance",
    "DISCO FLUTTUANTE": "floating-disk",
    "DISGIUNZIONE": "mages-disjunction",
    "ELUCUBRAZIONE": "mages-lucubration",
    "EVOCAZIONI ISTANTANEE": "instant-summons",
    "FRECCIA ACIDA": "acid-arrow",
    "LEGAME TELEPATICO": "telepathic-bond",
    "MANO INTERPOSTA": "interposing-hand",
    "MANO POSSENTE": "forceful-hand",
    "MANO STRINGENTE": "grasping-hand",
    "MANO STRITOLATRICE": "crushing-hand",
    "OCCULTA OGGETTO": "magic-aura",  # Nystul's Magic Aura alternate name
    "POTENZIATORE MNEMONICO": "mnemonic-enhancer",
    "PUGNO SERRATO": "clenched-fist",
    "REGGIA MERAVIGLIOSA": "mages-magnificent-mansion",
    "RIFUGIO": "mages-private-sanctum",
    "SCRIGNO SEGRETO": "secret-chest",
    "SEGUGIO": "mages-faithful-hound",
    "SERRAMENTO ARCANO": "arcane-lock",
    "SIMBOLO DI DEBOLEZZA": "symbol-of-weakness",
    "SPADA": "mages-sword",
    "SVENTURA": "bestow-curse",
    "TOMO SEGRETO": "secret-page",
    "TRASFORMAZIONE": "transformation",
    "TRUCCO DI CORDA": "rope-trick",
    "UNTO": "grease",
    "VISTA ARCANA": "arcane-sight",
    "VOLPE ASTUTA": "foxs-cunning",
}


def extract_spells_from_html(filepath):
    """Extract spell entries from a PDF SRD HTML file.

    Returns list of dicts with keys: name_it, school, fields, desc_html
    """
    with open(filepath, encoding="utf-8") as f:
        content = f.read()

    spells = []

    # Find all spell blocks
    blocks = re.findall(
        r'<div class="spell-block">(.*?)</div>',
        content,
        re.DOTALL,
    )

    for block in blocks:
        # Extract name from h3
        h3_match = re.search(r"<h3>([^<]+)</h3>", block)
        if not h3_match:
            continue
        name = h3_match.group(1).strip()

        # Extract school/subschool
        school_match = re.search(
            r'<p class="school"><i>([^<]+)</i></p>', block
        )
        school = school_match.group(1).strip() if school_match else ""

        # Extract fields
        fields = {}
        for fm in re.finditer(
            r'<p class="field"><b>([^<]+)</b>\s*(.*?)</p>',
            block,
            re.DOTALL,
        ):
            field_name = fm.group(1).strip().rstrip(":")
            field_value = fm.group(2).strip()
            fields[field_name] = field_value

        # Extract description
        desc_parts = []
        for dm in re.finditer(r'<p class="desc">(.*?)</p>', block, re.DOTALL):
            desc_parts.append(dm.group(1).strip())

        desc_html = "\n".join(f"<p>{p}</p>" for p in desc_parts) if desc_parts else ""

        # Build full desc_html including fields
        full_desc_parts = []
        if school:
            full_desc_parts.append(f"<p><i>{school}</i></p>")
        for fname, fval in fields.items():
            full_desc_parts.append(f"<p><strong>{fname}:</strong> {fval}</p>")
        if desc_parts:
            for p in desc_parts:
                full_desc_parts.append(f"<p>{p}</p>")

        full_desc_html = "\n".join(full_desc_parts)

        spells.append({
            "name_it": name,
            "school": school,
            "fields": fields,
            "desc_html": full_desc_html,
            "desc_only": "\n".join(f"<p>{p}</p>" for p in desc_parts),
        })

    return spells


def slugify(name):
    """Convert a name to a slug."""
    s = name.lower().strip()
    s = re.sub(r"[''']", "", s)
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    return s


def find_slug_for_spell(spell_name, it_to_slug, overlay_names, base_map):
    """Try to find the EN slug for an Italian spell name."""
    name_upper = spell_name.upper()

    # 1. Manual mapping
    if name_upper in IT_NAME_TO_SLUG:
        slug = IT_NAME_TO_SLUG[name_upper]
        if slug in base_map:
            return slug

    # 2. Exact match on overlay IT names
    if name_upper in it_to_slug:
        return it_to_slug[name_upper]

    # 3. Title case match
    name_title = spell_name.title()
    if name_title.upper() in it_to_slug:
        return it_to_slug[name_title.upper()]

    # 4. Fuzzy match against overlay names
    best_ratio = 0
    best_slug = None
    for key, slug in it_to_slug.items():
        ratio = SequenceMatcher(None, name_upper, key).ratio()
        if ratio > best_ratio and ratio > 0.88:
            best_ratio = ratio
            best_slug = slug

    return best_slug


def main():
    dry_run = "--dry-run" in sys.argv

    if dry_run:
        print("=== DRY RUN MODE (no files will be modified) ===\n")

    # Load base and overlay
    with open(BASE_PATH, encoding="utf-8") as f:
        base = json.load(f)
    with open(OVERLAY_PATH, encoding="utf-8") as f:
        overlay = json.load(f)

    base_map = {e["slug"]: e for e in base}
    overlay_map = {e["slug"]: e for e in overlay}

    # Build IT name → slug mapping from overlay
    it_to_slug = {}
    for entry in overlay:
        name = entry.get("name", "").strip()
        if name:
            it_to_slug[name.upper()] = entry["slug"]

    # Parse all PDF SRD spell files
    all_parsed = []
    for letter in ["A", "B", "C", "D", "E", "F", "G", "HIJK", "L", "M",
                    "NO", "PQ", "R", "S", "T", "UVWXYZ"]:
        filepath = SOURCES_DIR / f"incantesimi_{letter}.html"
        if not filepath.exists():
            continue
        spells = extract_spells_from_html(filepath)
        all_parsed.extend(spells)

    print(f"Parsed {len(all_parsed)} spells from PDF SRD IT\n")

    # Track stats
    matched = 0
    unmatched = []
    updated_desc = 0
    updated_fields = 0
    skipped_has_desc = 0

    for spell in all_parsed:
        slug = find_slug_for_spell(
            spell["name_it"], it_to_slug, it_to_slug, base_map
        )

        if not slug:
            unmatched.append(spell["name_it"])
            continue

        if slug not in base_map:
            unmatched.append(f"{spell['name_it']} (slug: {slug} not in base)")
            continue

        matched += 1

        if slug in overlay_map:
            entry = overlay_map[slug]

            # Only update desc_html if missing
            if not entry.get("desc_html", "").strip():
                if spell["desc_html"]:
                    if not dry_run:
                        entry["desc_html"] = spell["desc_html"]
                        if "translation_source" not in entry:
                            entry["translation_source"] = "pdf"
                            entry["reviewed"] = False
                    updated_desc += 1
            else:
                skipped_has_desc += 1
        else:
            # This spell exists in base but not overlay — create new entry
            new_entry = {
                "slug": slug,
                "name": spell["name_it"].title()
                if spell["name_it"].isupper()
                else spell["name_it"],
            }

            if spell.get("school"):
                new_entry["school"] = spell["school"]

            if spell["desc_html"]:
                new_entry["desc_html"] = spell["desc_html"]

            new_entry["translation_source"] = "pdf"
            new_entry["reviewed"] = False

            if not dry_run:
                overlay.append(new_entry)
                overlay_map[slug] = new_entry
            updated_fields += 1

    print(f"Summary:")
    print(f"  Parsed:              {len(all_parsed)} spells from PDF SRD IT")
    print(f"  Matched:             {matched}")
    print(f"  Added desc_html:     {updated_desc} (overlay had no desc)")
    print(f"  New overlay entries: {updated_fields}")
    print(f"  Skipped (has desc):  {skipped_has_desc}")
    print(f"  Unmatched:           {len(unmatched)}")

    if unmatched:
        print(f"\nUnmatched spells ({len(unmatched)}):")
        for u in sorted(unmatched):
            print(f"    {u}")

    if not dry_run and (updated_desc > 0 or updated_fields > 0):
        overlay.sort(key=lambda e: e.get("slug", ""))
        with open(OVERLAY_PATH, "w", encoding="utf-8") as f:
            json.dump(overlay, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"\nWritten {len(overlay)} entries to {OVERLAY_PATH}")
    elif dry_run:
        print("\nDry run complete. No files modified.")
    else:
        print("\nNo changes needed.")


if __name__ == "__main__":
    main()
