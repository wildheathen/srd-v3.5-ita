#!/usr/bin/env python3
"""
Compare Italian spell names between NAME_MAP (translate_spells.py) and
the OCR'd manual (testo manuale/manuale base completo.txt).

Produces a report with:
  A) Exact matches (confirmed correct)
  B) Fuzzy matches (discrepancies to review)
  C) Manual names with no match in NAME_MAP
  D) NAME_MAP entries with no match in manual
"""

import json
import re
import sys
import unicodedata
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(REPO_ROOT / "scripts"))
from translate_spells import NAME_MAP
from convert_manual import (
    load_lines, find_spell_section, parse_spells_from_text
)


def normalize(s):
    """Normalize string for comparison: lowercase, strip accents, collapse whitespace."""
    s = s.lower().strip()
    s = unicodedata.normalize("NFKD", s)
    s = s.encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[''`]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s


def simplify(s):
    """Remove articles/prepositions for fuzzy match."""
    s = re.sub(
        r"\b(i|il|lo|la|le|gli|l'|l |del|della|dei|delle|dell'|degli|"
        r"di|da|in|su|con|per|tra|fra|al|alla|alle|agli|a)\b",
        "", s.lower()
    )
    s = re.sub(r"[''`]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def main():
    # Build inverted NAME_MAP: Italian lowercase → English name
    it_to_en = {}
    en_to_it = {}
    for en, it in NAME_MAP.items():
        it_to_en[it.lower()] = en
        en_to_it[en] = it

    # Extract spell names from the manual
    print("Loading manual text...")
    lines = load_lines()
    start, end = find_spell_section(lines)
    print("Parsing spells from manual...")
    spells = parse_spells_from_text(lines, start, end)
    print(f"Found {len(spells)} spell entries in manual\n")

    # Clean manual names
    manual_names = []
    for s in spells:
        name = s["name_it"].strip()
        # Fix trailing single letters from OCR
        name = re.sub(r"\s+([a-zà-ú])\s*$", r"\1", name)
        name = re.sub(r"\bmass\s+a\b", "massa", name)
        name = re.sub(r"\s+", " ", name).strip()
        manual_names.append(name)

    exact_matches = []
    fuzzy_matches = []
    manual_unmatched = []

    matched_en_names = set()

    for manual_name in manual_names:
        mn_lower = manual_name.lower()

        # Try exact match
        en_name = it_to_en.get(mn_lower)
        if en_name:
            namemap_it = en_to_it[en_name]
            exact_matches.append((manual_name, en_name, namemap_it))
            matched_en_names.add(en_name)
            continue

        # Try accent-normalized match
        mn_norm = normalize(manual_name)
        found = False
        for it_val, en_val in it_to_en.items():
            if normalize(it_val) == mn_norm:
                namemap_it = en_to_it[en_val]
                fuzzy_matches.append((manual_name, en_val, namemap_it, "accenti"))
                matched_en_names.add(en_val)
                found = True
                break

        if found:
            continue

        # Try simplified match (remove articles/prepositions)
        mn_simple = simplify(mn_lower)
        for it_val, en_val in it_to_en.items():
            it_simple = simplify(it_val)
            if mn_simple == it_simple:
                namemap_it = en_to_it[en_val]
                fuzzy_matches.append((manual_name, en_val, namemap_it, "articoli/preposizioni"))
                matched_en_names.add(en_val)
                found = True
                break
            # Try verb suffix variations
            for sfrom, sto in [("", "re"), ("", "e"), ("a", "are"), ("e", "ere"),
                               ("re", ""), ("are", "a"), ("ere", "e"), ("ire", "i")]:
                trial = mn_simple[:-len(sfrom)] + sto if sfrom and mn_simple.endswith(sfrom) else (mn_simple + sto if not sfrom else None)
                if trial and trial == it_simple:
                    namemap_it = en_to_it[en_val]
                    fuzzy_matches.append((manual_name, en_val, namemap_it, "coniugazione verbo"))
                    matched_en_names.add(en_val)
                    found = True
                    break
            if found:
                break

        if found:
            continue

        # Try substring matching
        for it_val, en_val in it_to_en.items():
            if mn_lower.startswith(it_val) or it_val.startswith(mn_lower):
                if abs(len(mn_lower) - len(it_val)) <= 3:
                    namemap_it = en_to_it[en_val]
                    fuzzy_matches.append((manual_name, en_val, namemap_it, "sottostringa"))
                    matched_en_names.add(en_val)
                    found = True
                    break

        if not found:
            manual_unmatched.append(manual_name)

    # Find NAME_MAP entries with no manual match
    namemap_unmatched = []
    for en_name, it_name in sorted(en_to_it.items()):
        if en_name not in matched_en_names:
            namemap_unmatched.append((en_name, it_name))

    # Print report
    print("=" * 70)
    print(f"REPORT: Verifica nomi incantesimi IT")
    print("=" * 70)

    print(f"\n--- A) Match esatti: {len(exact_matches)} ---")
    for manual, en, it in sorted(exact_matches, key=lambda x: x[0]):
        print(f"  OK  {manual}  =  {en}")

    print(f"\n--- B) Match fuzzy (discrepanze da revisionare): {len(fuzzy_matches)} ---")
    for manual, en, namemap_it, reason in sorted(fuzzy_matches, key=lambda x: x[0]):
        if manual.lower() != namemap_it.lower():
            print(f"  ~   Manuale: \"{manual}\"  vs  NAME_MAP: \"{namemap_it}\"  ({en}) [{reason}]")
        else:
            print(f"  OK  {manual}  ~  {en}  [{reason}]")

    print(f"\n--- C) Non matchati dal manuale: {len(manual_unmatched)} ---")
    for name in sorted(manual_unmatched):
        print(f"  ?   {name}")

    print(f"\n--- D) NAME_MAP senza match nel manuale: {len(namemap_unmatched)} ---")
    for en, it in namemap_unmatched:
        print(f"  -   {en}  ({it})")

    print(f"\n{'=' * 70}")
    print(f"RIEPILOGO:")
    print(f"  Manuale: {len(manual_names)} incantesimi")
    print(f"  NAME_MAP: {len(NAME_MAP)} traduzioni")
    print(f"  Match esatti: {len(exact_matches)}")
    print(f"  Match fuzzy: {len(fuzzy_matches)}")
    print(f"  Non matchati (manuale): {len(manual_unmatched)}")
    print(f"  Non matchati (NAME_MAP): {len(namemap_unmatched)}")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
