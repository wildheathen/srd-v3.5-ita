#!/usr/bin/env python3
"""
Phase B+C — Parse downloaded dndtools.net HTML into structured JSON.

Reads spell HTML files from html_cache/, extracts all fields,
and produces spells_en_final.json with deduplication and stats.

Auto-discovers books from html_cache/ directories (each with a manifest.json).

Usage:
    python scripts/dndtools_parse.py                  # parse all books in cache
    python scripts/dndtools_parse.py --output out.json # custom output file
"""

from html import unescape as html_unescape
import json
import os
import re
import sys

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "html_cache")
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def parse_spell_html_regex(html, source_url=""):
    """Parse a spell detail page using regex — robust for dndtools HTML."""
    data = {
        "name": "",
        "school": "",
        "subschool": None,
        "descriptor": None,
        "level": "",
        "components": "",
        "casting_time": "",
        "range": "",
        "target_area_effect": "",
        "duration": "",
        "saving_throw": "",
        "spell_resistance": "",
        "desc_html": "",
        "source_book": "",
        "source_page": "",
        "source_url": source_url,
    }

    # Find the #content div
    content_match = re.search(r'<div[^>]*id="content"[^>]*>(.*)', html, re.DOTALL)
    content = content_match.group(1) if content_match else html

    # Spell name from <h2>
    h2_match = re.search(r"<h2>(.*?)</h2>", content)
    if h2_match:
        data["name"] = re.sub(r"<[^>]+>", "", h2_match.group(1)).strip()

    # Source book from rulebook link
    book_match = re.search(r'<a href="/rulebooks/[^"]*">([^<]+)</a>\s*,?\s*p\.\s*(\d+)', content)
    if book_match:
        data["source_book"] = book_match.group(1).strip()
        data["source_page"] = book_match.group(2)
    else:
        book_match2 = re.search(r'<a href="/rulebooks/[^"]*">([^<]+)</a>', content)
        if book_match2:
            data["source_book"] = book_match2.group(1).strip()

    # School from school link
    school_matches = re.findall(r'<a href="/spells/schools/[^"]*">([^<]+)</a>', content)
    if school_matches:
        data["school"] = school_matches[0]

    # Subschool from sub-school link
    subschool_matches = re.findall(r'<a href="/spells/sub-schools/[^"]*">([^<]+)</a>', content)
    if subschool_matches:
        data["subschool"] = subschool_matches[0]

    # Descriptors from descriptor links
    descriptor_matches = re.findall(r'<a href="/spells/descriptors/[^"]*">([^<]+)</a>', content)
    if descriptor_matches:
        data["descriptor"] = ", ".join(descriptor_matches)

    # Level from class/level links
    level_matches = re.findall(r'<a href="/classes/[^"]*spells-level-\d+/">([^<]+)</a>', content)
    if level_matches:
        data["level"] = ", ".join(level_matches)

    # Metadata fields (between <strong>Label:</strong> and <br>)
    field_patterns = {
        "components": r"<strong>Components?:</strong>\s*(.*?)(?:<br|<strong)",
        "casting_time": r"<strong>Casting Time:</strong>\s*(.*?)(?:<br|<strong)",
        "range": r"<strong>Range:</strong>\s*(.*?)(?:<br|<strong)",
        "duration": r"<strong>Duration:</strong>\s*(.*?)(?:<br|<strong)",
        "saving_throw": r"<strong>Saving Throw:</strong>\s*(.*?)(?:<br|<strong)",
        "spell_resistance": r"<strong>Spell Resistance:</strong>\s*(.*?)(?:<br|<strong)",
    }

    for field, pattern in field_patterns.items():
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        if match:
            value = match.group(1)
            value = re.sub(r"<[^>]+>", "", value)
            value = " ".join(value.split()).strip().rstrip(",").strip()
            data[field] = value

    # Target/Area/Effect — can be multiple labels
    tae_patterns = [
        r"<strong>Effect:</strong>\s*(.*?)(?:<br|<strong)",
        r"<strong>Target:</strong>\s*(.*?)(?:<br|<strong)",
        r"<strong>Targets?:</strong>\s*(.*?)(?:<br|<strong)",
        r"<strong>Area:</strong>\s*(.*?)(?:<br|<strong)",
    ]
    tae_parts = []
    seen_tae = set()
    for pattern in tae_patterns:
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        if match:
            value = re.sub(r"<[^>]+>", "", match.group(1))
            value = " ".join(value.split()).strip().rstrip(",").strip()
            if value and value not in seen_tae:
                seen_tae.add(value)
                tae_parts.append(value)
    if tae_parts:
        data["target_area_effect"] = "; ".join(tae_parts)

    # Description — all <p> tags after Spell Resistance
    sr_match = re.search(r"<strong>Spell Resistance:</strong>[^<]*", content)
    if sr_match:
        after_meta = content[sr_match.end():]
    else:
        after_meta = content

    p_matches = re.findall(r"(<p>.*?</p>)", after_meta, re.DOTALL)
    if p_matches:
        desc_html = "\n".join(p_matches)
        desc_html = re.sub(r'<a[^>]*>(.*?)</a>', r'\1', desc_html)
        data["desc_html"] = desc_html.strip()

    # Decode HTML entities in text fields (not desc_html — keep as-is)
    for field in ("name", "school", "subschool", "descriptor", "level",
                  "components", "casting_time", "range", "target_area_effect",
                  "duration", "saving_throw", "spell_resistance",
                  "source_book", "source_page"):
        if data[field]:
            data[field] = html_unescape(data[field])

    return data


