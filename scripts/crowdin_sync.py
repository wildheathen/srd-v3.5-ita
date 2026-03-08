#!/usr/bin/env python3
"""
crowdin_sync.py
Sincronizza le traduzioni da Crowdin (flat JSON) verso i file app (array JSON).

Usage:
  # Importa traduzioni da Crowdin → aggiorna data/i18n/it/*.json
  python3 scripts/crowdin_sync.py import it

  # Rigenera i file sorgente EN e IT flat (dopo aggiornamenti alla sorgente)
  python3 scripts/crowdin_sync.py generate
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

METADATA_FIELDS = {"translation_source", "reviewed"}

TRANSLATABLE_FIELDS = {
    "skills":    ["name", "source_book", "check", "action", "special", "synergy", "try_again", "restriction", "untrained", "benefit", "desc_html"],
    "classes":   ["name", "source_book", "reference", "table_html", "desc_html_dndtools", "desc_html"],
    "equipment": ["name", "category"],
    "feats":     ["name", "source_book", "reference", "desc_html"],
    "monsters":  ["name", "source_book", "desc_html"],
    "races":     ["name", "source_book", "traits", "desc_html"],
    "rules":     ["name", "desc_html"],
    "spells":    ["name", "summary_it", "school", "level", "manual_name", "reference", "desc_html"],
}

def import_translations(lang_code):
    """
    Importa flat JSON da data/i18n/crowdin/{lang}/ 
    e aggiorna data/i18n/{lang}/*.json (formato array).
    """
    crowdin_dir = os.path.join(ROOT, "data", "i18n", "crowdin", lang_code)
    app_dir = os.path.join(ROOT, "data", "i18n", lang_code)
    os.makedirs(app_dir, exist_ok=True)

    for name, fields in TRANSLATABLE_FIELDS.items():
        crowdin_path = os.path.join(crowdin_dir, f"{name}.json")
        app_path = os.path.join(app_dir, f"{name}.json")

        if not os.path.exists(crowdin_path):
            print(f"[SKIP] {name}.json - file Crowdin non trovato")
            continue

        # Carica flat JSON da Crowdin
        with open(crowdin_path, encoding="utf-8") as f:
            flat = json.load(f)

        # Raggruppa per slug
        by_slug = {}
        for key, val in flat.items():
            if "." not in key:
                continue
            slug, field = key.split(".", 1)
            if slug not in by_slug:
                by_slug[slug] = {}
            by_slug[slug][field] = val

        # Carica array esistente (se presente) per preservare metadati
        existing = {}
        if os.path.exists(app_path):
            with open(app_path, encoding="utf-8") as f:
                existing_list = json.load(f)
            for entry in existing_list:
                if "slug" in entry:
                    existing[entry["slug"]] = entry

        # Costruisci nuovo array
        new_entries = []
        translated_count = 0
        for slug, translations in by_slug.items():
            entry = {"slug": slug}
            # Preserva metadati esistenti
            if slug in existing:
                for meta_key in METADATA_FIELDS:
                    if meta_key in existing[slug]:
                        entry[meta_key] = existing[slug][meta_key]
            # Aggiorna campi tradotti
            for field in fields:
                if field in translations and translations[field].strip():
                    entry[field] = translations[field]
                    translated_count += 1
            if len(entry) > 1:  # ha almeno un campo oltre slug
                new_entries.append(entry)

        with open(app_path, "w", encoding="utf-8") as f:
            json.dump(new_entries, f, indent=2, ensure_ascii=False)
        print(f"[{lang_code.upper()}] {name}.json: {len(new_entries)} entries, {translated_count} campi tradotti")

def generate():
    """Rigenera i file flat Crowdin da sorgenti."""
    from crowdin_generate import generate as gen
    gen()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "import":
        lang = sys.argv[2] if len(sys.argv) > 2 else "it"
        print(f"Importando traduzioni {lang.upper()} da Crowdin...")
        import_translations(lang)
        print("Sync completato.")
    elif cmd == "generate":
        generate()
    else:
        print(f"Comando sconosciuto: {cmd}")
        print(__doc__)
        sys.exit(1)
