#!/usr/bin/env python3
"""
Advanced parser for Italian SRD skill descriptions from PDF.

Uses a hybrid approach (same as pdf_to_html.py):
  1. pdftotext (flow mode) for complete text extraction
  2. pdftotext -layout for table detection and column splitting
  3. Raw PDF stream parsing for bold/italic font detection

Produces structured overlay fields (check, action, special, etc.) with:
  - Proper <table> HTML for DC/check tables
  - <b> and <i> tags from PDF font analysis
  - Sentence-based line breaks for readability

Usage:
    python scripts/parse_srd_skills_it.py <pdf_path>           # apply changes
    python scripts/parse_srd_skills_it.py <pdf_path> --dry-run # preview only
"""

import json
import re
import subprocess
import sys
from pathlib import Path

# Reuse formatting functions from pdf_to_html.py
sys.path.insert(0, str(Path(__file__).resolve().parent))
from pdf_to_html import (
    decompress_streams,
    parse_font_map,
    extract_formatted_fragments,
    apply_bold_italic,
    detect_table_lines,
    split_table_columns,
    table_lines_to_html,
)

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
OVERLAY_PATH = DATA_DIR / "i18n" / "it" / "skills.json"
BASE_PATH = DATA_DIR / "skills.json"
HTML_SOURCE = ROOT / "sources" / "pdf-ita" / "04-abilita" / "elencoabilita.html"

# ── Skill name mappings ─────────────────────────────────────────────────────

# Mapping from Italian skill name (uppercase) to EN slug
IT_SKILL_TO_SLUG = {
    "ACROBAZIA": "tumble",
    "ADDESTRARE ANIMALI": "handle-animal",
    "ARTIGIANATO": "craft",
    "ARTISTA DELLA FUGA": "escape-artist",
    "ASCOLTARE": "listen",
    "CAMUFFARE": "disguise",
    "CAVALCARE": "ride",
    "CERCARE": "search",
    "CONCENTRAZIONE": "concentration",
    "CONOSCENZE": "knowledge",
    "DECIFRARE SCRITTURE": "decipher-script",
    "DIPLOMAZIA": "diplomacy",
    "DISATTIVARE CONGEGNI": "disable-device",
    "EQUILIBRIO": "balance",
    "FALSIFICARE": "forgery",
    "GUARIRE": "heal",
    "INTIMIDIRE": "intimidate",
    "INTRATTENERE": "perform",
    "MUOVERSI SILENZIOSAMENTE": "move-silently",
    "NASCONDERSI": "hide",
    "NUOTARE": "swim",
    "OSSERVARE": "spot",
    "PARLARE LINGUAGGI": "speak-language",
    "PERCEPIRE INTENZIONI": "sense-motive",
    "PROFESSIONE": "profession",
    "RACCOGLIERE INFORMAZIONI": "gather-information",
    "RAGGIRARE": "bluff",
    "RAPIDITÀ DI MANO": "sleight-of-hand",
    "SALTARE": "jump",
    "SAPIENZA MAGICA": "spellcraft",
    "SCALARE": "climb",
    "SCASSINARE SERRATURE": "open-lock",
    "SOPRAVVIVENZA": "survival",
    "UTILIZZARE CORDE": "use-rope",
    "UTILIZZARE OGGETTI MAGICI": "use-magic-device",
    "VALUTARE": "appraise",
}

# Mapping from Italian field names to EN base data field names
IT_FIELD_TO_EN = {
    "Prova": "check",
    "Azione": "action",
    "Ritentare": "try_again",
    "Speciale": "special",
    "Sinergia": "synergy",
    "Restrizioni": "restriction",
    "Senza addestramento": "untrained",
}

# Skill heading pattern: NOME (ABILITÀ; FLAGS) or just NOME on its own line
HEADING_RE = re.compile(
    r"^([A-ZÀÈÉÌÒÙ][A-ZÀÈÉÌÒÙ '\u0080-\u00FF]{2,})"
    r"(?:\s*\(([^)]+)\))?$"
)

# Field markers within skill text
FIELD_MARKERS = [
    "Prova:",
    "Azione:",
    "Ritentare:",
    "Speciale:",
    "Sinergia:",
    "Restrizioni:",
    "Senza addestramento:",
]

# Patterns that indicate the start of a DC table sidebar
# These are detected and stripped from flow-mode text, then re-extracted
# from layout mode as proper HTML tables
TABLE_START_PATTERNS = [
    r"CD di \w+\s*Esempio",
    r"CD\s+Esempio di",
    r"Atteggiamento\s+iniziale",
    r"INFLUENZARE L'ATTEGGIAMENTO",
    r"Modificatore alla CD di",
    r"CD\s+Compito",
    r"\d+\s+Una pendenza",
]


