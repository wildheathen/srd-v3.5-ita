#!/usr/bin/env python3
"""
Parse Italian feat descriptions from PDF SRD HTML files and merge into overlay.

Sources: sources/pdf-ita/05-talenti/*.html
Target:  data/i18n/it/feats.json

The PDF SRD uses the official Italian manual names (MdG) which may differ from
the overlay names (from dndtools/5clone). We match by building a mapping from
IT name → EN slug using the existing overlay and base data.
"""

import json
import re
import sys
from pathlib import Path
from difflib import SequenceMatcher

ROOT = Path(__file__).resolve().parent.parent
SOURCES_DIR = ROOT / "sources" / "pdf-ita" / "05-talenti"
DATA_DIR = ROOT / "data"
OVERLAY_PATH = DATA_DIR / "i18n" / "it" / "feats.json"
BASE_PATH = DATA_DIR / "feats.json"

# Mapping from official Italian feat names (MdG) to EN slug
# Built from known divergences between MdG and dndtools translations
IT_NAME_TO_SLUG = {
    "ABILITÀ FOCALIZZATA": "skill-focus",
    "ARMA FOCALIZZATA": "weapon-focus",
    "ARMA FOCALIZZATA SUPERIORE": "greater-weapon-focus",
    "AUMENTARE EVOCAZIONE": "augment-summoning",
    "INCALZARE": "cleave",
    "GRANDE INCALZARE": "great-cleave",
    "INCANTESIMI INARRESTABILI": "spell-penetration",
    "INCANTESIMI INARRESTABILI SUPERIORE": "greater-spell-penetration",
    "INCANTESIMI INGRANDITI": "enlarge-spell",
    "INDAGATORE": "investigator",
    "MANOLESTA": "deft-hands",
    "PADRONANZA DEGLI INCANTESIMI": "spell-mastery",
    "SEGUIRE TRACCE URBANE": "urban-tracking",
    "TEMPRA POSSENTE": "great-fortitude",
    "VOCAZIONE MAGICA": "spell-focus",
    "VOCAZIONE MAGICA SUPERIORE": "greater-spell-focus",
    "CREARE COSTRUTTO": "craft-construct",
    "ARMA SPECIALIZZATA": "weapon-specialization",
    "ARMA SPECIALIZZATA SUPERIORE": "greater-weapon-specialization",
    "INCALZARE POTENZIATO": "great-cleave",
    "NOME DEL TALENTO": None,  # Template entry, skip
}


def slugify(name):
    """Convert a name to a slug."""
    s = name.lower().strip()
    s = re.sub(r"[''']", "", s)
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    return s


def normalize_name(name):
    """Normalize an Italian feat name for matching."""
    # Remove extra whitespace
    name = " ".join(name.split())
    # Title case for comparison
    return name.strip()


def extract_feats_from_html(filepath):
    """Extract feat entries from an HTML file.

    Returns list of dicts with keys: name_it, type_it, prerequisites, benefit, normal, special, preamble
    """
    with open(filepath, encoding="utf-8") as f:
        content = f.read()

    # Remove HTML boilerplate (everything before first <h2> in body)
    body_match = re.search(r"<body>(.*)</body>", content, re.DOTALL)
    if not body_match:
        return []
    body = body_match.group(1)

    # Split by h2/h3 headings
    # Pattern: <h2>NAME [TYPE]</h2> or <h3>NAME [TYPE]</h3>
    parts = re.split(r"<(h[23])>([^<]+)</\1>", body)

    feats = []
    i = 0
    while i < len(parts):
        if i + 2 < len(parts) and parts[i + 1] in ("h2", "h3"):
            heading_tag = parts[i + 1]
            heading_text = parts[i + 2].strip()
            # Get content after heading (until next heading or end)
            content_after = parts[i + 3] if i + 3 < len(parts) else ""

            # Check if this is a feat heading (has [TYPE])
            m = re.match(r"(.+?)\s*\[([^\]]+)\]", heading_text)
            if m:
                feat_name = m.group(1).strip()
                feat_type = m.group(2).strip()

                # Parse the content for fields
                feat = parse_feat_content(feat_name, feat_type, content_after)
                if feat:
                    feats.append(feat)

            i += 3
        else:
            i += 1

    return feats


