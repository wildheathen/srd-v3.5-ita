#!/usr/bin/env python3
"""
crowdin_generate.py
Genera i file flat JSON per Crowdin da usare come sorgente/traduzione.
Formato: {"slug.field": "valore"}

Usage:
  python3 scripts/crowdin_generate.py
"""

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Campi da tradurre per ogni file (escludi: slug, translation_source, reviewed)
TRANSLATABLE_FIELDS = {
    "skills":    ["name", "check"],
    "classes":   ["name", "manual_name", "reference"],
    "equipment": ["name", "category"],
    "feats":     ["name", "manual_name", "reference"],
    "monsters":  ["name", "desc_html"],
    "races":     ["name", "traits", "desc_html"],
    "rules":     ["name", "desc_html"],
    "spells":    ["name", "summary_it", "school", "level", "manual_name", "reference"],
}

def to_flat(entries, fields):
    """Converte array di oggetti in flat JSON: {slug.field: value}"""
    result = {}
    for entry in entries:
        slug = entry.get("slug", "")
        if not slug:
            continue
        for field in fields:
            val = entry.get(field)
            if val is not None and val != "" and val != []:
                # Converti liste in stringa separata da newline (es. traits)
                if isinstance(val, list):
                    val = "\n".join(str(v) for v in val)
                result[f"{slug}.{field}"] = str(val)
    return result

def generate():
    en_out_dir = os.path.join(ROOT, "data", "i18n", "crowdin", "en")
    it_out_dir = os.path.join(ROOT, "data", "i18n", "crowdin", "it")
    os.makedirs(en_out_dir, exist_ok=True)
    os.makedirs(it_out_dir, exist_ok=True)

    for name, fields in TRANSLATABLE_FIELDS.items():
        # Sorgente EN
        src_path = os.path.join(ROOT, "data", f"{name}.json")
        with open(src_path, encoding="utf-8") as f:
            src_data = json.load(f)
        
        en_flat = to_flat(src_data, fields)
        en_path = os.path.join(en_out_dir, f"{name}.json")
        with open(en_path, "w", encoding="utf-8") as f:
            json.dump(en_flat, f, indent=2, ensure_ascii=False)
        print(f"[EN] {name}.json: {len(en_flat)} stringhe")

        # Traduzione IT (da file IT esistente)
        it_src_path = os.path.join(ROOT, "data", "i18n", "it", f"{name}.json")
        if os.path.exists(it_src_path):
            with open(it_src_path, encoding="utf-8") as f:
                it_data = json.load(f)
            it_flat = to_flat(it_data, fields)
            # Includi solo le chiavi che esistono nella sorgente EN
            it_flat_filtered = {k: v for k, v in it_flat.items() if k in en_flat}
            it_path = os.path.join(it_out_dir, f"{name}.json")
            with open(it_path, "w", encoding="utf-8") as f:
                json.dump(it_flat_filtered, f, indent=2, ensure_ascii=False)
            pct = len(it_flat_filtered) / len(en_flat) * 100 if en_flat else 0
            print(f"[IT] {name}.json: {len(it_flat_filtered)}/{len(en_flat)} stringhe ({pct:.1f}% tradotto)")
        else:
            # Crea file IT vuoto (solo chiavi)
            it_flat = {k: "" for k in en_flat}
            it_path = os.path.join(it_out_dir, f"{name}.json")
            with open(it_path, "w", encoding="utf-8") as f:
                json.dump(it_flat, f, indent=2, ensure_ascii=False)
            print(f"[IT] {name}.json: 0/{len(en_flat)} stringhe (0% - nuovo)")

    print("\nFatto! File generati in data/i18n/crowdin/")

if __name__ == "__main__":
    generate()
