#!/usr/bin/env python3
"""
Convert the Italian D&D 3.5 PHB text (OCR from PDF) into:
  1. Readable HTML files organized by chapter
  2. Structured JSON overlays for the Crystal Ball i18n system

Usage:
    python scripts/convert_manual.py html       # Generate HTML by chapter
    python scripts/convert_manual.py spells     # Extract spells → update IT overlay
    python scripts/convert_manual.py feats      # Extract feats → update IT overlay
    python scripts/convert_manual.py all        # Everything
"""

import json
import os
import re
import sys
import unicodedata
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TXT_FILE = REPO_ROOT / "testo manuale" / "manuale base completo.txt"
HTML_DIR = REPO_ROOT / "testo manuale" / "html"
DATA_DIR = REPO_ROOT / "data"
I18N_DIR = DATA_DIR / "i18n" / "it"

# ── Italian school names (used to detect spell entries) ──────────────────────
SCHOOLS_IT = {
    "Abiurazione", "Ammaliamento", "Divinazione", "Evocazione",
    "Illusione", "Invocazione", "Necromanzia", "Trasmutazione", "Universale",
}

# Subschools and descriptors that may appear in parentheses/brackets after school
SUBSCHOOLS_IT = {
    "Richiamo", "Creazione", "Guarigione", "Convocazione", "Teletrasporto",
    "Charme", "Compulsione", "Finzione", "Mascheramento", "Trama",
    "Fantasma", "Ombra", "Scrutamento", "Allucinazione",
}

# Spell metadata field labels
SPELL_FIELDS = [
    "Livello", "Componenti", "Tempo di lancio", "Raggio di azione",
    "Raggio d'azione", "Bersaglio", "Bersagli", "Area", "Effetto",
    "Durata", "Tiro salvezza", "Resistenza agli incantesimi",
]

# Feat type tags
FEAT_TYPES = {"GENERALE", "CREAZIONE OGGETTO", "METAMAGIA"}

# ── OCR correction dictionary ────────────────────────────────────────────────
# Pattern → replacement for common OCR errors
OCR_CORRECTIONS = {
    # L' misread as E/L without apostrophe
    r"\bEincantatore\b": "L'incantatore",
    r"\bLincantatore\b": "L'incantatore",
    r"\bEincantesimo\b": "L'incantesimo",
    r"\bLincantesimo\b": "L'incantesimo",
    r"\bEoggetto\b": "L'oggetto",
    r"\bLoggetto\b": "L'oggetto",
    r"\bEeffetto\b": "L'effetto",
    r"\bLeffetto\b": "L'effetto",
    r"\bEattacco\b": "L'attacco",
    r"\bLattacco\b": "L'attacco",
    r"\bEavversario\b": "L'avversario",
    r"\bEabilità\b": "L'abilità",
    r"\bEarea\b": "L'area",
    r"\bEarma\b": "L'arma",
    r"\bEenergia\b": "L'energia",
    r"\bEallineamento\b": "L'allineamento",
    r"\bEuso\b": "L'uso",
    # 11 at start of sentence → Il
    r"(?<![0-9])11 personaggio\b": "Il personaggio",
    r"(?<![0-9])11 DM\b": "Il DM",
    r"(?<![0-9])11 bersaglio\b": "Il bersaglio",
    r"(?<![0-9])11 soggetto\b": "Il soggetto",
    r"(?<![0-9])11 camminatore\b": "Il camminatore",
    r"(?<![0-9])11 numero\b": "Il numero",
    r"(?<![0-9])11 tiro\b": "Il tiro",
    r"(?<![0-9])11 danno\b": "Il danno",
    r"(?<![0-9])11 bonus\b": "Il bonus",
    r"(?<![0-9])11 raggio\b": "Il raggio",
    r"(?<![0-9])11 livello\b": "Il livello",
    # i° → 1° (common OCR error)
    r"\bi°\b": "1°",
    # Common accent errors
    r"\bpud\b": "può",
    r"\bperchd\b": "perché",
    r"\bpoichd\b": "poiché",
    r"\bcapacitd\b": "capacità",
    r"\bmetd\b": "metà",
    r"\bgid\b": "già",
    r"\bciod\b": "cioè",
    r"\bperd\b": "però",
    r"\bpiid\b": "più",
    # p f → pf (punti ferita)
    r"\bp f\b": "pf",
}

# Compiled regex patterns for OCR corrections
OCR_PATTERNS = [(re.compile(pat, re.IGNORECASE if pat.startswith(r"(?<!")
                             else 0), repl)
                 for pat, repl in OCR_CORRECTIONS.items()]
# Recompile properly
OCR_PATTERNS = []
for pat, repl in OCR_CORRECTIONS.items():
    OCR_PATTERNS.append((re.compile(pat), repl))

