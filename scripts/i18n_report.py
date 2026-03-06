#!/usr/bin/env python3
"""
i18n Quality Report — Dashboard per verificare la qualit delle traduzioni.

Confronta i dati base EN con gli overlay IT per ogni categoria,
rileva problemi (campi mancanti, OCR, residui inglesi) e genera report.

Uso:
    python scripts/i18n_report.py                          # Dashboard completa
    python scripts/i18n_report.py spells                   # Solo spells
    python scripts/i18n_report.py spells --field desc_html # Solo un campo
    python scripts/i18n_report.py spells --field desc_html --details  # Mostra record
    python scripts/i18n_report.py --save                   # Salva report JSON
    python scripts/i18n_report.py --frontend               # Genera JSON per frontend
"""

import argparse
import io
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# Force UTF-8 output on Windows
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"

# Definizione campi traducibili per categoria
TRANSLATABLE_FIELDS = {
    "spells": [
        "name", "school", "subschool", "descriptor", "level", "components",
        "casting_time", "range", "target_area_effect", "duration",
        "saving_throw", "spell_resistance", "desc_html",
    ],
    "feats": ["name", "type", "prerequisites", "benefit", "normal", "special", "desc_html"],
    "monsters": ["name", "type", "alignment", "environment", "organization", "desc_html"],
    "classes": ["name", "alignment", "table_html", "desc_html"],
    "races": ["name", "traits", "desc_html"],
    "equipment": ["name"],
    "rules": ["name", "desc_html"],
}

# --- Detect functions ---

OCR_PATTERNS = [
    (r"ziuna\b", "OCR suffix: ziuna -> zione"),
    (r"siuna\b", "OCR suffix: siuna -> sione"),
    (r"\bpe r\b", "parola spezzata: 'pe r'"),
    (r"\bd i\b", "parola spezzata: 'd i'"),
    (r"\bch e\b", "parola spezzata: 'ch e'"),
    (r"\bco n\b", "parola spezzata: 'co n'"),
    (r"\bogn i\b", "parola spezzata: 'ogn i'"),
    (r"\btr e\b", "parola spezzata: 'tr e'"),
    (r"\bcentrat a\b", "parola spezzata: 'centrat a'"),
    (r"\btoccat i\b", "parola spezzata: 'toccat i'"),
    (r"\blivell o\b", "parola spezzata: 'livell o'"),
    (r"\braggi o\b", "parola spezzata: 'raggi o'"),
    (r"\d+\s*rn\b", "OCR: rn -> m"),
    (r"\d+\s*tn\b", "OCR: tn -> m"),
    (r"\u00b7", "carattere corrotto: middle dot"),
    (r"\u201e", "carattere corrotto: double low quote"),
    (r"- \.", "artefatto: '- .'"),
    (r"toscata\b", "OCR: toscata -> toccata"),
    (r"viventetoscata", "OCR: parole fuse"),
    (r"pi\s+\u00f9u", "OCR: pi uu -> piu"),
    (r"\boa/", "OCR: oa/ -> ora/"),
    (r"\bgiono\b", "OCR: giono -> giorno"),
    (r"\bgioni\b", "OCR: gioni -> giorni"),
    (r"\bincantatoe\b", "OCR: incantatoe -> incantatore"),
    (r"\bmoe\b", "OCR: moe -> more"),
]

ENGLISH_TOKENS = re.compile(
    r"\b(the|and|or|with|that|which|can|has|have|are|is|was|were|this|"
    r"spell|effect|target|bonus|check|damage|attack|save|class|"
    r"ability|skill|feat|character|weapon|armor|shield|"
    r"you|your|she|her|its|they|their|"
    r"must|may|cannot|does not|instead|however|although|"
    r"each|every|any|all|no|not|if|when|while|until|"
    r"within|against|upon|from|into|through|"
    r"hit points|hit dice|caster level|spell level|"
    r"saving throw|base attack|armor class|"
    r"standard action|full-round action|free action|"
    r"subject|failure|success|otherwise)\b",
    re.IGNORECASE,
)

# Words that look English but are valid Italian
ITALIAN_FALSE_POSITIVES = {
    "creature", "per", "area", "medium", "line", "round", "no",
    "base", "i", "a", "e", "o", "con", "in", "non", "come",
    "bonus", "all", "standard", "special",
}

