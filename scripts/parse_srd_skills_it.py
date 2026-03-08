#!/usr/bin/env python3
"""
Parse Italian skill descriptions from the PDF SRD text and update skills overlay.

Reads the raw text extracted from srd35_04_01_elencoabilita.pdf via pdftotext,
parses each skill entry into structured fields matching the EN base data schema
(check, action, try_again, special, synergy, restriction, untrained), and writes
them as individual overlay fields so the frontend renders them in the proper
sections (replacing the English text).

Also re-processes skills from the HTML conversion to fix bold formatting artifacts
and extract individual fields.

Usage:
    python scripts/parse_srd_skills_it.py <pdf_path>           # apply changes
    python scripts/parse_srd_skills_it.py <pdf_path> --dry-run # preview only
"""

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
OVERLAY_PATH = DATA_DIR / "i18n" / "it" / "skills.json"
BASE_PATH = DATA_DIR / "skills.json"
HTML_SOURCE = ROOT / "sources" / "pdf-ita" / "04-abilita" / "elencoabilita.html"

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


def extract_text_from_pdf(pdf_path):
    """Extract text from PDF using pdftotext."""
    result = subprocess.run(
        ["pdftotext", str(pdf_path), "-"],
        capture_output=True,
    )
    if result.returncode != 0:
        print(f"Error running pdftotext: {result.stderr}")
        sys.exit(1)
    # Try UTF-8 first, fall back to latin-1
    try:
        return result.stdout.decode("utf-8")
    except UnicodeDecodeError:
        return result.stdout.decode("latin-1")


def parse_skills_from_text(text):
    """Parse skill entries from raw PDF text.

    Returns dict: slug → {name_it, ability_info, fields}
    where fields maps IT field names to text content.
    """
    lines = text.split("\n")
    skills = {}

    # Find all skill heading positions
    skill_starts = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue

        # Handle headings where ability info is on the same line
        m = HEADING_RE.match(line)
        if m:
            potential_name = m.group(1).strip()
            ability_info = m.group(2) or ""

            # Check if it's a known skill
            if potential_name in IT_SKILL_TO_SLUG:
                # If ability_info is empty, check next line
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

    # Extract content for each skill
    for idx, (start_line, name, ability_info, content_start) in enumerate(
        skill_starts
    ):
        # Content goes until the next skill heading or end of file
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

        # Clean up multiple spaces
        content = re.sub(r"\s+", " ", content).strip()

        slug = IT_SKILL_TO_SLUG.get(name)
        if not slug:
            continue

        # Parse fields from content
        fields = parse_skill_fields(content)

        skills[slug] = {
            "name_it": name.title(),
            "ability_info": ability_info.strip(),
            "fields": fields,
        }

    return skills


def parse_skill_fields(content):
    """Parse field sections from skill content text.

    Returns dict with IT field names as keys (Prova, Azione, etc.)
    and a 'preamble' key for text before the first field.
    """
    fields = {}

    # Find positions of all field markers
    marker_positions = []
    for marker in FIELD_MARKERS:
        pos = 0
        while True:
            idx = content.find(marker, pos)
            if idx == -1:
                break
            # Make sure it's not inside a word
            if idx == 0 or not content[idx - 1].isalpha():
                marker_positions.append((idx, marker))
            pos = idx + len(marker)

    # Sort by position
    marker_positions.sort(key=lambda x: x[0])

    # Extract preamble (text before first field)
    if marker_positions:
        preamble = content[: marker_positions[0][0]].strip()
        if preamble:
            fields["preamble"] = preamble
    else:
        fields["preamble"] = content.strip()

    # Extract each field
    for i, (pos, marker) in enumerate(marker_positions):
        field_name = marker.rstrip(":")
        start = pos + len(marker)
        if i + 1 < len(marker_positions):
            end = marker_positions[i + 1][0]
        else:
            end = len(content)

        value = content[start:end].strip()
        if value:
            # Strip DC table data that pdftotext appends at the end
            # (sidebar tables in the PDF get extracted after the main text)
            value = strip_table_data(value)
            fields[field_name] = value

    return fields


# Patterns that indicate the start of a DC table sidebar
# These tables are already present in the EN base data as proper HTML tables
TABLE_START_PATTERNS = [
    r"CD di \w+\s*Esempio",       # "CD di Scalare Esempio di..."
    r"CD\s+Esempio di",           # "CD Esempio di..."
    r"Atteggiamento\s+iniziale",  # Diplomazia attitude table
    r"INFLUENZARE L'ATTEGGIAMENTO",
    r"Modificatore alla CD di",   # DC modifier tables
    r"CD\s+Compito",              # "CD Compito" task tables
    r"\d+\s+Una pendenza",        # Start of climb DC entries
]


