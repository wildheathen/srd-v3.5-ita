#!/usr/bin/env python3
"""Apply Italian spell description translations to the overlay file.

Reads translations from scripts/spell_desc_it.json and merges them into
data/i18n/it/spells.json overlay.

Usage:
    python scripts/apply_spell_translations.py
"""

import json
import os


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(script_dir)

    # Read translations
    trans_path = os.path.join(script_dir, "spell_desc_it.json")
    with open(trans_path, "r", encoding="utf-8") as f:
        translations = json.load(f)

    # Read current overlay
    overlay_path = os.path.join(root_dir, "data", "i18n", "it", "spells.json")
    with open(overlay_path, "r", encoding="utf-8") as f:
        overlay = json.load(f)

    # Build lookup by slug
    overlay_map = {entry["slug"]: entry for entry in overlay}

    # Apply translations
    added = 0
    updated = 0
    for slug, fields in translations.items():
        if slug in overlay_map:
            for field, value in fields.items():
                if field not in overlay_map[slug] or overlay_map[slug][field] != value:
                    overlay_map[slug][field] = value
                    updated += 1
        else:
            entry = {"slug": slug}
            entry.update(fields)
            overlay.append(entry)
            overlay_map[slug] = entry
            added += 1

    # Sort by slug for consistency
    overlay.sort(key=lambda x: x["slug"])

    # Write updated overlay
    with open(overlay_path, "w", encoding="utf-8") as f:
        json.dump(overlay, f, ensure_ascii=False, indent=2)

    print(f"Applied translations: {added} new entries, {updated} field updates")
    print(f"Total overlay entries: {len(overlay)}")


if __name__ == "__main__":
    main()