# ── PDF text extraction ─────────────────────────────────────────────────────

def extract_text_from_pdf(pdf_path, layout=False):
    """Extract text from PDF using pdftotext.

    Args:
        pdf_path: Path to PDF file
        layout: If True, use -layout mode (preserves spatial layout for tables)
    """
    cmd = ["pdftotext"]
    if layout:
        cmd.append("-layout")
    cmd.extend([str(pdf_path), "-"])

    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        print(f"Error running pdftotext: {result.stderr}")
        sys.exit(1)
    for enc in ["utf-8", "latin-1", "cp1252"]:
        try:
            text = result.stdout.decode(enc)
            if any(c in text for c in "àèéìòùÀÈÉÌÒÙ"):
                return text
        except Exception:
            continue
    return result.stdout.decode("latin-1")


def extract_formatting_from_pdf(pdf_path):
    """Extract bold and italic fragment sets from PDF stream analysis."""
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    font_map = parse_font_map(pdf_bytes)
    streams = decompress_streams(pdf_bytes)
    bold_set, italic_set = extract_formatted_fragments(streams, font_map)
    return bold_set, italic_set


# ── Table extraction from layout mode ───────────────────────────────────────

def extract_tables_by_skill(layout_text, skill_boundaries):
    """Extract HTML tables from layout-mode text for each skill.

    Uses detect_table_lines from pdf_to_html.py to find table regions,
    then associates them with the nearest skill heading.

    Returns: dict slug → list of table HTML strings
    """
    lines = layout_text.split("\n")
    table_ranges = detect_table_lines(lines)

    # Build a mapping of line number → skill slug
    skill_line_map = []
    for slug, (start_line, end_line) in skill_boundaries.items():
        skill_line_map.append((start_line, end_line, slug))
    skill_line_map.sort()

    # Associate each table with a skill
    skill_tables = {}
    for table_start, table_end in table_ranges:
        # Find which skill owns this table range
        owner_slug = None
        for s_start, s_end, slug in skill_line_map:
            if s_start <= table_start < s_end:
                owner_slug = slug
                break

        if not owner_slug:
            # Try nearest skill before this table
            for s_start, s_end, slug in reversed(skill_line_map):
                if s_start <= table_start:
                    owner_slug = slug
                    break

        if owner_slug:
            table_html = table_lines_to_html(
                lines[table_start:table_end], set(), set()
            )
            if table_html:
                skill_tables.setdefault(owner_slug, []).append(table_html)

    return skill_tables


def find_skill_boundaries_layout(layout_text):
    """Find line ranges for each skill in layout-mode text.

    Returns: dict slug → (start_line, end_line)
    """
    lines = layout_text.split("\n")
    boundaries = {}
    skill_starts = []

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue

        # Check for skill heading (ALL-CAPS name)
        name_part = stripped.split("(")[0].strip().upper()
        # Handle multi-word names that might wrap
        for name, slug in IT_SKILL_TO_SLUG.items():
            if name_part == name or stripped.upper().startswith(name + " ("):
                skill_starts.append((i, slug))
                break

    # Build boundaries
    for idx, (start, slug) in enumerate(skill_starts):
        if idx + 1 < len(skill_starts):
            end = skill_starts[idx + 1][0]
        else:
            end = len(lines)
        boundaries[slug] = (start, end)

    return boundaries


# ── Flow-mode text parsing ──────────────────────────────────────────────────

def parse_skills_from_text(text):
    """Parse skill entries from raw PDF text (flow mode).

    Returns dict: slug → {name_it, ability_info, fields}
    """
    lines = text.split("\n")
    skills = {}

    skill_starts = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue

        m = HEADING_RE.match(line)
        if m:
            potential_name = m.group(1).strip()
            ability_info = m.group(2) or ""

            if potential_name in IT_SKILL_TO_SLUG:
                if not ability_info and i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if next_line.startswith("(") and next_line.endswith(")"):
                        ability_info = next_line[1:-1]
                        skill_starts.append(
                            (i, potential_name, ability_info, i + 2)
                        )
                        i += 2
                        continue
                skill_starts.append(
                    (i, potential_name, ability_info, i + 1)
                )
        i += 1

    for idx, (start_line, name, ability_info, content_start) in enumerate(
        skill_starts
    ):
        if idx + 1 < len(skill_starts):
            end_line = skill_starts[idx + 1][0]
        else:
            end_line = len(lines)

        content_lines = lines[content_start:end_line]
        content = " ".join(
            line.strip()
            for line in content_lines
            if line.strip()
            and not line.strip().startswith("This material is Open Game")
        )
        content = re.sub(r"\s+", " ", content).strip()

        slug = IT_SKILL_TO_SLUG.get(name)
        if not slug:
            continue

        fields = parse_skill_fields(content)

        skills[slug] = {
            "name_it": name.title(),
            "ability_info": ability_info.strip(),
            "fields": fields,
        }

    return skills