def strip_table_data(text):
    """Remove DC table data that pdftotext appends from PDF sidebars.

    The tables are already available in the EN base data with proper HTML
    formatting. Keeping the flat text version would be confusing.
    """
    for pattern in TABLE_START_PATTERNS:
        m = re.search(pattern, text)
        if m:
            # Truncate at the start of the table data
            truncated = text[:m.start()].strip()
            if truncated:
                return truncated
    return text


def format_field_html(text):
    """Wrap plain text in paragraph tags with sentence-based line breaks.

    Adds <p> wrapper and inserts <br> after sentences ending with periods
    followed by capital letters (indicating a new sentence/paragraph in
    the original PDF layout).
    """
    if not text:
        return ""

    # Add line breaks between distinct topics/paragraphs
    # Pattern: sentence end (. ) followed by a new topic indicator
    text = re.sub(
        r'(\.) ([A-ZÀÈÉÌÒÙ])',
        r'\1<br>\2',
        text
    )

    return f"<p>{text}</p>"


def extract_skills_from_html(filepath):
    """Extract skill entries from the Italian SRD HTML file.

    Returns dict: slug → {fields dict with IT field names}
    """
    with open(filepath, encoding="utf-8") as f:
        content = f.read()

    body_match = re.search(r"<body>(.*)</body>", content, re.DOTALL)
    if not body_match:
        return {}
    body = body_match.group(1)

    # Split by h3 headings (skill entries)
    parts = re.split(r"<h3>([^<]+)</h3>", body)

    skills = {}
    i = 1  # Skip preamble before first h3
    while i < len(parts):
        heading = parts[i].strip()
        content_after = parts[i + 1] if i + 1 < len(parts) else ""
        i += 2

        # Parse heading: NAME (ABILITY; FLAGS)
        m = re.match(r"(.+?)\s*\(([^)]+)\)", heading)
        if not m:
            continue

        name = " ".join(m.group(1).split()).strip()
        name_upper = name.upper()

        slug = IT_SKILL_TO_SLUG.get(name_upper)
        if not slug:
            continue

        # Clean the HTML content
        desc = content_after.strip()

        # Fix bold formatting artifacts from pdf_to_html.py
        # Remove erroneous <b>di</b> (preposition wrongly bolded)
        desc = re.sub(r'<b>di</b>', 'di', desc)
        # Fix merged words like <b>diScalare</b> → di <b>Scalare</b>
        desc = re.sub(
            r'<b>di([A-ZÀÈÉÌÒÙ][a-zàèéìòù]+)</b>',
            r'di \1',
            desc
        )
        # Fix <b>CD</b> artifacts (CD is not bolded in the original)
        desc = re.sub(r'<b>CD</b>', 'CD', desc)

        # Normalize whitespace
        desc = re.sub(r"\s+", " ", desc).strip()

        # Parse fields from HTML content
        fields = parse_html_skill_fields(desc)

        skills[slug] = {
            "name_it": name.title() if name.isupper() else name,
            "fields": fields,
            "source": "html",
        }

    return skills


def parse_html_skill_fields(html_content):
    """Parse field sections from HTML skill content.

    Handles both <b>Prova:</b> and <strong>Prova:</strong> patterns.
    """
    fields = {}
    content = html_content

    # Field markers in HTML (both <b> and <strong> variants)
    html_markers = []
    for marker_text in FIELD_MARKERS:
        label = marker_text.rstrip(":")
        # Match <b>Label:</b> or <strong>Label:</strong>
        for tag in ["b", "strong"]:
            pattern = f"<{tag}>{re.escape(label)}:</{tag}>"
            for m in re.finditer(pattern, content, re.IGNORECASE):
                html_markers.append((m.start(), m.end(), label))

        # Also match plain text "Label:" at word boundary
        pattern = rf"(?<![<\w]){re.escape(label)}:\s"
        for m in re.finditer(pattern, content):
            # Skip if inside a tag
            before = content[:m.start()]
            if before.count("<") > before.count(">"):
                continue
            html_markers.append((m.start(), m.end(), label))

    # Deduplicate and sort by position
    seen = set()
    unique_markers = []
    for start, end, label in sorted(html_markers, key=lambda x: x[0]):
        if start not in seen:
            seen.add(start)
            unique_markers.append((start, end, label))

    # Extract preamble
    if unique_markers:
        preamble = content[:unique_markers[0][0]].strip()
        if preamble:
            # Clean HTML tags from preamble for plain-text storage
            fields["preamble"] = strip_tags(preamble)
    else:
        fields["preamble"] = strip_tags(content)

    # Extract each field
    for idx, (start, end, label) in enumerate(unique_markers):
        if idx + 1 < len(unique_markers):
            next_start = unique_markers[idx + 1][0]
            value = content[end:next_start].strip()
        else:
            value = content[end:].strip()

        # Clean trailing <br> tags
        value = re.sub(r"\s*<br\s*/?>\s*$", "", value).strip()

        if value:
            fields[label] = strip_tags(value)

    return fields