def parse_feat_content(name, feat_type, html_content):
    """Parse the HTML content of a feat entry into structured fields."""
    # Skip template entries
    if name.upper() == "NOME DEL TALENTO":
        return None

    # Clean the HTML content
    content = html_content.strip()

    # Remove surrounding <p>...</p> tags but keep inner HTML
    content = re.sub(r"^\s*<p>\s*", "", content)
    content = re.sub(r"\s*</p>\s*$", "", content)

    # Extract fields using bold markers
    fields = {}

    # Patterns for field extraction
    field_patterns = [
        (r"<b>Prerequisit[io]:</b>\s*", "prerequisites"),
        (r"<b>Prerequisiti:</b>\s*", "prerequisites"),
        (r"<b>Beneficio:</b>\s*", "benefit"),
        (r"<b>Normale:</b>\s*", "normal"),
        (r"<b>Speciale:</b>\s*", "special"),
    ]

    # Find all field positions
    field_positions = []
    for pattern, field_name in field_patterns:
        for m in re.finditer(pattern, content, re.IGNORECASE):
            field_positions.append((m.start(), m.end(), field_name))

    # Sort by position
    field_positions.sort(key=lambda x: x[0])

    # Extract preamble (text before first field)
    preamble = ""
    if field_positions:
        preamble = content[:field_positions[0][0]].strip()
    else:
        preamble = content.strip()

    # Extract each field's content
    for idx, (start, end, field_name) in enumerate(field_positions):
        if idx + 1 < len(field_positions):
            next_start = field_positions[idx + 1][0]
            value = content[end:next_start].strip()
        else:
            value = content[end:].strip()

        # Clean trailing <br> tags
        value = re.sub(r"\s*<br\s*/?>[\s]*$", "", value)
        value = value.strip()

        if field_name not in fields or not fields[field_name]:
            fields[field_name] = value

    # Clean up preamble
    preamble = re.sub(r"\s*<br\s*/?>[\s]*$", "", preamble)
    preamble = preamble.strip()

    # Build the result
    result = {
        "name_it": normalize_name(name),
        "type_it": feat_type,
    }

    if preamble:
        result["preamble"] = preamble
    if fields.get("prerequisites"):
        result["prerequisites"] = fields["prerequisites"]
    if fields.get("benefit"):
        result["benefit"] = fields["benefit"]
    if fields.get("normal"):
        result["normal"] = fields["normal"]
    if fields.get("special"):
        result["special"] = fields["special"]

    return result


def build_it_to_slug_map(base, overlay):
    """Build a mapping from Italian feat name (uppercase) → EN slug.

    Uses both the existing overlay names and manual mappings.
    """
    mapping = {}

    # From overlay: IT name → slug
    for entry in overlay:
        name = entry.get("name", "").strip()
        if name:
            mapping[name.upper()] = entry["slug"]

    # From manual mapping
    for it_name, slug in IT_NAME_TO_SLUG.items():
        if slug:
            mapping[it_name.upper()] = slug

    return mapping


def find_slug_for_feat(feat, it_to_slug, base_map):
    """Try to find the EN slug for an Italian feat.

    Strategies:
    1. Exact match on IT name (uppercase)
    2. Manual mapping
    3. Fuzzy match on IT name against overlay names
    4. Try slugifying the IT name and checking base
    """
    name_upper = feat["name_it"].upper()

    # 1. Exact match
    if name_upper in it_to_slug:
        return it_to_slug[name_upper]

    # 2. Manual mapping (already included in it_to_slug)

    # 3. Try slugifying the EN-style name
    # Some IT names are the same as EN (e.g., "Track" → "track")
    slug_attempt = slugify(feat["name_it"])
    if slug_attempt in base_map:
        return slug_attempt

    # 4. Fuzzy match against overlay names
    best_ratio = 0
    best_slug = None
    for key, slug in it_to_slug.items():
        ratio = SequenceMatcher(None, name_upper, key).ratio()
        if ratio > best_ratio and ratio > 0.85:
            best_ratio = ratio
            best_slug = slug

    return best_slug


def build_desc_html(feat):
    """Build a desc_html from the individual fields."""
    parts = []

    if feat.get("preamble"):
        parts.append(f"<p>{feat['preamble']}</p>")

    if feat.get("prerequisites"):
        parts.append(f"<p><strong>Prerequisiti:</strong> {feat['prerequisites']}</p>")

    if feat.get("benefit"):
        parts.append(f"<p><strong>Beneficio:</strong> {feat['benefit']}</p>")

    if feat.get("normal"):
        parts.append(f"<p><strong>Normale:</strong> {feat['normal']}</p>")

    if feat.get("special"):
        parts.append(f"<p><strong>Speciale:</strong> {feat['special']}</p>")

    return "\n".join(parts)