def parse_skill_fields(content):
    """Parse field sections from skill content text."""
    fields = {}

    marker_positions = []
    for marker in FIELD_MARKERS:
        pos = 0
        while True:
            idx = content.find(marker, pos)
            if idx == -1:
                break
            if idx == 0 or not content[idx - 1].isalpha():
                marker_positions.append((idx, marker))
            pos = idx + len(marker)

    marker_positions.sort(key=lambda x: x[0])

    if marker_positions:
        preamble = content[: marker_positions[0][0]].strip()
        if preamble:
            fields["preamble"] = preamble
    else:
        fields["preamble"] = content.strip()

    for i, (pos, marker) in enumerate(marker_positions):
        field_name = marker.rstrip(":")
        start = pos + len(marker)
        if i + 1 < len(marker_positions):
            end = marker_positions[i + 1][0]
        else:
            end = len(content)

        value = content[start:end].strip()
        if value:
            value = strip_table_data(value)
            fields[field_name] = value

    return fields


def strip_table_data(text):
    """Remove DC table data that pdftotext appends from PDF sidebars.

    The tables are extracted separately from layout mode with proper formatting.
    Finds the EARLIEST matching pattern to truncate at.
    """
    earliest_pos = len(text)
    for pattern in TABLE_START_PATTERNS:
        m = re.search(pattern, text)
        if m and m.start() < earliest_pos:
            earliest_pos = m.start()

    if earliest_pos < len(text):
        truncated = text[:earliest_pos].strip()
        if truncated:
            return truncated
    return text


# ── HTML formatting ─────────────────────────────────────────────────────────

def clean_bold_artifacts(html):
    """Fix common bold formatting artifacts from PDF extraction.

    The PDF has 'di', 'CD', 'e' etc. as separate bold fragments that
    get incorrectly matched against the flow-mode text. This post-processing
    removes or fixes these false positives.
    """
    # Remove bold from common short Italian prepositions/articles
    for word in ["di", "del", "dei", "della", "delle", "e", "il", "la",
                 "le", "lo", "gli", "in", "un", "una", "al", "per",
                 "con", "da", "che", "non", "si", "se", "su", "o"]:
        # Standalone bold word: <b>di</b>
        html = re.sub(
            rf"<b>{re.escape(word)}</b>",
            word,
            html,
        )
        # Merged bold: <b>diScalare</b> → di <b>Scalare</b>
        html = re.sub(
            rf"<b>{re.escape(word)}([A-ZÀÈÉÌÒÙ])",
            rf"{word} <b>\1",
            html,
        )

    # Remove bold from standalone 'CD' (it's an abbreviation, not emphasis)
    html = re.sub(r"<b>CD</b>", "CD", html)

    # Merge adjacent bold tags that got split: </b> <b> → space
    html = re.sub(r"</b>\s*<b>", " ", html)

    # Remove empty bold/italic tags
    html = re.sub(r"<b>\s*</b>", "", html)
    html = re.sub(r"<i>\s*</i>", "", html)

    return html


def format_field_html(text, bold_set, italic_set):
    """Format a field's text as HTML with bold/italic and line breaks.

    Uses the bold/italic fragment sets from PDF stream analysis,
    then cleans up common artifacts.
    """
    if not text:
        return ""

    # Apply bold/italic from PDF formatting analysis
    html = apply_bold_italic(text, bold_set, italic_set)

    # Clean up bold artifacts
    html = clean_bold_artifacts(html)

    # Add line breaks between sentences
    html = re.sub(r"(\.) (?=(?:<[bi]>)*[A-ZÀÈÉÌÒÙ])", r"\1<br>", html)

    return f"<p>{html}</p>"


def break_long_html(html):
    """Add line breaks to long HTML paragraphs for readability."""
    # Break after periods followed by uppercase (new sentences)
    html = re.sub(
        r"(\.) (?=(?:<[bi]>)*[A-ZÀÈÉÌÒÙ])", r"\1<br>\n", html
    )
    return html