def strip_tags(html):
    """Remove HTML tags from text, preserving content."""
    # First handle <br> → space
    text = re.sub(r"<br\s*/?>", " ", html)
    # Remove all other tags
    text = re.sub(r"<[^>]+>", "", text)
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/parse_srd_skills_it.py <pdf_path> [--dry-run]")
        sys.exit(1)

    pdf_path = Path(sys.argv[1])
    dry_run = "--dry-run" in sys.argv

    if not pdf_path.exists():
        print(f"Error: PDF not found: {pdf_path}")
        sys.exit(1)

    if dry_run:
        print("=== DRY RUN MODE (no files will be modified) ===\n")

    # Extract text from PDF
    print(f"Extracting text from {pdf_path}...")
    text = extract_text_from_pdf(pdf_path)
    print(f"  Got {len(text)} chars\n")

    # Parse skills from PDF text
    pdf_parsed = parse_skills_from_text(text)
    print(f"Parsed {len(pdf_parsed)} skills from PDF text\n")

    # Parse skills from HTML source (if available)
    html_parsed = {}
    if HTML_SOURCE.exists():
        html_parsed = extract_skills_from_html(HTML_SOURCE)
        print(f"Parsed {len(html_parsed)} skills from HTML source\n")

    # Merge: prefer PDF text for field extraction (cleaner text),
    # but use HTML source as fallback
    all_parsed = {}
    for slug in set(list(pdf_parsed.keys()) + list(html_parsed.keys())):
        if slug in pdf_parsed:
            all_parsed[slug] = pdf_parsed[slug]
        else:
            all_parsed[slug] = html_parsed[slug]

    print(f"Total unique skills: {len(all_parsed)}\n")

    # Load base and overlay
    with open(BASE_PATH, encoding="utf-8") as f:
        base = json.load(f)
    # Build base_map preferring category=skill over skill_trick for duplicates
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

    # Update overlay with individual fields
    updated = 0
    added = 0

    for slug, skill_data in sorted(all_parsed.items()):
        if slug not in base_map:
            print(f"  Warning: {slug} not in base, skipping")
            continue

        base_entry = base_map[slug]
        fields = skill_data["fields"]

        if slug in overlay_map:
            entry = overlay_map[slug]
            changes = []

            # Write individual fields (check, action, etc.)
            for it_field, en_field in IT_FIELD_TO_EN.items():
                it_text = fields.get(it_field, "")
                if not it_text:
                    continue

                # Only update if EN base has this field (don't add fields
                # that don't exist in the base)
                if not base_entry.get(en_field):
                    continue

                # Only update if overlay doesn't have it yet
                if not entry.get(en_field, "").strip():
                    html_val = format_field_html(it_text)
                    if not dry_run:
                        entry[en_field] = html_val
                    changes.append(f"+{en_field}")

            # Remove old desc_html if we now have individual fields
            # (individual fields are preferred by the frontend)
            if changes and entry.get("desc_html"):
                if not dry_run:
                    del entry["desc_html"]
                changes.append("-desc_html (replaced by fields)")

            # Update translation_source
            if changes and "translation_source" not in entry:
                if not dry_run:
                    entry["translation_source"] = "pdf"
                    entry["reviewed"] = False

            if changes:
                updated += 1
                print(f"  Updated {slug}: {', '.join(changes)}")
        else:
            # Create new entry
            new_entry = {
                "slug": slug,
                "name": skill_data["name_it"],
                "translation_source": "pdf",
                "reviewed": False,
            }

            for it_field, en_field in IT_FIELD_TO_EN.items():
                it_text = fields.get(it_field, "")
                if it_text and base_entry.get(en_field):
                    new_entry[en_field] = format_field_html(it_text)

            if not dry_run:
                overlay.append(new_entry)
                overlay_map[slug] = new_entry
            added += 1
            print(f"  Added {slug}: {skill_data['name_it']}")

    # Summary
    print(f"\nSummary:")
    print(f"  PDF skills parsed:  {len(pdf_parsed)}")
    print(f"  HTML skills parsed: {len(html_parsed)}")
    print(f"  Updated: {updated} overlay entries")
    print(f"  Added:   {added} new overlay entries")

    # Count field coverage
    field_counts = {en: 0 for en in IT_FIELD_TO_EN.values()}
    for entry in overlay:
        for en_field in IT_FIELD_TO_EN.values():
            if entry.get(en_field):
                field_counts[en_field] += 1
    print(f"\n  Field coverage in overlay:")
    for field, count in sorted(field_counts.items()):
        print(f"    {field}: {count}")

    # Show unmatched
    known_slugs = set(IT_SKILL_TO_SLUG.values())
    parsed_slugs = set(all_parsed.keys())
    missing = known_slugs - parsed_slugs
    if missing:
        print(f"\n  Skills in mapping but not parsed ({len(missing)}):")
        for s in sorted(missing):
            print(f"    {s}")

    if not dry_run and (updated > 0 or added > 0):
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