def discover_books():
    """Auto-discover books from html_cache/ directories with manifest.json."""
    books = []
    if not os.path.isdir(CACHE_DIR):
        return books
    for entry in sorted(os.listdir(CACHE_DIR)):
        entry_path = os.path.join(CACHE_DIR, entry)
        if not os.path.isdir(entry_path):
            continue
        manifest_path = os.path.join(entry_path, "manifest.json")
        spells_dir = os.path.join(entry_path, "spells")
        if os.path.isdir(spells_dir):
            # Read manifest if available
            slug = ""
            if os.path.exists(manifest_path):
                with open(manifest_path, "r", encoding="utf-8") as f:
                    manifest = json.load(f)
                slug = manifest.get("slug", "")
            books.append({
                "abbr": entry,
                "slug": slug,
                "spells_dir": spells_dir,
            })
    return books


def parse_book(book):
    """Parse all spell HTML files for a book."""
    abbr = book["abbr"]
    slug = book["slug"]
    spells_dir = book["spells_dir"]

    html_files = sorted(f for f in os.listdir(spells_dir) if f.endswith(".html"))
    if not html_files:
        return []

    print(f"  Parsing {len(html_files):>5} files: {abbr}")

    spells = []
    errors = []
    empty_desc = 0

    for filename in html_files:
        filepath = os.path.join(spells_dir, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                html = f.read()
        except Exception as e:
            errors.append((filename, str(e)))
            continue

        spell_slug_name = filename.replace(".html", "")
        source_url = f"https://dndtools.net/spells/{slug}/{spell_slug_name}/" if slug else ""

        spell_data = parse_spell_html_regex(html, source_url)

        # Add book metadata
        spell_data["source"] = abbr
        spell_data["source_book_full"] = spell_data.get("source_book", "") or abbr

        if not spell_data["name"]:
            errors.append((filename, "No spell name found"))
            continue

        if not spell_data["desc_html"]:
            empty_desc += 1

        spells.append(spell_data)

    if errors:
        print(f"    Errors: {len(errors)}")
    if empty_desc:
        print(f"    No desc: {empty_desc}")

    return spells


def deduplicate(spells):
    """Remove duplicates by (name, source_book). Keep first occurrence."""
    seen = set()
    unique = []
    dupes = 0
    for spell in spells:
        key = (spell["name"].lower(), spell.get("source", ""))
        if key in seen:
            dupes += 1
            continue
        seen.add(key)
        unique.append(spell)
    if dupes:
        print(f"  Removed {dupes} duplicates")
    return unique


def main():
    args = sys.argv[1:]
    output_file = os.path.join(REPO_ROOT, "spells_en_final.json")

    for i, arg in enumerate(args):
        if arg == "--output" and i + 1 < len(args):
            output_file = args[i + 1]

    books = discover_books()
    if not books:
        print("No books found in html_cache/. Run dndtools_download.py first.")
        sys.exit(1)

    print(f"D&D Tools Spell Parser")
    print(f"Cache dir: {CACHE_DIR}")
    print(f"Books found: {len(books)}")
    print(f"Output: {output_file}\n")

    all_spells = []
    stats = {}

    for book in books:
        spells = parse_book(book)
        stats[book["abbr"]] = len(spells)
        all_spells.extend(spells)

    print(f"\n{'='*60}")
    print(f"Pre-dedup total: {len(all_spells)}")

    all_spells = deduplicate(all_spells)

    print(f"Final total: {len(all_spells)}")

    # Write output
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_spells, f, indent=2, ensure_ascii=False)
    print(f"\nWritten to: {output_file}")

    # Also write JSONL
    jsonl_file = output_file.replace(".json", ".jsonl")
    with open(jsonl_file, "w", encoding="utf-8") as f:
        for spell in all_spells:
            f.write(json.dumps(spell, ensure_ascii=False) + "\n")
    print(f"JSONL: {jsonl_file}")

    # Report
    no_desc = [s for s in all_spells if not s.get("desc_html")]
    if no_desc:
        print(f"\n  WARNING: {len(no_desc)} spells without description")


if __name__ == "__main__":
    main()
