#!/usr/bin/env python3
"""
Confronta i dati base EN con gli overlay di traduzione e mostra lo stato.

Uso:
    python scripts/translation_status.py              # tutte le categorie
    python scripts/translation_status.py spells       # solo incantesimi
    python scripts/translation_status.py --lang it    # lingua specifica (default: it)
"""

import json
import sys
import os
from difflib import SequenceMatcher

# Campi traducibili per categoria (esclusi slug e campi puramente numerici)
TRANSLATABLE_FIELDS = {
    "spells": [
        "name", "school", "subschool", "descriptor", "level", "components",
        "casting_time", "range", "target_area_effect", "duration",
        "saving_throw", "spell_resistance", "desc_html",
    ],
    "feats": [
        "name", "type", "prerequisites", "benefit", "normal", "special",
        "desc_html",
    ],
    "classes": [
        "name", "hit_die", "alignment", "table_html", "desc_html",
    ],
    "races": [
        "name", "traits", "desc_html",
    ],
    "monsters": [
        "name", "type", "environment", "organization", "alignment",
        "desc_html",
    ],
    "equipment": [
        "name", "category", "desc_html",
    ],
    "rules": [
        "name", "desc_html",
    ],
}

BAR_WIDTH = 20

SIMILARITY_THRESHOLD = 0.85  # Above this = too similar to EN, likely untranslated


def is_genuinely_translated(overlay_value, base_value):
    """Return True if the overlay value is meaningfully different from the base."""
    if not overlay_value or not base_value:
        return bool(overlay_value)
    # For non-string values (lists, dicts), compare directly
    if not isinstance(overlay_value, str) or not isinstance(base_value, str):
        return overlay_value != base_value
    # Exact match — not translated
    if overlay_value == base_value:
        return False
    # Normalized whitespace match
    if " ".join(overlay_value.split()) == " ".join(base_value.split()):
        return False
    # Similarity check for medium strings (100-5000 chars)
    if 100 < len(base_value) <= 5000:
        ratio = SequenceMatcher(None, base_value, overlay_value).ratio()
        if ratio > SIMILARITY_THRESHOLD:
            return False
    # For very large strings, use a faster heuristic: compare length + sample
    elif len(base_value) > 5000:
        # If lengths are very close, likely untranslated
        len_ratio = min(len(overlay_value), len(base_value)) / max(len(overlay_value), len(base_value))
        if len_ratio > 0.95:
            # Sample: compare first 2000 and last 2000 chars
            sample_base = base_value[:2000] + base_value[-2000:]
            sample_overlay = overlay_value[:2000] + overlay_value[-2000:]
            ratio = SequenceMatcher(None, sample_base, sample_overlay).ratio()
            if ratio > SIMILARITY_THRESHOLD:
                return False
    return True