def strip_html(text):
    """Remove HTML tags from text."""
    return re.sub(r"<[^>]+>", "", text).strip()


def main():
    dry_run = "--dry-run" in sys.argv

    if dry_run:
        print("=== DRY RUN MODE (no files will be modified) ===\n")

    # Load base and overlay data
    with open(BASE_PATH, encoding="utf-8") as f:
        base = json.load(f)
    with open(OVERLAY_PATH, encoding="utf-8") as f:
        overlay = json.load(f)

    base_map = {e["slug"]: e for e in base}
    overlay_map = {e["slug"]: e for e in overlay}

    # Build IT name → slug mapping
    it_to_slug = build_it_to_slug_map(base, overlay)

    # Parse all PDF SRD feat files
    feat_files = [
        SOURCES_DIR / "talentielenco.html",
        SOURCES_DIR / "talenti_bonusguerriero.html",
        SOURCES_DIR / "talenti_creazioneoggetto.html",
        SOURCES_DIR / "talenti_metamagia.html",
        SOURCES_DIR / "talenti_mostri.html",
    ]

    all_parsed = {}
    for filepath in feat_files:
        if not filepath.exists():
            print(f"  Warning: {filepath} not found, skipping")
            continue
        feats = extract_feats_from_html(filepath)
        for feat in feats:
            key = feat["name_it"].upper()
            if key not in all_parsed:
                all_parsed[key] = feat

    print(f"Parsed {len(all_parsed)} unique feats from PDF SRD IT\n")

    # Match parsed feats to base data
    matched = 0
    unmatched = []
    updated = 0
    added = 0

    for key, feat in sorted(all_parsed.items()):
        slug = find_slug_for_feat(feat, it_to_slug, base_map)

        if not slug:
            unmatched.append(feat["name_it"])
            continue

        if slug not in base_map:
            unmatched.append(f"{feat['name_it']} (slug: {slug} not in base)")
            continue

        matched += 1

        # Update or create overlay entry
        if slug in overlay_map:
            entry = overlay_map[slug]
            changes = []

            # Update fields if the overlay doesn't have them
            for field in ["prerequisites", "benefit", "normal", "special"]:
                pdf_val = feat.get(field, "")
                existing_val = entry.get(field, "")
                if pdf_val and not existing_val:
                    if not dry_run:
                        entry[field] = strip_html(pdf_val)
                    changes.append(f"+{field}")

            # Add desc_html if missing
            if not entry.get("desc_html", "").strip():
                desc = build_desc_html(feat)
                if desc:
                    if not dry_run:
                        entry["desc_html"] = desc
                    changes.append("+desc_html")

            # Add type if missing
            if not entry.get("type", "").strip() and feat.get("type_it"):
                if not dry_run:
                    entry["type"] = feat["type_it"].title()
                changes.append("+type")

            # Tag source if not already tagged
            if "translation_source" not in entry and changes:
                if not dry_run:
                    entry["translation_source"] = "pdf"
                    entry["reviewed"] = False

            if changes:
                updated += 1
                print(f"  Updated {slug}: {', '.join(changes)}")
        else:
            # Create new overlay entry
            new_entry = {"slug": slug, "name": feat["name_it"].title()}

            for field in ["prerequisites", "benefit", "normal", "special"]:
                val = feat.get(field, "")
                if val:
                    new_entry[field] = strip_html(val)

            desc = build_desc_html(feat)
            if desc:
                new_entry["desc_html"] = desc

            if feat.get("type_it"):
                new_entry["type"] = feat["type_it"].title()

            new_entry["translation_source"] = "pdf"
            new_entry["reviewed"] = False

            if not dry_run:
                overlay.append(new_entry)
                overlay_map[slug] = new_entry
            added += 1
            print(f"  Added {slug}: {new_entry['name']}")

    print(f"\nSummary:")
    print(f"  Parsed:    {len(all_parsed)} feats from PDF SRD IT")
    print(f"  Matched:   {matched}")
    print(f"  Updated:   {updated} overlay entries")
    print(f"  Added:     {added} new overlay entries")
    print(f"  Unmatched: {len(unmatched)}")

    if unmatched:
        print(f"\nUnmatched feats:")
        for u in sorted(unmatched):
            print(f"    {u}")

    if not dry_run and (updated > 0 or added > 0):
        # Sort overlay by slug
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