# ── Chapter definitions ──────────────────────────────────────────────────────
# The TXT has no clear "Capitolo X" headers in the body (only in the TOC).
# We use content-based markers to detect chapter boundaries.
# Each chapter has a "marker" regex + a search range (min_line, max_line).
CHAPTERS = [
    {"id": "introduzione", "title": "Introduzione",
     "marker": r"^Introduzione$", "search": (380, 450),
     "file": "introduzione.html"},
    {"id": "cap01", "title": "Capitolo 1: Caratteristiche",
     "marker": r"(?i)DETERMINARE I PUNTEGGI DELL", "search": (600, 700),
     "file": "cap01-caratteristiche.html"},
    {"id": "cap02", "title": "Capitolo 2: Razze",
     "marker": r"(?i)SCEGLIERE UNA RA", "search": (1150, 1250),
     "file": "cap02-razze.html"},
    {"id": "cap03", "title": "Capitolo 3: Classi",
     "marker": r"(?i)^.{0,5}classi?\s*$|LE CLASSI$|I \.F\. CI \.ASS", "search": (2300, 2400),
     "file": "cap03-classi.html"},
    {"id": "cap04", "title": "Capitolo 4: Abilità",
     "marker": r"(?i)ACQUISIRE ABILIT.* AL 1", "search": (7400, 7600),
     "file": "cap04-abilita.html"},
    {"id": "cap05", "title": "Capitolo 5: Talenti",
     "marker": r"(?i)ACC.{0,4}ISIRE TALENTI", "search": (10750, 10950),
     "file": "cap05-talenti.html"},
    {"id": "cap06", "title": "Capitolo 6: Descrizione",
     "marker": r"(?i)ASPETTO.*PERSONALIT", "search": (13500, 13700),
     "file": "cap06-descrizione.html"},
    {"id": "cap07", "title": "Capitolo 7: Equipaggiamento",
     "marker": r"(?i)TABELLA 7-1.*DENARO|DENARO INIZIALE CASUAL",
     "search": (13750, 13900),
     "file": "cap07-equipaggiamento.html"},
    {"id": "cap08", "title": "Capitolo 8: Combattimento",
     "marker": r"(?i)LA GRIGLIA DI BATTAGLIA",
     "search": (16350, 16500),
     "file": "cap08-combattimento.html"},
    {"id": "cap09", "title": "Capitolo 9: All'avventura",
     "marker": r"(?i)MISCELLANE|MISCELLANEOi|ADVENTURING",
     "search": (19300, 19500),
     "file": "cap09-avventura.html"},
    {"id": "cap10", "title": "Capitolo 10: Magia",
     "marker": r"(?i)ANCIARF? INCANTESIMI|LANCIARE INCANTESIMI",
     "search": (20350, 20500),
     "file": "cap10-magia.html"},
    {"id": "cap11", "title": "Capitolo 11: Incantesimi",
     "marker": r"(?i)incantesimi.*seguono.*ordine alfabetico|^INCANTESIM\s*I$",
     "search": (24200, 24350),
     "file": "cap11-incantesimi.html"},
    {"id": "appendice", "title": "Appendice",
     "marker": r"(?i)Appendice.*Linee guida",
     "search": (42800, 43000),
     "file": "appendice.html"},
]

# ── Helpers ──────────────────────────────────────────────────────────────────

def load_lines():
    """Load the TXT file and return list of lines."""
    with open(TXT_FILE, "r", encoding="utf-8") as f:
        return f.readlines()


def clean_line(line):
    """Clean a single line of OCR artifacts."""
    # Strip trailing whitespace and newline
    line = line.rstrip()

    # Remove leading OCR junk: isolated punctuation/symbols at start
    line = re.sub(r"^[.\s,;:!_+\-~]+(?=\s*[A-ZÀ-Úa-zà-ú])", "", line)

    # Remove tab characters, replace with space
    line = line.replace("\t", " ")

    # Apply OCR corrections
    for pattern, replacement in OCR_PATTERNS:
        line = pattern.sub(replacement, line)

    # Fix spaced numbers in common patterns like "1 .000" → "1.000"
    line = re.sub(r"(\d)\s+\.\s*(\d)", r"\1.\2", line)

    # Collapse multiple spaces
    line = re.sub(r"  +", " ", line)

    return line.strip()


def is_junk_line(line):
    """Return True if line is OCR junk (single char, noise, figure refs, etc.)."""
    stripped = line.strip()
    if not stripped:
        return False  # blank lines are separators, not junk
    # Single character lines
    if len(stripped) == 1:
        return True
    # Lines that are only punctuation/symbols (no alphanumeric content)
    if re.match(r"^[^A-Za-zÀ-Úà-ú0-9]+$", stripped):
        return True
    # Very short lines (2-3 chars) with no real words
    if len(stripped) <= 3 and not re.search(r"[A-Za-zÀ-Úà-ú]{2,}", stripped):
        return True
    # Figure references (FIG. X, fig. X)
    if re.match(r"^FIG\.?\s*[A-Z]?\.?'?$", stripped, re.IGNORECASE):
        return True
    # OCR noise patterns: just symbols and isolated chars
    if re.match(r"^[\s\W\d]{1,5}$", stripped):
        return True
    # Tab-only lines or tab+junk
    if re.match(r"^\t+\s*$", stripped):
        return True
    return False


def merge_paragraphs(lines):
    """
    Merge fragmented lines into proper paragraphs.
    Returns list of paragraph strings.
    """
    paragraphs = []
    current = []

    for line in lines:
        cleaned = clean_line(line)

        # Junk lines and blank lines are paragraph breaks
        if is_junk_line(line) or not cleaned:
            if current:
                paragraphs.append(" ".join(current))
                current = []
            continue

        # If this line looks like a heading, break before it
        if is_heading(cleaned) and current:
            paragraphs.append(" ".join(current))
            current = []

        # Handle hyphenated line breaks: word- at end of line
        if current and current[-1].endswith("-"):
            # Remove the trailing hyphen and join with next word
            prev = current[-1][:-1]
            # Heuristic: if next line starts lowercase, it's a broken word
            if cleaned and cleaned[0].islower():
                current[-1] = prev + cleaned
                continue

        current.append(cleaned)

    if current:
        paragraphs.append(" ".join(current))

    return paragraphs


def is_heading(text):
    """Detect if a paragraph looks like a section heading."""
    # ALL CAPS text (at least 3 chars, mostly uppercase)
    if len(text) > 2 and len(text) < 120:
        alpha_chars = [c for c in text if c.isalpha()]
        if alpha_chars and sum(1 for c in alpha_chars if c.isupper()) > len(alpha_chars) * 0.7:
            return True
    return False