# Fields where identical EN/IT values are legitimate (not a translation issue).
# Each entry is a regex that matches values which are correctly the same in both languages.
IDENTICAL_EXCEPTIONS = {
    # Components use international abbreviations: V, S, M, F, DF, XP
    "components": re.compile(r"^[VSMF,/\s]*(DF|XP)?[VSMF,/\s]*$"),
    # Level uses class abbreviations shared in Italian: Brd 3, Drd 1, Rgr 2, etc.
    "level": re.compile(r"^[A-Za-z/]+\s+\d+(,\s*[A-Za-z/]+\s+\d+)*$"),
    # Casting time: "1 round" is used in Italian too
    "casting_time": re.compile(r"^\d+\s*round", re.IGNORECASE),
    # Duration: "1 round", "1 min." are used in Italian too
    "duration": re.compile(r"^\d+\s*(round|min\.)", re.IGNORECASE),
    # Saving throw: "No" is the same in Italian
    "saving_throw": re.compile(r"^No$", re.IGNORECASE),
    # Spell resistance: "No" is the same in Italian
    "spell_resistance": re.compile(r"^No$", re.IGNORECASE),
    # Prerequisites: only "Int" is the same in both languages (Intelligence/Intelligenza)
    # Str→For, Dex→Des, Con→Cos, Wis→Sag, Cha→Car are different
    "prerequisites": re.compile(r"^Int\s+\d+\.?$", re.IGNORECASE),
}

# Names that are legitimately identical in Italian (proper nouns, borrowed terms).
# If a name is present in the overlay with the same value as EN, it was intentional.
# This applies to "name" field across all categories.
IDENTICAL_NAME_EXCEPTIONS = {
    # D&D class names used in Italian
    "ranger",
    # Spell names used in Italian
    "clone", "shillelagh", "status",
    # Monster proper names — creatures with no Italian equivalent.
    # These are auto-detected: if the name is in the overlay, it's intentional.
}


def detect_ocr_issues(value):
    """Detect OCR artifacts in a value. Returns list of (pattern_desc, match)."""
    if not value or len(value) > 2000:  # skip very long HTML
        return []
    issues = []
    for pattern, desc in OCR_PATTERNS:
        if re.search(pattern, value):
            issues.append(desc)
    return issues


def detect_english_residue(value):
    """Detect English words in a value that should be Italian."""
    if not value or len(value) > 500:  # skip long HTML content
        return []
    matches = ENGLISH_TOKENS.findall(value)
    return [m for m in matches if m.lower() not in ITALIAN_FALSE_POSITIVES]


def analyze_field(en_entries, it_entries, field):
    """Analyze a single field across all entries."""
    en_by_slug = {e["slug"]: e for e in en_entries}
    it_by_slug = {e["slug"]: e for e in it_entries}

    stats = {
        "present": 0,
        "missing": 0,
        "identical_to_en": 0,
        "ocr_issues": 0,
        "english_residue": 0,
        "issues": [],
    }

    all_slugs = set(en_by_slug.keys()) | set(it_by_slug.keys())

    for slug in sorted(all_slugs):
        en_val = en_by_slug.get(slug, {}).get(field, "")
        it_entry = it_by_slug.get(slug, {})
        it_val = it_entry.get(field, "")

        # For list fields (like traits), convert to string for comparison
        if isinstance(en_val, list):
            en_val = json.dumps(en_val, ensure_ascii=False)
        if isinstance(it_val, list):
            it_val = json.dumps(it_val, ensure_ascii=False)

        if not en_val and not it_val:
            continue  # field doesn't exist in either

        if not it_val and en_val:
            stats["missing"] += 1
            stats["issues"].append({
                "slug": slug,
                "type": "missing",
                "en_value": str(en_val)[:120],
            })
            continue

        stats["present"] += 1

        # Check if identical to EN
        if it_val == en_val and en_val:
            # Check if this is a legitimate exception (value is correctly the same)
            exception_re = IDENTICAL_EXCEPTIONS.get(field)
            if exception_re and exception_re.match(str(it_val)):
                continue  # legitimate, skip
            # For "name" field: if slug is in the overlay, the translator kept it intentionally
            if field == "name" and slug in it_by_slug and "name" in it_by_slug[slug]:
                continue  # translator explicitly set this name
            stats["identical_to_en"] += 1
            stats["issues"].append({
                "slug": slug,
                "type": "identical",
                "value": str(it_val)[:120],
                "en_value": str(en_val)[:120],
            })
            continue

        # OCR check (skip very long HTML)
        if field != "desc_html" and field != "table_html":
            ocr = detect_ocr_issues(str(it_val))
            if ocr:
                stats["ocr_issues"] += 1
                stats["issues"].append({
                    "slug": slug,
                    "type": "ocr",
                    "value": str(it_val)[:120],
                    "en_value": str(en_val)[:120],
                    "details": ocr,
                })

            eng = detect_english_residue(str(it_val))
            if eng:
                stats["english_residue"] += 1
                stats["issues"].append({
                    "slug": slug,
                    "type": "english",
                    "value": str(it_val)[:120],
                    "en_value": str(en_val)[:120],
                    "words": eng,
                })
        else:
            # For HTML fields: check length anomaly
            if en_val and it_val and len(str(it_val)) < len(str(en_val)) * 0.3:
                stats["issues"].append({
                    "slug": slug,
                    "type": "length_anomaly",
                    "en_len": len(str(en_val)),
                    "it_len": len(str(it_val)),
                })

    return stats


