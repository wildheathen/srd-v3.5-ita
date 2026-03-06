#!/usr/bin/env python3
"""
Compare spell and feat titles from Italian manual TXT files
against the i18n overlay JSON files.
"""
import json
import re
import sys
from pathlib import Path
from difflib import get_close_matches

ROOT = Path(__file__).resolve().parent.parent

# ── SPELL EXTRACTION FROM TXT ──────────────────────────────────────────

SCHOOLS = [
    "abiurazione", "ammaliamento", "divinazione", "evocazione",
    "illusione", "invocazione", "necromanzia", "trasmutazione",
    "universale",
]

def extract_spell_titles_from_txt(path):
    """Extract spell titles from INCANTESIMI.txt.
    A spell title is a line in title-case followed (within 2 lines) by a school keyword.
    """
    with open(path, encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    titles = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        # Skip lines that look like metadata (contain : or numbers at start)
        if ":" in stripped and any(k in stripped.lower() for k in ["livello", "componenti", "tempo", "raggio", "bersaglio", "durata", "tiro", "resistenza"]):
            continue
        # Check if next 1-3 lines contain a school keyword
        lookahead = " ".join(lines[i+1:i+4]).lower() if i+1 < len(lines) else ""
        has_school = any(s in lookahead for s in SCHOOLS)
        if not has_school:
            continue
        # Title should be relatively short, title-case-ish, no colons
        if ":" in stripped or len(stripped) > 80:
            continue
        # Should start with uppercase
        if not stripped[0].isupper():
            continue
        # Should not be all uppercase (that would be a section header)
        if stripped.isupper() and len(stripped) > 5:
            continue
        # Should not contain typical metadata patterns
        if any(k in stripped.lower() for k in ["livello", "componenti", "tempo di lancio", "raggio d'azione"]):
            continue
        titles.append(stripped)

    return titles


# ── FEAT EXTRACTION FROM TXT ───────────────────────────────────────────

def extract_feat_titles_from_txt(path):
    """Extract feat titles from talenti.txt.
    Read the table of contents section at the beginning.
    """
    with open(path, encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    titles = []
    # The file starts with a table of contents
    # Read line by line, collect feat names
    in_toc = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if "TABELLA" in stripped.upper() and "TALENTI" in stripped.upper():
            in_toc = True
            continue
        if not in_toc:
            continue
        if not stripped:
            continue
        # End of TOC - look for a clear section break
        # TOC entries are short feat names
        # Stop if we hit a very long line (description) or specific markers
        if len(stripped) > 60:
            break
        # Clean up OCR artifacts
        clean = stripped.rstrip("' o").rstrip("'").rstrip(" o").strip()
        if clean and clean[0].isupper():
            titles.append(clean)

    return titles


# ── COMPARISON ──────────────────────────────────────────────────────────

def normalize(s):
    """Normalize a title for fuzzy comparison."""
    s = s.lower().strip()
    s = re.sub(r"[''`]", "'", s)
    s = re.sub(r"\s+", " ", s)
    return s


def compare_titles(txt_titles, overlay_entries, entity_type):
    """Compare titles from manual TXT against overlay JSON names."""
    # Build lookup from overlay
    overlay_names = {}
    for entry in overlay_entries:
        name = entry.get("name", "")
        slug = entry.get("slug", "")
        if name:
            overlay_names[slug] = name

    # Build normalized lookup for TXT titles
    txt_norm = {normalize(t): t for t in txt_titles}
    overlay_norm = {normalize(n): (slug, n) for slug, n in overlay_names.items()}

    print(f"\n{'='*70}")
    print(f"  {entity_type.upper()} COMPARISON")
    print(f"  TXT titles: {len(txt_titles)}, Overlay entries: {len(overlay_names)}")
    print(f"{'='*70}")

    # Find overlay names NOT in TXT (possibly wrong translations)
    mismatches = []
    matched = []
    no_match = []

    for slug, overlay_name in sorted(overlay_names.items()):
        norm_overlay = normalize(overlay_name)
        if norm_overlay in txt_norm:
            matched.append((slug, overlay_name, txt_norm[norm_overlay]))
            continue

        # Try fuzzy match
        close = get_close_matches(norm_overlay, txt_norm.keys(), n=1, cutoff=0.7)
        if close:
            txt_original = txt_norm[close[0]]
            mismatches.append((slug, overlay_name, txt_original))
        else:
            no_match.append((slug, overlay_name))

    print(f"\n  EXACT matches: {len(matched)}")
    print(f"  CLOSE matches (MISMATCHES to fix): {len(mismatches)}")
    print(f"  NO match in TXT: {len(no_match)}")

    if mismatches:
        print(f"\n{'─'*70}")
        print("  MISMATCHES (overlay name ≠ manual name):")
        print(f"{'─'*70}")
        for slug, overlay_name, txt_name in mismatches:
            print(f"  {slug:40s}")
            print(f"    OVERLAY: {overlay_name}")
            print(f"    MANUAL:  {txt_name}")
            print()

    if no_match:
        print(f"\n{'─'*70}")
        print("  NO MATCH IN TXT (may need manual check):")
        print(f"{'─'*70}")
        for slug, overlay_name in no_match:
            print(f"  {slug:40s} → {overlay_name}")

    return mismatches, no_match


def main():
    # Load overlay JSONs
    spells_overlay_path = ROOT / "data" / "i18n" / "it" / "spells.json"
    feats_overlay_path = ROOT / "data" / "i18n" / "it" / "feats.json"
    spells_txt_path = ROOT / "sources" / "testo-manuale" / "INCANTESIMI.txt"
    feats_txt_path = ROOT / "sources" / "testo-manuale" / "talenti.txt"

    with open(spells_overlay_path, encoding="utf-8") as f:
        spells_overlay = json.load(f)
    with open(feats_overlay_path, encoding="utf-8") as f:
        feats_overlay = json.load(f)

    # Extract titles from TXT
    print("Extracting spell titles from TXT...")
    spell_titles = extract_spell_titles_from_txt(spells_txt_path)
    print(f"  Found {len(spell_titles)} spell titles")

    print("Extracting feat titles from TXT...")
    feat_titles = extract_feat_titles_from_txt(feats_txt_path)
    print(f"  Found {len(feat_titles)} feat titles")

    # Compare
    spell_mismatches, spell_no_match = compare_titles(spell_titles, spells_overlay, "Spells")
    feat_mismatches, feat_no_match = compare_titles(feat_titles, feats_overlay, "Feats")

    # Summary
    total_issues = len(spell_mismatches) + len(feat_mismatches)
    print(f"\n{'='*70}")
    print(f"  SUMMARY: {total_issues} mismatches found")
    print(f"  Spell mismatches: {len(spell_mismatches)}")
    print(f"  Feat mismatches: {len(feat_mismatches)}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
