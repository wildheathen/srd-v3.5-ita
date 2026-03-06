#!/usr/bin/env python3
"""
Extract spell and feat names from OCR'd Italian manual TXT files,
clean up OCR artifacts, and compare against i18n overlay JSON.
"""
import json
import re
import sys
from pathlib import Path
from difflib import get_close_matches, SequenceMatcher

ROOT = Path(__file__).resolve().parent.parent

# Schools of magic (Italian) for identifying spell headers
SCHOOL_PATTERNS = [
    "abiurazion", "ammaliament", "divinazion", "evocazion",
    "illusion", "invocazion", "necromanzi", "trasmutazion",
    "universal",
]

def clean_ocr(text):
    """Fix common OCR artifacts in Italian text."""
    text = text.strip()
    # Fix spaces before last 1-2 letters (common OCR break): "acid a" -> "acida"
    text = re.sub(r'\b(\w{3,})\s([aeio])\b', r'\1\2', text)
    # Fix "ment o" -> "mento"
    text = re.sub(r'\b(\w{3,})\s(to|te|ta|ti|no|ne|na|ni|re|le|la|li|lo|se|si|so)\b', r'\1\2', text)
    # Remove trailing punctuation artifacts
    text = re.sub(r'\s*[_`\'"\.\[\]]+\s*$', '', text)
    # Remove leading punctuation artifacts
    text = re.sub(r'^[\.\s_]+', '', text)
    # Collapse multiple spaces
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def has_school_keyword(text):
    """Check if text contains an Italian school of magic keyword."""
    t = text.lower()
    return any(s in t for s in SCHOOL_PATTERNS)


def extract_spells_from_txt(path):
    """Extract spell title lines from INCANTESIMI.txt."""
    with open(path, encoding="utf-8", errors="replace") as f:
        lines = [l.rstrip('\n') for l in f.readlines()]

    titles = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue

        # Check if next 1-3 non-empty lines contain a school keyword
        lookahead_lines = []
        j = i + 1
        while j < min(i + 5, len(lines)) and len(lookahead_lines) < 3:
            if lines[j].strip():
                lookahead_lines.append(lines[j].strip())
            j += 1

        lookahead_text = " ".join(lookahead_lines).lower()

        if has_school_keyword(lookahead_text):
            # This line might be a spell title
            # Filter out metadata lines
            lower = line.lower()
            if any(k in lower for k in ["livello", "componenti", "tempo di lancio",
                    "raggio", "bersaglio", "durata", "tiro salvezza", "resistenza",
                    "area", "effetto", "costo", "focus"]):
                i += 1
                continue
            if ":" in line:
                i += 1
                continue
            if len(line) > 60:
                i += 1
                continue
            # Should start with uppercase
            if line[0].isupper():
                cleaned = clean_ocr(line)
                if cleaned and len(cleaned) > 1:
                    titles.append(cleaned)
        i += 1

    return titles


def extract_feats_from_txt(path):
    """Extract feat names from talenti.txt table of contents."""
    with open(path, encoding="utf-8", errors="replace") as f:
        lines = [l.rstrip('\n') for l in f.readlines()]

    titles = []
    # The first part is a table - feat names are in the left column
    # They're short lines starting with uppercase, before "Prerequisiti" and "Benefici" columns
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        # Clean OCR artifacts
        cleaned = clean_ocr(stripped)
        # Remove trailing quote marks
        cleaned = re.sub(r"[\s'`\"]+$", "", cleaned)
        # Remove trailing " o" (OCR artifact for "Acrobatic o" -> "Acrobatico")
        if cleaned.endswith(" o") and len(cleaned) > 3:
            cleaned = cleaned[:-2] + "o"
        if cleaned.endswith(" e") and len(cleaned) > 3:
            cleaned = cleaned[:-2] + "e"
        if cleaned.endswith(" a") and len(cleaned) > 3:
            cleaned = cleaned[:-2] + "a"
        if cleaned.endswith(" i") and len(cleaned) > 3:
            cleaned = cleaned[:-2] + "i"

        if not cleaned or not cleaned[0].isupper():
            continue
        if len(cleaned) > 50:
            continue
        # Skip known non-feat lines
        if any(k in cleaned.lower() for k in ["tabella", "talenti general",
                "talenti di creazione", "talenti di metamagia", "prerequisiti",
                "benefici", "bonus di", "competenza nell", "nessun",
                "for 13", "des 13", "int 13", "sag 13", "car 13",
                "livello", "ottiene", "riduce", "dimezza", "ripete",
                "nega", "raddoppia", "la mano", "l'avversario",
                "è considerato", "chiama", "stordisce", "devia",
                "afferra", "utilizza"]):
            continue
        titles.append(cleaned)

    return titles