def analyze_category(category, lang="it"):
    """Analyze a full category. Returns result dict."""
    en_path = DATA_DIR / f"{category}.json"
    it_path = DATA_DIR / "i18n" / lang / f"{category}.json"

    if not en_path.exists():
        return None
    if not it_path.exists():
        return {"category": category, "lang": lang, "error": "overlay file missing"}

    with open(en_path, "r", encoding="utf-8") as f:
        en_data = json.load(f)
    with open(it_path, "r", encoding="utf-8") as f:
        it_data = json.load(f)

    fields = TRANSLATABLE_FIELDS.get(category, [])
    result = {
        "category": category,
        "lang": lang,
        "total_en": len(en_data),
        "total_it": len(it_data),
        "fields": {},
    }

    for field in fields:
        result["fields"][field] = analyze_field(en_data, it_data, field)

    return result


# --- Display functions ---

def bar(current, total, width=20):
    """Create a progress bar string."""
    if total == 0:
        return " " * width
    filled = int(width * current / total)
    return "\u2588" * filled + "\u2591" * (width - filled)


def print_dashboard(results):
    """Print formatted dashboard to console."""
    print()
    print("=" * 66)
    print(f"  i18n Quality Report")
    print("=" * 66)

    for r in results:
        if r is None:
            continue
        if "error" in r:
            print(f"\n  {r['category'].upper()}: {r['error']}")
            continue

        cat = r["category"].upper()
        print(f"\n  {cat} ({r['total_it']} entries)")
        print("  " + "-" * 62)

        total_issues = 0
        for field, stats in r["fields"].items():
            total = stats["present"] + stats["missing"]
            if total == 0:
                continue
            pct = stats["present"] * 100 // total if total else 0
            b = bar(stats["present"], total)
            print(f"    {field:<22} {b} {stats['present']:>4}/{total:<4} {pct:>3}%")

            n_issues = stats["ocr_issues"] + stats["english_residue"] + stats["identical_to_en"]
            if n_issues > 0:
                parts = []
                if stats["identical_to_en"]:
                    parts.append(f"{stats['identical_to_en']} identici EN")
                if stats["ocr_issues"]:
                    parts.append(f"{stats['ocr_issues']} OCR")
                if stats["english_residue"]:
                    parts.append(f"{stats['english_residue']} inglese")
                print(f"    {'':22}   -> {', '.join(parts)}")
                total_issues += n_issues

    print()
    print("=" * 66)


def print_field_details(result, field_name):
    """Print detailed issues for a specific field."""
    if result is None or "error" in result:
        print("No data available")
        return

    stats = result["fields"].get(field_name)
    if not stats:
        print(f"Field '{field_name}' not found in {result['category']}")
        return

    total = stats["present"] + stats["missing"]
    print(f"\n{result['category']}.{field_name}")
    print(f"  Presenti: {stats['present']}/{total}")
    print(f"  Mancanti: {stats['missing']}")
    print(f"  Identici a EN: {stats['identical_to_en']}")
    print(f"  Problemi OCR: {stats['ocr_issues']}")
    print(f"  Residui inglese: {stats['english_residue']}")

    if not stats["issues"]:
        print("\n  Nessun problema rilevato!")
        return

    # Group by type
    by_type = {}
    for issue in stats["issues"]:
        t = issue["type"]
        by_type.setdefault(t, []).append(issue)

    for itype, issues in by_type.items():
        label = {
            "missing": "Mancanti",
            "identical": "Identici a EN (non tradotti?)",
            "ocr": "Artefatti OCR",
            "english": "Residui inglese",
            "length_anomaly": "Lunghezza anomala",
        }.get(itype, itype)

        print(f"\n  --- {label}: {len(issues)} ---")
        for issue in issues[:50]:  # limit output
            slug = issue["slug"]
            val = issue.get("value", issue.get("en_value", ""))
            detail = issue.get("details", issue.get("words", ""))
            if detail:
                print(f"    {slug}: {val}")
                print(f"      -> {detail}")
            else:
                print(f"    {slug}: {val}")