def load_json(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def make_bar(ratio):
    filled = round(ratio * BAR_WIDTH)
    empty = BAR_WIDTH - filled
    return "█" * filled + "░" * empty


def report_category(category, lang, data_dir):
    base_path = os.path.join(data_dir, f"{category}.json")
    overlay_path = os.path.join(data_dir, "i18n", lang, f"{category}.json")

    base = load_json(base_path)
    overlay = load_json(overlay_path)

    if not base:
        print(f"  (nessun dato base trovato in {base_path})")
        return

    # Index overlay and base by slug
    overlay_map = {}
    for entry in overlay:
        slug = entry.get("slug")
        if slug:
            overlay_map[slug] = entry

    base_map = {e.get("slug"): e for e in base if e.get("slug")}

    fields = TRANSLATABLE_FIELDS.get(category, ["name"])
    total = len(base)
    overlay_count = len(overlay_map)

    print(f"\n{'=' * 50}")
    print(f"  {category.upper()} — {total} entries, {overlay_count} nell'overlay")
    print(f"{'=' * 50}")

    for field in fields:
        # Count how many base entries have this field (non-null)
        base_with_field = sum(
            1 for e in base
            if e.get(field) is not None and e.get(field) != ""
        )
        if base_with_field == 0:
            continue

        # Count how many overlay entries have this field AND are genuinely translated
        translated = sum(
            1 for slug, e in overlay_map.items()
            if field in e and e[field] is not None and e[field] != ""
            and is_genuinely_translated(e[field], base_map.get(slug, {}).get(field, ""))
        )

        # Count suspicious (present but identical/too similar to EN)
        suspicious = sum(
            1 for slug, e in overlay_map.items()
            if field in e and e[field] is not None and e[field] != ""
            and not is_genuinely_translated(e[field], base_map.get(slug, {}).get(field, ""))
        )

        ratio = translated / base_with_field if base_with_field > 0 else 0
        pct = ratio * 100
        bar = make_bar(ratio)

        print(f"  {field:<20s} {translated:>4d}/{base_with_field:<4d} {bar} {pct:5.1f}%")
        if suspicious > 0:
            print(f"    \u26a0 {suspicious} entries have overlay \u2248 EN base (>{SIMILARITY_THRESHOLD*100:.0f}% similar)")

    print()


def generate_json_report(lang, data_dir, categories):
    """Generate a JSON report of translation status."""
    from datetime import datetime, timezone

    result = {
        "lang": lang,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "categories": {},
        "summary": {
            "total_entries": 0,
            "total_fields": 0,
            "translated_fields": 0,
            "overall_percent": 0.0,
        },
    }

    for cat in categories:
        base = load_json(os.path.join(data_dir, f"{cat}.json"))
        overlay = load_json(os.path.join(data_dir, "i18n", lang, f"{cat}.json"))

        overlay_map = {}
        for entry in overlay:
            slug = entry.get("slug")
            if slug:
                overlay_map[slug] = entry

        base_map = {e.get("slug"): e for e in base if e.get("slug")}

        fields = TRANSLATABLE_FIELDS.get(cat, ["name"])
        cat_data = {"total": len(base), "overlay_count": len(overlay_map), "fields": {}}

        for field in fields:
            base_with_field = sum(
                1 for e in base
                if e.get(field) is not None and e.get(field) != ""
            )
            if base_with_field == 0:
                continue

            translated = sum(
                1 for slug, e in overlay_map.items()
                if field in e and e[field] is not None and e[field] != ""
                and is_genuinely_translated(e[field], base_map.get(slug, {}).get(field, ""))
            )

            suspicious = sum(
                1 for slug, e in overlay_map.items()
                if field in e and e[field] is not None and e[field] != ""
                and not is_genuinely_translated(e[field], base_map.get(slug, {}).get(field, ""))
            )

            pct = (translated / base_with_field * 100) if base_with_field > 0 else 0
            cat_data["fields"][field] = {
                "translated": translated,
                "suspicious": suspicious,
                "total": base_with_field,
                "percent": round(pct, 1),
            }

            result["summary"]["total_fields"] += base_with_field
            result["summary"]["translated_fields"] += translated

        result["categories"][cat] = cat_data
        result["summary"]["total_entries"] += len(base)

    total = result["summary"]["total_fields"]
    done = result["summary"]["translated_fields"]
    result["summary"]["overall_percent"] = round(done / total * 100, 1) if total > 0 else 0.0

    return result


def main():
    lang = "it"
    category_filter = None
    json_output = False

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--lang" and i + 1 < len(args):
            lang = args[i + 1]
            i += 2
        elif args[i] == "--json":
            json_output = True
            i += 1
        elif not args[i].startswith("-"):
            category_filter = args[i]
            i += 1
        else:
            i += 1

    # Find data directory relative to script location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(os.path.dirname(script_dir), "data")

    if not os.path.isdir(data_dir):
        print(f"Errore: cartella dati non trovata: {data_dir}")
        sys.exit(1)

    categories = list(TRANSLATABLE_FIELDS.keys())
    if category_filter:
        if category_filter not in categories:
            print(f"Errore: categoria '{category_filter}' non valida.")
            print(f"Categorie disponibili: {', '.join(categories)}")
            sys.exit(1)
        categories = [category_filter]

    if json_output:
        from datetime import datetime, timezone

        # Auto-detect available languages from data/i18n/ subdirectories
        i18n_dir = os.path.join(data_dir, "i18n")
        if os.path.isdir(i18n_dir):
            langs = sorted(
                d for d in os.listdir(i18n_dir)
                if os.path.isdir(os.path.join(i18n_dir, d)) and d != "__pycache__"
            )
        else:
            langs = [lang]

        # Generate per-language status files
        for lng in langs:
            report = generate_json_report(lng, data_dir, categories)
            out_path = os.path.join(data_dir, f"translation-status-{lng}.json")
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
                f.write("\n")
            print(f"Written translation status to {out_path}")

        # Also write legacy translation-status.json (first language)
        if langs:
            report = generate_json_report(langs[0], data_dir, categories)
            out_path = os.path.join(data_dir, "translation-status.json")
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
                f.write("\n")

        # Generate index file
        index = {
            "languages": langs,
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        index_path = os.path.join(data_dir, "translation-status-index.json")
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"Written index to {index_path}")
        return

    print(f"Stato traduzioni [{lang.upper()}]")

    total_base = 0
    total_translated_names = 0

    for cat in categories:
        report_category(cat, lang, data_dir)

        # Quick summary stats
        base = load_json(os.path.join(data_dir, f"{cat}.json"))
        overlay = load_json(os.path.join(data_dir, "i18n", lang, f"{cat}.json"))
        overlay_slugs = {e.get("slug") for e in overlay if e.get("slug")}
        total_base += len(base)
        total_translated_names += sum(
            1 for e in overlay if e.get("name")
        )

    if len(categories) > 1:
        print(f"{'=' * 50}")
        print(f"  TOTALE: {total_translated_names} nomi tradotti su {total_base} entries")
        print(f"{'=' * 50}")


if __name__ == "__main__":
    main()