def detect_chapter_starts(lines):
    """
    Find line indices where each chapter begins.
    Uses content-based markers within search ranges.
    Returns dict: chapter_id → line_index
    """
    chapter_starts = {}

    for ch in CHAPTERS:
        min_line, max_line = ch["search"]
        max_line = min(max_line, len(lines))
        pattern = re.compile(ch["marker"])

        for i in range(min_line, max_line):
            stripped = lines[i].strip()
            if pattern.search(stripped):
                chapter_starts[ch["id"]] = i
                break
        else:
            # Fallback: use the start of the search range
            print(f"  WARNING: Could not find marker for {ch['title']}, "
                  f"using line {min_line}")
            chapter_starts[ch["id"]] = min_line

    return chapter_starts


# ── Phase 1: HTML Generation ────────────────────────────────────────────────

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — D&D 3.5 Manuale del Giocatore</title>
<style>
body {{ font-family: Georgia, 'Times New Roman', serif; max-width: 800px;
       margin: 2rem auto; padding: 0 1rem; line-height: 1.6; color: #222; }}
h1 {{ color: #8b0000; border-bottom: 2px solid #8b0000; padding-bottom: 0.3em; }}
h2 {{ color: #333; margin-top: 2em; }}
h3 {{ color: #555; }}
p {{ text-align: justify; margin: 0.8em 0; }}
ul, ol {{ margin: 0.5em 0; padding-left: 2em; }}
.spell-entry {{ border-left: 3px solid #8b0000; padding-left: 1em; margin: 1.5em 0; }}
.spell-name {{ font-size: 1.2em; font-weight: bold; color: #8b0000; }}
.spell-meta {{ color: #555; font-style: italic; }}
.spell-field {{ margin: 0.2em 0; }}
.spell-field strong {{ color: #333; }}
.feat-entry {{ border-left: 3px solid #2e5090; padding-left: 1em; margin: 1.5em 0; }}
.feat-name {{ font-size: 1.1em; font-weight: bold; color: #2e5090; }}
nav {{ background: #f5f5f5; padding: 1em; border-radius: 5px; margin-bottom: 2em; }}
nav a {{ margin-right: 1em; text-decoration: none; color: #8b0000; }}
nav a:hover {{ text-decoration: underline; }}
</style>
</head>
<body>
<nav>
<a href="index.html">← Indice</a>
{nav_links}
</nav>
<h1>{title}</h1>
{content}
</body>
</html>
"""

INDEX_TEMPLATE = """<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>D&D 3.5 Manuale del Giocatore — Indice</title>
<style>
body {{ font-family: Georgia, 'Times New Roman', serif; max-width: 800px;
       margin: 2rem auto; padding: 0 1rem; line-height: 1.6; color: #222; }}
h1 {{ color: #8b0000; border-bottom: 2px solid #8b0000; padding-bottom: 0.3em; }}
ul {{ list-style: none; padding: 0; }}
li {{ margin: 0.8em 0; }}
a {{ color: #8b0000; text-decoration: none; font-size: 1.1em; }}
a:hover {{ text-decoration: underline; }}
</style>
</head>
<body>
<h1>D&D 3.5 — Manuale del Giocatore</h1>
<h2>Indice dei Capitoli</h2>
<ul>
{links}
</ul>
</body>
</html>
"""


def paragraphs_to_html(paragraphs):
    """Convert paragraph list to HTML string with heading detection."""
    html_parts = []
    for para in paragraphs:
        # Escape HTML entities
        safe = para.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        if is_heading(para):
            level = "h2" if len(para) < 40 else "h3"
            html_parts.append(f"<{level}>{safe}</{level}>")
        elif para.startswith("•") or para.startswith("▪"):
            # Bullet point
            items = [p.strip().lstrip("•▪ ") for p in para.split("•") if p.strip()]
            if not items:
                items = [p.strip().lstrip("•▪ ") for p in para.split("▪") if p.strip()]
            if items:
                html_parts.append("<ul>")
                for item in items:
                    item_safe = item.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                    html_parts.append(f"  <li>{item_safe}</li>")
                html_parts.append("</ul>")
        else:
            html_parts.append(f"<p>{safe}</p>")

    return "\n".join(html_parts)


def generate_nav_links(current_id):
    """Generate prev/next navigation links."""
    ids = [ch["id"] for ch in CHAPTERS]
    links = []
    try:
        idx = ids.index(current_id)
        if idx > 0:
            prev_ch = CHAPTERS[idx - 1]
            links.append(f'<a href="{prev_ch["file"]}">← {prev_ch["title"]}</a>')
        if idx < len(ids) - 1:
            next_ch = CHAPTERS[idx + 1]
            links.append(f'<a href="{next_ch["file"]}">{next_ch["title"]} →</a>')
    except ValueError:
        pass
    return " | ".join(links)


def generate_html():
    """Phase 1: Generate HTML files from the TXT manual."""
    print("Loading TXT file...")
    raw_lines = load_lines()
    print(f"  {len(raw_lines)} lines loaded")

    print("Detecting chapter boundaries...")
    chapter_starts = detect_chapter_starts(raw_lines)
    print(f"  Found {len(chapter_starts)} chapters:")
    for cid, start in sorted(chapter_starts.items(), key=lambda x: x[1]):
        print(f"    {cid}: line {start}")

    # Create output directory
    HTML_DIR.mkdir(parents=True, exist_ok=True)

    # Sort chapters by start line
    sorted_chapters = []
    for ch in CHAPTERS:
        if ch["id"] in chapter_starts:
            sorted_chapters.append((ch, chapter_starts[ch["id"]]))
    sorted_chapters.sort(key=lambda x: x[1])

    # Generate each chapter HTML
    for i, (ch, start_line) in enumerate(sorted_chapters):
        # End line is start of next chapter or end of file
        if i + 1 < len(sorted_chapters):
            end_line = sorted_chapters[i + 1][1]
        else:
            end_line = len(raw_lines)

        print(f"Processing {ch['title']} (lines {start_line}-{end_line})...")
        chapter_lines = raw_lines[start_line:end_line]
        paragraphs = merge_paragraphs(chapter_lines)
        content_html = paragraphs_to_html(paragraphs)
        nav = generate_nav_links(ch["id"])

        page_html = HTML_TEMPLATE.format(
            title=ch["title"],
            nav_links=nav,
            content=content_html,
        )

        out_path = HTML_DIR / ch["file"]
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(page_html)
        print(f"  → {out_path.relative_to(REPO_ROOT)} ({len(paragraphs)} paragraphs)")

    # Generate index page
    links_html = "\n".join(
        f'  <li><a href="{ch["file"]}">{ch["title"]}</a></li>'
        for ch in CHAPTERS if ch["id"] in chapter_starts
    )
    index_html = INDEX_TEMPLATE.format(links=links_html)
    index_path = HTML_DIR / "index.html"
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(index_html)
    print(f"  → {index_path.relative_to(REPO_ROOT)}")
    print(f"\nPhase 1 complete: {len(sorted_chapters)} chapter files + index generated in {HTML_DIR.relative_to(REPO_ROOT)}/")


# ── Phase 2A: Spell extraction ──────────────────────────────────────────────

def load_name_map():
    """Load and invert NAME_MAP from translate_spells.py (IT name → EN name)."""
    # Import the map directly
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    from translate_spells import NAME_MAP
    # Invert: Italian name → English name
    it_to_en = {}
    for en, it in NAME_MAP.items():
        it_to_en[it.lower()] = en
        # Also store with normalized accents
        normalized = unicodedata.normalize("NFC", it.lower())
        it_to_en[normalized] = en
    return NAME_MAP, it_to_en


def find_spell_section(lines):
    """Find start and end of the spell descriptions section (Chapter 11 body)."""
    chapter_starts = detect_chapter_starts(lines)
    spell_start = chapter_starts.get("cap11")
    if not spell_start:
        print("ERROR: Could not find Chapter 11 (Incantesimi)")
        return None, None

    # Find the end: Appendice or end of file
    spell_end = chapter_starts.get("appendice", len(lines))
    return spell_start, spell_end


def is_school_line(text):
    """Check if a line starts with a known Italian magic school name."""
    text = text.strip()
    for school in SCHOOLS_IT:
        if text.startswith(school):
            return True
    return False


def parse_school_line_it(text):
    """Parse an Italian school line like 'Evocazione (Convocazione) [Fuoco]'."""
    text = text.strip()
    school = None
    subschool = None
    descriptor = None

    # Match: School (Subschool) [Descriptor]
    m = re.match(r"(\w+)\s*(?:\(([^)]+)\))?\s*(?:\[([^\]]+)\])?", text)
    if m:
        school = m.group(1).strip()
        subschool = m.group(2).strip() if m.group(2) else None
        descriptor = m.group(3).strip() if m.group(3) else None

    return school, subschool, descriptor


def extract_spell_field(text, field_name):
    """Extract value after 'Field:' from a line."""
    for label in [field_name + ":", field_name + " :"]:
        if label in text:
            return text.split(label, 1)[1].strip()
    return None


def parse_spells_from_text(lines, start, end):
    """
    Parse spell entries from the text between start and end line indices.
    Returns list of dicts with spell data.
    """
    spells = []
    i = start
    cleaned_lines = []

    # Pre-clean and filter junk lines
    for idx in range(start, end):
        line = lines[idx]
        if is_junk_line(line):
            cleaned_lines.append("")
        else:
            cleaned_lines.append(clean_line(line))

    # Now scan for spell entries
    # A spell entry starts with: Name line, followed by School line
    spell_entries = []  # list of (name, start_offset)

    for idx in range(len(cleaned_lines) - 1):
        line = cleaned_lines[idx]
        next_line = cleaned_lines[idx + 1] if idx + 1 < len(cleaned_lines) else ""

        if not line or not next_line:
            continue

        # Check if next line starts with a school name
        if is_school_line(next_line):
            # Current line should be the spell name
            # Validate: name should be reasonable (not too long, not a field label)
            name = line.strip()
            if (3 <= len(name) <= 80 and
                    not any(name.startswith(f) for f in SPELL_FIELDS) and
                    not name.startswith("Componente materiale")):
                spell_entries.append((name, idx))

    print(f"  Found {len(spell_entries)} potential spell entries")

    # Now parse each spell entry
    for entry_idx, (name, offset) in enumerate(spell_entries):
        # End of this entry is start of next entry or section end
        if entry_idx + 1 < len(spell_entries):
            entry_end = spell_entries[entry_idx + 1][1]
        else:
            entry_end = len(cleaned_lines)

        # Collect all lines of this entry
        entry_lines = cleaned_lines[offset:entry_end]

        spell = {"name_it": name}

        # Parse school line
        if len(entry_lines) > 1:
            school, subschool, descriptor = parse_school_line_it(entry_lines[1])
            if school:
                spell["school_it"] = school
            if subschool:
                spell["subschool_it"] = subschool
            if descriptor:
                spell["descriptor_it"] = descriptor

        # Parse metadata fields
        field_text = " ".join(entry_lines[2:])  # Join remaining lines
        for field in SPELL_FIELDS:
            val = extract_spell_field(field_text, field)
            if val:
                # Truncate at next field label (handle both "Field:" and "Field :")
                for other_field in SPELL_FIELDS:
                    if other_field != field:
                        for suffix in [":", " :"]:
                            cut_label = other_field + suffix
                            idx = val.find(cut_label)
                            if idx != -1:
                                val = val[:idx].strip()
                spell[field.lower().replace(" ", "_").replace("'", "")] = val

        # Extract description: everything after the last metadata field
        desc_lines = []
        past_metadata = False
        last_meta_idx = 1  # after school line

        for li, eline in enumerate(entry_lines[2:], start=2):
            if not eline:
                if past_metadata:
                    desc_lines.append("")
                continue

            is_meta = False
            for field in SPELL_FIELDS:
                if eline.strip().startswith(field + ":") or eline.strip().startswith(field + " :"):
                    is_meta = True
                    last_meta_idx = li
                    break

            if is_meta:
                past_metadata = False
                continue

            # Check if we're past the "Resistenza agli incantesimi" line
            if li > last_meta_idx and not is_meta:
                past_metadata = True
                desc_lines.append(eline)

        # Build description HTML from desc_lines
        desc_paragraphs = merge_paragraphs(desc_lines)
        if desc_paragraphs:
            desc_html = "\n".join(f"<p>{p}</p>" for p in desc_paragraphs if p.strip())
            spell["desc_html"] = desc_html

        spells.append(spell)

    return spells


def slugify(name):
    """Create a URL-friendly slug from a name."""
    s = name.lower().strip()
    s = unicodedata.normalize("NFKD", s)
    s = s.encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[-\s]+", "-", s)
    return s.strip("-")


def clean_ocr_target_value(val):
    """Clean OCR artifacts from target/area/effect values."""
    if not val:
        return None
    # Normalize whitespace
    val = re.sub(r"\s+", " ", val).strip()
    # Truncate at description-start patterns (text leaked past field boundary)
    for pattern in [
        r"\s+Funziona come\b",
        r"\s+Questo incantesimo\b",
        r"\s+L'incantesimo\b",
        r"\s+L incantesimo\b",
        r"\s+L'incantatore viene\b",
        r"\s+Componente materiale",
        r"\s+Focus arcano",
        r"\s+Fotto arcano",           # OCR for "Fotto" = "Foco/Focus"
        r"\bdi soggetto rimane\b",
        r"\bE cosciente e respira\b",
        r"\bche pu[oò] anche\.\s",    # continuation of Componente materiale
        r"\bCome evoca\w*\b",           # "Come evoca mostri/alleato naturale..."
        r"\binferiore dello stesso tipo\b",
        r"\brenza che è possibile\b",  # OCR for "differenza che è possibile"
    ]:
        m = re.search(pattern, val)
        if m:
            val = val[:m.start()].strip()
    # Fix broken words at end: "spiritual e" → "spirituale"
    val = re.sub(r"\s+([a-zà-ú])\s*$", r"\1", val)
    # Fix "mass a" → "massa"
    val = re.sub(r"\bmass\s+a\b", "massa", val)
    # Remove spurious OCR characters
    val = re.sub(r"[_|{}\[\]]", "", val).strip()
    # Fix double spaces
    val = re.sub(r"\s{2,}", " ", val)
    # Remove trailing punctuation artifacts
    val = re.sub(r"[\s.,:;]+$", "", val)
    if len(val) < 3:
        return None
    return val


def extract_spells():
    """Phase 2A: Extract Italian spells and update overlay JSON."""
    print("Loading TXT file...")
    raw_lines = load_lines()

    print("Loading spell name map...")
    name_map_en_to_it, name_map_it_to_en = load_name_map()

    print("Finding spell section...")
    start, end = find_spell_section(raw_lines)
    if start is None:
        return

    # The actual spell descriptions start after the spell lists
    # (lists like "Incantesimi da bardo", "Incantesimi da chierico" etc.)
    # The descriptions begin alphabetically, typically around "Abolire incantamenti" or similar
    # Let's look for the first spell entry after the lists
    print(f"  Spell section: lines {start}-{end}")

    print("Parsing spell entries...")
    spells = parse_spells_from_text(raw_lines, start, end)
    print(f"  Parsed {len(spells)} spells")

    # Load existing overlay
    overlay_path = I18N_DIR / "spells.json"
    if overlay_path.exists():
        with open(overlay_path, "r", encoding="utf-8") as f:
            existing_overlay = json.load(f)
    else:
        existing_overlay = []

    # Index existing by slug
    existing_by_slug = {entry["slug"]: entry for entry in existing_overlay}

    # Match parsed spells to English slugs
    matched = 0
    unmatched_names = []

    def clean_spell_name(name):
        """Clean OCR artifacts from spell names for matching."""
        # Fix trailing single letters from broken words (e.g., "Antipati a" → "Antipatia")
        name = re.sub(r"\s+([a-zà-ú])\s*$", r"\1", name)
        # Fix "di mass a" → "di massa"
        name = re.sub(r"\bmass\s+a\b", "massa", name)
        # Fix double spaces
        name = re.sub(r"\s+", " ", name).strip()
        return name

    for spell in spells:
        name_it = clean_spell_name(spell["name_it"])
        name_lower = name_it.lower().strip()

        # Try direct match with inverted NAME_MAP
        en_name = name_map_it_to_en.get(name_lower)

        if not en_name:
            # Try fuzzy: remove accents, lowercase
            normalized = unicodedata.normalize("NFKD", name_lower)
            normalized = normalized.encode("ascii", "ignore").decode("ascii")
            for it_key, en_val in name_map_it_to_en.items():
                it_normalized = unicodedata.normalize("NFKD", it_key)
                it_normalized = it_normalized.encode("ascii", "ignore").decode("ascii")
                if normalized == it_normalized:
                    en_name = en_val
                    break

        if not en_name:
            # Try with common variations:
            # "Blocca animali" → "Bloccare Animali" (add -re suffix)
            # "Animare morti" → "Animare i Morti" (add articles)
            # Remove articles and prepositions for fuzzy match
            def simplify(s):
                s = re.sub(r"\b(i|il|lo|la|le|gli|l'|l |del|della|dei|delle|dell'|degli|di|da|in|su|con|per|tra|fra|al|alla|alle|agli|a)\b", "", s.lower())
                s = re.sub(r"[''`]", "", s)
                s = re.sub(r"\s+", " ", s).strip()
                return s

            name_simple = simplify(name_lower)
            for it_key, en_val in name_map_it_to_en.items():
                key_simple = simplify(it_key)
                if name_simple == key_simple:
                    en_name = en_val
                    break
                # Also try with verb suffix variations (blocca→bloccare, ecc.)
                for suffix_from, suffix_to in [("", "re"), ("", "e"),
                                               ("a", "are"), ("e", "ere"),
                                               ("re", ""), ("are", "a"),
                                               ("ere", "e"), ("ire", "i")]:
                    if name_simple.endswith(suffix_from):
                        trial = name_simple[:-len(suffix_from)] + suffix_to if suffix_from else name_simple + suffix_to
                        if trial == key_simple:
                            en_name = en_val
                            break
                if en_name:
                    break

        if not en_name:
            # Try substring matching: if the cleaned name starts with a known IT name
            for it_key, en_val in name_map_it_to_en.items():
                if name_lower.startswith(it_key) or it_key.startswith(name_lower):
                    if abs(len(name_lower) - len(it_key)) <= 3:
                        en_name = en_val
                        break

        if en_name:
            slug = slugify(en_name)
            matched += 1

            # Update or create overlay entry
            if slug in existing_by_slug:
                entry = existing_by_slug[slug]
            else:
                entry = {"slug": slug, "name": name_it}
                existing_by_slug[slug] = entry

            # Add desc_html if we have it and it's not already set
            if "desc_html" in spell and spell["desc_html"]:
                if not entry.get("desc_html") or len(entry.get("desc_html", "")) < 20:
                    entry["desc_html"] = spell["desc_html"]

            # Add other IT fields
            for field_key in ["school_it", "subschool_it", "descriptor_it"]:
                mapped_key = field_key.replace("_it", "")
                if field_key in spell and not entry.get(mapped_key):
                    entry[mapped_key] = spell[field_key]

            # Map Bersaglio/Area/Effetto → target_area_effect (manual is authoritative)
            for tae_key in ["bersaglio", "bersagli", "effetto", "area"]:
                if tae_key in spell and spell[tae_key]:
                    cleaned = clean_ocr_target_value(spell[tae_key])
                    if cleaned:
                        entry["target_area_effect"] = cleaned
                        break  # use first available in priority order
        else:
            unmatched_names.append(name_it)

    print(f"  Matched: {matched}/{len(spells)}")
    if unmatched_names:
        print(f"  Unmatched ({len(unmatched_names)}):")
        for name in unmatched_names[:20]:
            print(f"    - {name}")
        if len(unmatched_names) > 20:
            print(f"    ... and {len(unmatched_names) - 20} more")

    # Write updated overlay
    updated_overlay = sorted(existing_by_slug.values(), key=lambda x: x["slug"])
    with open(overlay_path, "w", encoding="utf-8") as f:
        json.dump(updated_overlay, f, ensure_ascii=False, indent=2)
    print(f"  -> Updated {overlay_path.relative_to(REPO_ROOT)} ({len(updated_overlay)} entries)")


# ── Phase 2B: Feat extraction ───────────────────────────────────────────────

def find_feat_section(lines):
    """Find the feat descriptions in Chapter 5."""
    chapter_starts = detect_chapter_starts(lines)
    feat_start = chapter_starts.get("cap05")
    feat_end = chapter_starts.get("cap06", len(lines))
    return feat_start, feat_end


def parse_feats_from_text(lines, start, end):
    """Parse feat entries from the text."""
    feats = []
    cleaned = []

    for idx in range(start, end):
        line = lines[idx]
        if is_junk_line(line):
            cleaned.append("")
        else:
            cleaned.append(clean_line(line))

    # Feat pattern: NAME [TYPE]
    # e.g., "FINTARE MIGLIORATO [GENERALE]"
    feat_pattern = re.compile(r"^([A-ZÀÈÉÌÒÙ][A-ZÀÈÉÌÒÙ\s\-']+)\s*\[([A-ZÀÈÉÌÒÙ\s]+)\]\s*$")

    feat_entries = []
    for idx, line in enumerate(cleaned):
        m = feat_pattern.match(line.strip())
        if m:
            name = m.group(1).strip().title()
            feat_type = m.group(2).strip().title()
            feat_entries.append((name, feat_type, idx))

    print(f"  Found {len(feat_entries)} feat entries")

    for entry_idx, (name, feat_type, offset) in enumerate(feat_entries):
        if entry_idx + 1 < len(feat_entries):
            entry_end = feat_entries[entry_idx + 1][2]
        else:
            entry_end = len(cleaned)

        entry_lines = cleaned[offset + 1:entry_end]
        feat = {
            "name_it": name,
            "type_it": feat_type,
        }

        # Parse fields: Prerequisiti, Prerequisito, Beneficio, Normale, Speciale
        current_field = None
        fields = {}
        desc_parts = []

        for line in entry_lines:
            if not line:
                continue

            field_found = False
            for field_name in ["Prerequisiti", "Prerequisito", "Beneficio",
                               "Normale", "Speciale"]:
                if line.strip().startswith(field_name + ":") or line.strip().startswith(field_name + " :"):
                    current_field = field_name.lower()
                    if current_field == "prerequisito":
                        current_field = "prerequisiti"
                    val = line.split(":", 1)[1].strip() if ":" in line else ""
                    fields[current_field] = val
                    field_found = True
                    break

            if not field_found and current_field:
                fields[current_field] = fields.get(current_field, "") + " " + line.strip()
            elif not field_found:
                desc_parts.append(line)

        feat.update(fields)

        # Build desc_html
        desc_paragraphs = merge_paragraphs(entry_lines)
        if desc_paragraphs:
            feat["desc_html"] = "\n".join(f"<p>{p}</p>" for p in desc_paragraphs if p.strip())

        feats.append(feat)

    return feats


def extract_feats():
    """Phase 2B: Extract Italian feats and update overlay JSON."""
    print("Loading TXT file...")
    raw_lines = load_lines()

    print("Finding feat section...")
    start, end = find_feat_section(raw_lines)
    if start is None:
        print("ERROR: Could not find Chapter 5 (Talenti)")
        return

    print(f"  Feat section: lines {start}-{end}")
    print("Parsing feat entries...")
    feats = parse_feats_from_text(raw_lines, start, end)
    print(f"  Parsed {len(feats)} feats")

    # Load existing overlay
    overlay_path = I18N_DIR / "feats.json"
    if overlay_path.exists():
        with open(overlay_path, "r", encoding="utf-8") as f:
            existing_overlay = json.load(f)
    else:
        existing_overlay = []

    existing_by_slug = {entry["slug"]: entry for entry in existing_overlay}

    # Load feats.json to get slug mapping
    feats_en_path = DATA_DIR / "feats.json"
    if feats_en_path.exists():
        with open(feats_en_path, "r", encoding="utf-8") as f:
            feats_en = json.load(f)
    else:
        feats_en = []

    # Build IT name → slug map from existing overlay
    it_name_to_slug = {}
    for entry in existing_overlay:
        if "name" in entry:
            it_name_to_slug[entry["name"].lower()] = entry["slug"]

    matched = 0
    for feat in feats:
        name_it = feat["name_it"]
        slug = it_name_to_slug.get(name_it.lower())

        if slug:
            matched += 1
            if slug in existing_by_slug:
                entry = existing_by_slug[slug]
            else:
                entry = {"slug": slug, "name": name_it}
                existing_by_slug[slug] = entry

            # Add fields
            if feat.get("desc_html") and not entry.get("desc_html"):
                entry["desc_html"] = feat["desc_html"]
            if feat.get("beneficio") and not entry.get("benefit"):
                entry["benefit"] = feat["beneficio"].strip()
            if feat.get("prerequisiti") and not entry.get("prerequisites"):
                entry["prerequisites"] = feat["prerequisiti"].strip()
            if feat.get("normale") and not entry.get("normal"):
                entry["normal"] = feat["normale"].strip()
            if feat.get("speciale") and not entry.get("special"):
                entry["special"] = feat["speciale"].strip()

    print(f"  Matched: {matched}/{len(feats)}")

    updated_overlay = sorted(existing_by_slug.values(), key=lambda x: x["slug"])
    with open(overlay_path, "w", encoding="utf-8") as f:
        json.dump(updated_overlay, f, ensure_ascii=False, indent=2)
    print(f"  -> Updated {overlay_path.relative_to(REPO_ROOT)} ({len(updated_overlay)} entries)")


# ── Phase 2C: Class extraction ──────────────────────────────────────────────

CLASS_NAMES_IT = [
    "Barbaro", "Bardo", "Chierico", "Druido", "Guerriero",
    "Ladro", "Mago", "Monaco", "Paladino", "Ranger", "Stregone",
]

CLASS_SLUG_MAP = {
    "barbaro": "barbarian", "bardo": "bard", "chierico": "cleric",
    "druido": "druid", "guerriero": "fighter", "ladro": "rogue",
    "mago": "wizard", "monaco": "monk", "paladino": "paladin",
    "ranger": "ranger", "stregone": "sorcerer",
}


def extract_classes():
    """Phase 2C: Extract Italian class descriptions and update overlay JSON."""
    print("Loading TXT file...")
    raw_lines = load_lines()

    chapter_starts = detect_chapter_starts(raw_lines)
    start = chapter_starts.get("cap03")
    end = chapter_starts.get("cap04", chapter_starts.get("cap05", len(raw_lines)))
    if start is None:
        print("ERROR: Could not find Chapter 3 (Classi)")
        return

    print(f"  Class section: lines {start}-{end}")

    # Find each class section using TABELLA 3-X pattern or class name in text
    # Classes are introduced as "Barbaro: Un ferocé combattente..."
    # and have TABELLA 3-X: CLASSNAME markers
    class_positions = []
    for i in range(start, end):
        stripped = raw_lines[i].strip()
        # Look for "ClasseName: description" pattern at class intro
        for cls_name in CLASS_NAMES_IT:
            pattern = cls_name + ":"
            if stripped.startswith(pattern) and len(stripped) > len(pattern) + 10:
                class_positions.append((cls_name, i))
                break
        # Also look for TABELLA 3-X: CLASSNAME
        if not class_positions or class_positions[-1][1] != i:
            m = re.match(r"TABELLA 3-\d+\s*:\s*(\w+)", stripped)
            if m:
                table_name = m.group(1).strip().title()
                if table_name in CLASS_NAMES_IT and (
                        not class_positions or class_positions[-1][0] != table_name):
                    class_positions.append((table_name, i))

    # Deduplicate: keep earliest occurrence of each class
    seen = {}
    unique_positions = []
    for name, pos in class_positions:
        if name not in seen:
            seen[name] = pos
            unique_positions.append((name, pos))
    class_positions = unique_positions

    print(f"  Found {len(class_positions)} class sections")

    overlay_path = I18N_DIR / "classes.json"
    if overlay_path.exists():
        with open(overlay_path, "r", encoding="utf-8") as f:
            existing_overlay = json.load(f)
    else:
        existing_overlay = []

    existing_by_slug = {entry["slug"]: entry for entry in existing_overlay}

    for idx, (cls_name, pos) in enumerate(class_positions):
        # End at next class or end of section
        if idx + 1 < len(class_positions):
            cls_end = class_positions[idx + 1][1]
        else:
            cls_end = end

        cls_lines = raw_lines[pos:cls_end]
        paragraphs = merge_paragraphs(cls_lines)
        desc_html = "\n".join(f"<p>{p}</p>" for p in paragraphs[1:] if p.strip())  # skip name

        slug = CLASS_SLUG_MAP.get(cls_name.lower())
        if slug and desc_html:
            if slug in existing_by_slug:
                entry = existing_by_slug[slug]
            else:
                entry = {"slug": slug, "name": cls_name}
                existing_by_slug[slug] = entry

            if not entry.get("desc_html") or len(entry.get("desc_html", "")) < 100:
                entry["desc_html"] = desc_html

    updated_overlay = sorted(existing_by_slug.values(), key=lambda x: x["slug"])
    with open(overlay_path, "w", encoding="utf-8") as f:
        json.dump(updated_overlay, f, ensure_ascii=False, indent=2)
    print(f"  -> Updated {overlay_path.relative_to(REPO_ROOT)} ({len(updated_overlay)} entries)")


# ── Phase 2D: Race extraction ───────────────────────────────────────────────

RACE_NAMES_IT = ["Umani", "Nani", "Elfi", "Gnomi", "Mezzelfi", "Mezzorchi", "Halflings"]
RACE_SLUG_MAP = {
    "umani": "humans", "nani": "dwarves", "elfi": "elves",
    "gnomi": "gnomes", "mezzelfi": "half-elves",
    "mezzorchi": "half-orcs", "halflings": "halflings",
}


def extract_races():
    """Phase 2D: Extract Italian race descriptions and update overlay JSON."""
    print("Loading TXT file...")
    raw_lines = load_lines()

    chapter_starts = detect_chapter_starts(raw_lines)
    start = chapter_starts.get("cap02")
    end = chapter_starts.get("cap03", len(raw_lines))
    if start is None:
        print("ERROR: Could not find Chapter 2 (Razze)")
        return

    print(f"  Race section: lines {start}-{end}")

    race_positions = []
    for i in range(start, end):
        stripped = raw_lines[i].strip()
        cleaned = clean_line(stripped)
        for race_name in RACE_NAMES_IT:
            # Look for race name as standalone heading or "NANI", "UMANI" etc.
            if (cleaned.lower() == race_name.lower() or
                    cleaned.upper() == race_name.upper()):
                race_positions.append((race_name, i))
                break
            # Also check for "Personalità" section marker unique to race descriptions
        # Look for race descriptions as "Nome razza" followed by descriptive text
        if not race_positions or race_positions[-1][1] != i:
            for race_name in RACE_NAMES_IT:
                if stripped.startswith(race_name + " ") and "+" in stripped and "-" in stripped:
                    # This is a table row, skip
                    continue
                if cleaned.upper() == race_name.upper():
                    race_positions.append((race_name, i))
                    break

    print(f"  Found {len(race_positions)} race sections")

    overlay_path = I18N_DIR / "races.json"
    if overlay_path.exists():
        with open(overlay_path, "r", encoding="utf-8") as f:
            existing_overlay = json.load(f)
    else:
        existing_overlay = []

    existing_by_slug = {entry["slug"]: entry for entry in existing_overlay}

    for idx, (race_name, pos) in enumerate(race_positions):
        if idx + 1 < len(race_positions):
            race_end = race_positions[idx + 1][1]
        else:
            race_end = end

        race_lines = raw_lines[pos:race_end]
        paragraphs = merge_paragraphs(race_lines)
        desc_html = "\n".join(f"<p>{p}</p>" for p in paragraphs[1:] if p.strip())

        slug = RACE_SLUG_MAP.get(race_name.lower())
        if slug and desc_html:
            if slug in existing_by_slug:
                entry = existing_by_slug[slug]
            else:
                entry = {"slug": slug, "name": race_name}
                existing_by_slug[slug] = entry

            if not entry.get("desc_html") or len(entry.get("desc_html", "")) < 100:
                entry["desc_html"] = desc_html

    updated_overlay = sorted(existing_by_slug.values(), key=lambda x: x["slug"])
    with open(overlay_path, "w", encoding="utf-8") as f:
        json.dump(updated_overlay, f, ensure_ascii=False, indent=2)
    print(f"  -> Updated {overlay_path.relative_to(REPO_ROOT)} ({len(updated_overlay)} entries)")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "html":
        generate_html()
    elif command == "spells":
        extract_spells()
    elif command == "feats":
        extract_feats()
    elif command == "classes":
        extract_classes()
    elif command == "races":
        extract_races()
    elif command == "all":
        generate_html()
        print("\n" + "=" * 60 + "\n")
        extract_spells()
        print("\n" + "=" * 60 + "\n")
        extract_feats()
        print("\n" + "=" * 60 + "\n")
        extract_classes()
        print("\n" + "=" * 60 + "\n")
        extract_races()
    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
