#!/usr/bin/env python3
"""Importa traduzioni da un file CSV nell'overlay IT.

Legge un CSV generato da export_for_translation.py (o creato a mano),
valida le entry e le merge nell'overlay JSON della categoria specificata.

Usage:
    python scripts/import_from_csv.py contrib/monsters_desc_html.csv monsters
    python scripts/import_from_csv.py contrib/rules_desc_html.csv rules --apply

Senza --apply, mostra solo le modifiche senza scrivere.
"""

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"


def find_field_column(headers):
    """Find the IT translation column (ends with _it)."""
    for h in headers:
        if h.endswith("_it") and h != "name_it":
            return h
    return None


def main():
    if len(sys.argv) < 3:
        print("Uso: python scripts/import_from_csv.py <file.csv> <categoria> [--apply]")
        print("  Esempio: python scripts/import_from_csv.py contrib/monsters_desc_html.csv monsters --apply")
        sys.exit(1)

    csv_path = Path(sys.argv[1])
    category = sys.argv[2]
    apply_mode = "--apply" in sys.argv

    overlay_path = DATA_DIR / "i18n" / "it" / f"{category}.json"
    en_path = DATA_DIR / f"{category}.json"

    if not csv_path.exists():
        print(f"Errore: {csv_path} non trovato")
        sys.exit(1)

    if not en_path.exists():
        print(f"Errore: {en_path} non trovato")
        sys.exit(1)

    # Load EN base for slug validation
    with open(en_path, encoding="utf-8") as f:
        en_data = json.load(f)
    valid_slugs = {e["slug"] for e in en_data}

    # Load existing overlay
    overlay = []
    if overlay_path.exists():
        with open(overlay_path, encoding="utf-8") as f:
            overlay = json.load(f)
    overlay_by_slug = {e["slug"]: e for e in overlay}

    # Read CSV
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        field_col = find_field_column(headers)

        if not field_col:
            print(f"Errore: nessuna colonna *_it trovata. Colonne: {headers}")
            sys.exit(1)

        # Extract field name from column name (e.g. "desc_html_it" -> "desc_html")
        field_name = field_col.replace("_it", "")

        added = 0
        updated = 0
        skipped = 0
        errors = []

        for row in reader:
            slug = row.get("slug", "").strip()
            translation = row.get(field_col, "").strip()

            if not slug:
                continue
            if not translation:
                skipped += 1
                continue

            # Validate slug
            if slug not in valid_slugs:
                errors.append(f"Slug sconosciuto: {slug}")
                continue

            # Validate HTML for desc_html fields
            if "html" in field_name:
                if "<" not in translation:
                    errors.append(f"{slug}: desc_html senza tag HTML — serve almeno <p>...</p>")
                    continue

            # Validate JSON structure
            try:
                # Ensure it's valid text (not broken encoding)
                translation.encode("utf-8").decode("utf-8")
            except UnicodeError:
                errors.append(f"{slug}: encoding non valido")
                continue

            # Merge into overlay
            if slug not in overlay_by_slug:
                overlay_by_slug[slug] = {"slug": slug}

            entry = overlay_by_slug[slug]
            if field_name in entry and entry[field_name] == translation:
                skipped += 1
                continue

            if field_name in entry:
                updated += 1
                action = "AGGIORNATO"
            else:
                added += 1
                action = "AGGIUNTO"

            if apply_mode:
                entry[field_name] = translation
            print(f"  {action}: {slug} ({len(translation)} chars)")

    print(f"\n{'='*60}")
    print(f"Campo: {field_name}")
    print(f"Aggiunti: {added}")
    print(f"Aggiornati: {updated}")
    print(f"Saltati (vuoti/invariati): {skipped}")
    print(f"Errori: {len(errors)}")

    if errors:
        print("\n--- Errori ---")
        for e in errors:
            print(f"  {e}")

    if apply_mode and (added > 0 or updated > 0):
        result = sorted(overlay_by_slug.values(), key=lambda x: x.get("slug", ""))
        with open(overlay_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"\nScritto {overlay_path}")
    elif not apply_mode:
        print(f"\nDry-run. Usa --apply per scrivere le modifiche.")


if __name__ == "__main__":
    main()