# ── Main logic ──────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print(
            "Usage: python scripts/parse_srd_skills_it.py <pdf_path> [--dry-run]"
        )
        sys.exit(1)

    pdf_path = Path(sys.argv[1])
    dry_run = "--dry-run" in sys.argv

    if not pdf_path.exists():
        print(f"Error: PDF not found: {pdf_path}")
        sys.exit(1)

    if dry_run:
        print("=== DRY RUN MODE (no files will be modified) ===\n")

    # ── Step 1: Extract text (flow mode) ──
    print(f"Extracting text from {pdf_path}...")
    flow_text = extract_text_from_pdf(pdf_path, layout=False)
    print(f"  Flow mode: {len(flow_text)} chars")

    # ── Step 2: Extract text (layout mode, for tables) ──
    layout_text = extract_text_from_pdf(pdf_path, layout=True)
    print(f"  Layout mode: {len(layout_text)} chars")

    # ── Step 3: Extract bold/italic from PDF streams ──
    print("Analyzing PDF streams for bold/italic...")
    bold_set, italic_set = extract_formatting_from_pdf(pdf_path)
    print(f"  Bold fragments: {len(bold_set)}")
    print(f"  Italic fragments: {len(italic_set)}")

    # ── Step 4: Extract tables from layout mode ──
    print("Detecting tables in layout mode...")
    layout_boundaries = find_skill_boundaries_layout(layout_text)
    skill_tables = extract_tables_by_skill(layout_text, layout_boundaries)
    total_tables = sum(len(v) for v in skill_tables.values())
    print(f"  Found {total_tables} tables across {len(skill_tables)} skills")
    for slug, tables in sorted(skill_tables.items()):
        print(f"    {slug}: {len(tables)} table(s)")
    print()

    # ── Step 5: Parse skill fields from flow text ──
    parsed = parse_skills_from_text(flow_text)
    print(f"Parsed {len(parsed)} skills from PDF text\n")

    # ── Step 6: Load base and overlay ──
    with open(BASE_PATH, encoding="utf-8") as f:
        base = json.load(f)
    base_map = {}
    for e in base:
        slug = e["slug"]
        if slug not in base_map or e.get("category") == "skill":
            base_map[slug] = e

    if OVERLAY_PATH.exists():
        with open(OVERLAY_PATH, encoding="utf-8") as f:
            overlay = json.load(f)
    else:
        overlay = []
    overlay_map = {e["slug"]: e for e in overlay}

    # ── Step 7: Update overlay ──
    updated = 0

    for slug, skill_data in sorted(parsed.items()):
        if slug not in base_map:
            print(f"  Warning: {slug} not in base, skipping")
            continue

        base_entry = base_map[slug]
        fields = skill_data["fields"]
        tables = skill_tables.get(slug, [])

        if slug not in overlay_map:
            print(f"  Warning: {slug} not in overlay, skipping")
            continue

        entry = overlay_map[slug]
        changes = []

        # Write individual fields with bold/italic formatting
        for it_field, en_field in IT_FIELD_TO_EN.items():
            it_text = fields.get(it_field, "")
            if not it_text:
                continue

            if not base_entry.get(en_field):
                continue

            # Build HTML with formatting
            field_html = format_field_html(it_text, bold_set, italic_set)

            # Append tables to the 'check' field (where DC tables belong)
            if en_field == "check" and tables:
                field_html += "\n" + "\n".join(tables)

            if not dry_run:
                entry[en_field] = field_html
            changes.append(f"+{en_field}")

        # Set desc_html to empty to suppress English fallback
        if changes:
            if not dry_run:
                entry["desc_html"] = ""
            changes.append("desc_html='' (suppress EN)")

        # Update translation_source to 'pdf' for all fields we touched
        if changes:
            if not dry_run:
                entry["translation_source"] = "pdf"
                entry["reviewed"] = False

            updated += 1
            print(f"  Updated {slug}: {', '.join(changes)}")

    # Summary
    print(f"\nSummary:")
    print(f"  Skills parsed: {len(parsed)}")
    print(f"  Tables found:  {total_tables}")
    print(f"  Updated:       {updated} overlay entries")

    # Field coverage
    field_counts = {en: 0 for en in IT_FIELD_TO_EN.values()}
    table_count = 0
    for entry in overlay:
        for en_field in IT_FIELD_TO_EN.values():
            if entry.get(en_field):
                field_counts[en_field] += 1
        if any("<table" in (entry.get(f) or "") for f in IT_FIELD_TO_EN.values()):
            table_count += 1
    print(f"\n  Field coverage:")
    for field, count in sorted(field_counts.items()):
        print(f"    {field}: {count}")
    print(f"  Skills with tables: {table_count}")

    if not dry_run and updated > 0:
        overlay.sort(key=lambda e: e.get("slug", ""))
        with open(OVERLAY_PATH, "w", encoding="utf-8") as f:
            json.dump(overlay, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"\nWritten {len(overlay)} entries to {OVERLAY_PATH}")
    elif dry_run:
        print("\nDry run complete. No files modified.")
    else:
        print("\nNo changes needed.")


if __name__ == "__main__":
    main()