def save_report(results, lang):
    """Save results as JSON files."""
    out_dir = REPO_ROOT / "reports" / "i18n" / lang
    out_dir.mkdir(parents=True, exist_ok=True)

    for r in results:
        if r is None:
            continue
        path = out_dir / f"{r['category']}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(r, f, ensure_ascii=False, indent=2)
        print(f"  Saved: {path}")


def generate_frontend_json(results, lang):
    """Generate translation-status JSON for the frontend dashboard."""
    report = {
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

    for r in results:
        if r is None or "error" in r:
            continue

        cat_name = r["category"]
        cat_data = {
            "total": r["total_en"],
            "overlay_count": r["total_it"],
            "fields": {},
        }

        for field_name, stats in r["fields"].items():
            total = stats["present"] + stats["missing"]
            if total == 0:
                continue

            translated = stats["present"] - stats["identical_to_en"]
            pct = round(translated / total * 100, 1) if total > 0 else 0.0

            field_data = {
                "translated": translated,
                "suspicious": stats["identical_to_en"],
                "total": total,
                "percent": pct,
                "identical_to_en": stats["identical_to_en"],
                "ocr_issues": stats["ocr_issues"],
                "english_residue": stats["english_residue"],
            }

            # Include issues (limit to 50 per field to keep JSON small)
            if stats["issues"]:
                field_data["issues"] = stats["issues"][:50]

            cat_data["fields"][field_name] = field_data

            report["summary"]["total_fields"] += total
            report["summary"]["translated_fields"] += translated

        report["categories"][cat_name] = cat_data
        report["summary"]["total_entries"] += r["total_en"]

    total = report["summary"]["total_fields"]
    done = report["summary"]["translated_fields"]
    report["summary"]["overall_percent"] = round(done / total * 100, 1) if total > 0 else 0.0

    return report


def save_frontend_json(lang):
    """Generate and save translation-status JSON files for the frontend."""
    categories = list(TRANSLATABLE_FIELDS.keys())
    results = [analyze_category(cat, lang) for cat in categories]

    report = generate_frontend_json(results, lang)

    out_path = DATA_DIR / f"translation-status-{lang}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"  Written: {out_path}")

    # Also write legacy translation-status.json
    legacy_path = DATA_DIR / "translation-status.json"
    with open(legacy_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write("\n")

    # Write index
    index = {
        "languages": [lang],
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    index_path = DATA_DIR / "translation-status-index.json"
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"  Written: {index_path}")


def main():
    parser = argparse.ArgumentParser(description="i18n Quality Report")
    parser.add_argument("category", nargs="?", help="Category to analyze (default: all)")
    parser.add_argument("--field", help="Show details for a specific field")
    parser.add_argument("--details", action="store_true", help="Show detailed issue list")
    parser.add_argument("--lang", default="it", help="Language code (default: it)")
    parser.add_argument("--save", action="store_true", help="Save JSON reports")
    parser.add_argument("--frontend", action="store_true", help="Generate translation-status JSON for frontend")
    args = parser.parse_args()

    if args.frontend:
        save_frontend_json(args.lang)
        return

    categories = list(TRANSLATABLE_FIELDS.keys())
    if args.category:
        if args.category not in categories:
            print(f"Unknown category: {args.category}")
            print(f"Available: {', '.join(categories)}")
            sys.exit(1)
        categories = [args.category]

    results = []
    for cat in categories:
        results.append(analyze_category(cat, args.lang))

    if args.field and len(results) == 1:
        print_field_details(results[0], args.field)
        if args.details:
            pass  # details already shown by print_field_details
    else:
        print_dashboard(results)

    if args.save:
        save_report(results, args.lang)


if __name__ == "__main__":
    main()