def build_slug_to_manual_name(titles):
    """Build a normalized lookup from manual titles."""
    result = {}
    for t in titles:
        # Create a simple slug from the title
        slug = t.lower()
        slug = re.sub(r"[''`]", "", slug)
        slug = re.sub(r"[^a-zàèéìòù\s]", "", slug)
        slug = slug.strip()
        result[slug] = t
    return result


def similarity(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def main():
    spells_overlay_path = ROOT / "data" / "i18n" / "it" / "spells.json"
    feats_overlay_path = ROOT / "data" / "i18n" / "it" / "feats.json"
    spells_txt_path = ROOT / "sources" / "testo-manuale" / "INCANTESIMI.txt"
    feats_txt_path = ROOT / "sources" / "testo-manuale" / "talenti.txt"

    with open(spells_overlay_path, encoding="utf-8") as f:
        spells_overlay = json.load(f)
    with open(feats_overlay_path, encoding="utf-8") as f:
        feats_overlay = json.load(f)

    # ── SPELLS ──
    print("=" * 80)
    print("SPELL TITLE ANALYSIS")
    print("=" * 80)

    spell_titles_txt = extract_spells_from_txt(spells_txt_path)
    print(f"Extracted {len(spell_titles_txt)} spell titles from TXT")

    # Build overlay lookup
    overlay_by_slug = {e["slug"]: e.get("name", "") for e in spells_overlay}

    # For each overlay entry, find best match in TXT titles
    txt_norms = {t.lower(): t for t in spell_titles_txt}

    exact = 0
    close_match = 0
    no_match = 0
    mismatches = []

    for slug, overlay_name in sorted(overlay_by_slug.items()):
        on = overlay_name.lower()
        if on in txt_norms:
            exact += 1
            continue

        # Try fuzzy
        best_score = 0
        best_txt = None
        for tn, original in txt_norms.items():
            s = similarity(on, tn)
            if s > best_score:
                best_score = s
                best_txt = original

        if best_score >= 0.75:
            close_match += 1
            mismatches.append((slug, overlay_name, best_txt, best_score))
        else:
            no_match += 1

    print(f"Exact matches: {exact}")
    print(f"Close matches (potential mismatches): {close_match}")
    print(f"No match: {no_match}")

    if mismatches:
        print(f"\n{'─'*80}")
        print("SPELL NAME MISMATCHES (overlay ≠ manual):")
        print(f"{'─'*80}")
        for slug, overlay_name, txt_name, score in sorted(mismatches, key=lambda x: -x[3]):
            if overlay_name.lower().strip() != txt_name.lower().strip():
                print(f"  {slug}")
                print(f"    OVERLAY: {overlay_name}")
                print(f"    MANUAL:  {txt_name}  (similarity: {score:.2f})")
                print()

    # ── FEATS ──
    print("\n" + "=" * 80)
    print("FEAT TITLE ANALYSIS")
    print("=" * 80)

    feat_titles_txt = extract_feats_from_txt(feats_txt_path)
    print(f"Extracted {len(feat_titles_txt)} feat titles from TXT")
    print("Titles found:", feat_titles_txt)

    feat_overlay_by_slug = {e["slug"]: e.get("name", "") for e in feats_overlay}
    feat_txt_norms = {t.lower(): t for t in feat_titles_txt}

    feat_exact = 0
    feat_mismatches = []
    feat_no_match_list = []

    for slug, overlay_name in sorted(feat_overlay_by_slug.items()):
        on = overlay_name.lower()
        if on in feat_txt_norms:
            feat_exact += 1
            continue

        best_score = 0
        best_txt = None
        for tn, original in feat_txt_norms.items():
            s = similarity(on, tn)
            if s > best_score:
                best_score = s
                best_txt = original

        if best_score >= 0.7:
            if overlay_name.lower().strip() != best_txt.lower().strip():
                feat_mismatches.append((slug, overlay_name, best_txt, best_score))
        else:
            feat_no_match_list.append((slug, overlay_name))

    print(f"Exact matches: {feat_exact}")
    print(f"Mismatches: {len(feat_mismatches)}")
    print(f"No match: {len(feat_no_match_list)}")

    if feat_mismatches:
        print(f"\n{'─'*80}")
        print("FEAT NAME MISMATCHES:")
        print(f"{'─'*80}")
        for slug, overlay_name, txt_name, score in feat_mismatches:
            print(f"  {slug}")
            print(f"    OVERLAY: {overlay_name}")
            print(f"    MANUAL:  {txt_name}  (similarity: {score:.2f})")
            print()


if __name__ == "__main__":
    main()
