#!/usr/bin/env python3
"""
Parse downloaded dndtools.net feat HTML into structured JSON.

Reads feat HTML files from html_cache/feats/items/, extracts all fields,
and produces data/dndtools/feats_en_parsed.json with deduplication and stats.

Auto-discovers HTML files from html_cache/feats/items/.

Usage:
    python scripts/dndtools_parse_feats.py                  # parse all feats
    python scripts/dndtools_parse_feats.py --output out.json # custom output file
"""

from html import unescape as html_unescape
import json
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(REPO_ROOT, "html_cache")
FEATS_ITEMS_DIR = os.path.join(CACHE_DIR, "feats", "items")
DEFAULT_OUTPUT = os.path.join(REPO_ROOT, "data", "dndtools", "feats_en_parsed.json")


def strip_tags(html_str):
    """Remove all HTML tags from a string."""
    return re.sub(r"<[^>]+>", "", html_str)


def clean_text(text):
    """Clean extracted text: decode entities, normalize whitespace."""
    text = html_unescape(text)
    text = " ".join(text.split()).strip()
    return text


def slugify(name):
    """Create a slug from a feat name."""
    s = name.lower().strip()
    s = re.sub(r"['\u2019]", "", s)
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    return s


def extract_section(content, heading, next_headings=None):
    """Extract text content between an <h4> heading and the next heading or end.

    Returns the raw HTML between the heading and the next section boundary,
    or None if the heading is not found.
    """
    if next_headings is None:
        next_headings = ["Prerequisite", "Required for", "Benefit", "Normal",
                         "Special", "Also appears in"]

    # Build pattern: match <h4>heading</h4> (case-insensitive, allow whitespace)
    pattern = r"<h4>\s*" + re.escape(heading) + r"\s*</h4>"
    match = re.search(pattern, content, re.IGNORECASE)
    if not match:
        return None

    start = match.end()

    # Find the next section boundary
    boundary_patterns = []
    for h in next_headings:
        boundary_patterns.append(r"<h4>\s*" + re.escape(h) + r"\s*</h4>")
    # Also stop at end of content div, or "Also appears in" as <h3>
    boundary_patterns.append(r"<h3>")
    boundary_patterns.append(r"</div>\s*</div>\s*<div")

    combined_boundary = "|".join(boundary_patterns)
    end_match = re.search(combined_boundary, content[start:], re.IGNORECASE)
    if end_match:
        section_html = content[start:start + end_match.start()]
    else:
        section_html = content[start:]

    return section_html.strip()


def section_to_text(section_html):
    """Convert section HTML to clean text."""
    if not section_html:
        return None
    # Strip links but keep text
    text = re.sub(r'<a[^>]*>(.*?)</a>', r'\1', section_html)
    # Strip remaining tags
    text = strip_tags(text)
    text = clean_text(text)
    return text if text else None


def section_to_desc_html(section_html):
    """Convert section HTML to cleaned desc_html (keep <p> and inline tags)."""
    if not section_html:
        return ""
    # Remove links but keep text
    html = re.sub(r'<a[^>]*>(.*?)</a>', r'\1', section_html)
    # Remove <abbr> wrappers but keep text
    html = re.sub(r'<abbr[^>]*>(.*?)</abbr>', r'\1', html)
    return html.strip()


def extract_required_for(content):
    """Extract feat names from the 'Required for' section.

    Returns a list of feat name strings.
    """
    section_html = extract_section(content, "Required for")
    if not section_html:
        return []

    # Find all feat links in the section: <a href="/feats/...">Feat Name</a>
    feat_links = re.findall(r'<a\s+href="/feats/[^"]*">([^<]+)</a>', section_html)
    names = []
    for name in feat_links:
        name = clean_text(name)
        if name:
            names.append(name)
    return names


def extract_also_appears_in(content):
    """Extract book names from the 'Also appears in' section.

    Returns a list of book name strings.
    """
    # Also appears in can be <h4> or <h3>
    pattern = r"<h[34]>\s*Also appears in\s*</h[34]>"
    match = re.search(pattern, content, re.IGNORECASE)
    if not match:
        return []

    start = match.end()
    # Find end boundary (next heading or end of content)
    end_match = re.search(r"<h[234]>|</div>\s*</div>", content[start:], re.IGNORECASE)
    if end_match:
        section = content[start:start + end_match.start()]
    else:
        section = content[start:]

    # Find all links in the section
    links = re.findall(r'<a\s+href="[^"]*">([^<]+)</a>', section)
    return [clean_text(name) for name in links if clean_text(name)]


def parse_feat_html(html, source_url=""):
    """Parse a feat detail page using regex — robust for dndtools HTML."""
    data = {
        "name": "",
        "slug": "",
        "type": "",
        "prerequisites": None,
        "benefit": None,
        "normal": None,
        "special": None,
        "required_for": [],
        "desc_html": "",
        "source_book": "",
        "source_page": "",
        "source_url": source_url,
        "edition": "3.5",
        "source_site": "dndtools.net",
    }

    # Find the #content div
    content_match = re.search(r'<div[^>]*id="content"[^>]*>(.*)', html, re.DOTALL)
    content = content_match.group(1) if content_match else html

    # Feat name from <h2> inside content
    h2_match = re.search(r"<h2>(.*?)</h2>", content)
    if h2_match:
        data["name"] = clean_text(strip_tags(h2_match.group(1)))

    if not data["name"]:
        return data

    data["slug"] = slugify(data["name"])

    # Source book from rulebook link: <a href="/rulebooks/...">Book Name</a>, p. 123
    book_match = re.search(
        r'<a\s+href="/rulebooks/[^"]*">([^<]+)</a>\s*,?\s*p\.\s*(\d+)',
        content
    )
    if book_match:
        data["source_book"] = clean_text(book_match.group(1))
        data["source_page"] = book_match.group(2)
    else:
        # Try without page number
        book_match2 = re.search(r'<a\s+href="/rulebooks/[^"]*">([^<]+)</a>', content)
        if book_match2:
            data["source_book"] = clean_text(book_match2.group(1))

    # Feat type/category from category link:
    # <a href="/feats/categories/{type}/">Type Name</a>
    type_match = re.search(
        r'<a\s+href="/feats/categories/[^"]*">([^<]+)</a>',
        content
    )
    if type_match:
        data["type"] = clean_text(type_match.group(1))

    # Edition detection: look for "3.0 Edition" warning text
    if re.search(r"3\.0\s+Edition", html, re.IGNORECASE):
        data["edition"] = "3.0"

    # Extract sections via <h4> headings
    # Prerequisite
    prereq_html = extract_section(content, "Prerequisite")
    data["prerequisites"] = section_to_text(prereq_html)

    # Benefit
    benefit_html = extract_section(content, "Benefit")
    data["benefit"] = section_to_text(benefit_html)

    # Normal
    normal_html = extract_section(content, "Normal")
    data["normal"] = section_to_text(normal_html)

    # Special
    special_html = extract_section(content, "Special")
    data["special"] = section_to_text(special_html)

    # Required for
    data["required_for"] = extract_required_for(content)

    # Build desc_html from all available sections
    desc_parts = []

    # Also include the brief description (text between type link and first <h4>)
    # This is the one-line description like "You can charge in a crooked line."
    brief_desc = ""
    type_link_match = re.search(
        r'<a\s+href="/feats/categories/[^"]*">[^<]+</a>\s*\]?\s*',
        content
    )
    first_h4 = re.search(r"<h4>", content)
    if type_link_match and first_h4:
        between = content[type_link_match.end():first_h4.start()]
        brief_text = clean_text(strip_tags(between))
        if brief_text:
            brief_desc = brief_text

    if brief_desc:
        desc_parts.append(f"<p>{brief_desc}</p>")

    if data["prerequisites"]:
        desc_parts.append(f"<p><strong>Prerequisite:</strong> {data['prerequisites']}</p>")

    if data["benefit"]:
        # Use the HTML version for desc_html (preserving <p>, <em>, etc.)
        benefit_desc = section_to_desc_html(benefit_html)
        if benefit_desc:
            # Wrap in <p> if not already wrapped
            if not benefit_desc.strip().startswith("<p"):
                benefit_desc = f"<p><strong>Benefit:</strong> {strip_tags(benefit_desc)}</p>"
            else:
                benefit_desc = f"<p><strong>Benefit:</strong></p>\n{benefit_desc}"
            desc_parts.append(benefit_desc)

    if data["normal"]:
        desc_parts.append(f"<p><strong>Normal:</strong> {data['normal']}</p>")

    if data["special"]:
        desc_parts.append(f"<p><strong>Special:</strong> {data['special']}</p>")

    data["desc_html"] = "\n".join(desc_parts)

    # Decode HTML entities in text fields
    for field in ("name", "type", "source_book", "source_page"):
        if data[field]:
            data[field] = html_unescape(data[field])

    return data


def discover_feat_files():
    """Auto-discover feat HTML files from html_cache/feats/items/."""
    if not os.path.isdir(FEATS_ITEMS_DIR):
        return []

    html_files = sorted(f for f in os.listdir(FEATS_ITEMS_DIR) if f.endswith(".html"))
    return html_files


def reconstruct_source_url(filename):
    """Reconstruct the dndtools.net URL from the cached filename.

    Filename patterns:
      {book-slug}__{feat-slug}.html  -> /feats/{book-slug}/{feat-slug}/
      {feat-slug}.html               -> /feats/{feat-slug}/  (unlikely but handle)
    """
    name = filename.replace(".html", "")
    if "__" in name:
        parts = name.split("__", 1)
        return f"https://dndtools.net/feats/{parts[0]}/{parts[1]}/"
    else:
        return f"https://dndtools.net/feats/{name}/"


def parse_all_feats(html_files):
    """Parse all feat HTML files."""
    feats = []
    errors = []
    empty_desc = 0

    for filename in html_files:
        filepath = os.path.join(FEATS_ITEMS_DIR, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                html = f.read()
        except Exception as e:
            errors.append((filename, str(e)))
            continue

        source_url = reconstruct_source_url(filename)
        feat_data = parse_feat_html(html, source_url)

        if not feat_data["name"]:
            errors.append((filename, "No feat name found"))
            continue

        if not feat_data["desc_html"]:
            empty_desc += 1

        feats.append(feat_data)

    return feats, errors, empty_desc


def deduplicate(feats):
    """Remove duplicates by (name_lower, source_book). Keep first occurrence."""
    seen = set()
    unique = []
    dupes = 0
    for feat in feats:
        key = (feat["name"].lower(), feat.get("source_book", ""))
        if key in seen:
            dupes += 1
            continue
        seen.add(key)
        unique.append(feat)
    if dupes:
        print(f"  Removed {dupes} duplicates")
    return unique


def main():
    args = sys.argv[1:]
    output_file = DEFAULT_OUTPUT

    for i, arg in enumerate(args):
        if arg == "--output" and i + 1 < len(args):
            output_file = args[i + 1]

    html_files = discover_feat_files()
    if not html_files:
        print("No feat HTML files found in html_cache/feats/items/.")
        print("Run: python scripts/dndtools_download.py --category feats")
        sys.exit(1)

    print(f"D&D Tools Feat Parser")
    print(f"Cache dir: {FEATS_ITEMS_DIR}")
    print(f"HTML files: {len(html_files)}")
    print(f"Output: {output_file}\n")

    # Parse all files
    print(f"  Parsing {len(html_files)} files...")
    feats, errors, empty_desc = parse_all_feats(html_files)

    if errors:
        print(f"    Errors: {len(errors)}")
        for filename, err in errors[:10]:
            print(f"      {filename}: {err}")
        if len(errors) > 10:
            print(f"      ... and {len(errors) - 10} more")
    if empty_desc:
        print(f"    No desc: {empty_desc}")

    print(f"\n{'='*60}")
    print(f"Pre-dedup total: {len(feats)}")

    feats = deduplicate(feats)

    print(f"Final total: {len(feats)}")

    # Stats
    types = {}
    editions = {"3.0": 0, "3.5": 0}
    books = {}
    with_prereqs = 0
    with_required_for = 0

    for feat in feats:
        t = feat.get("type", "") or "Unknown"
        types[t] = types.get(t, 0) + 1
        ed = feat.get("edition", "3.5")
        editions[ed] = editions.get(ed, 0) + 1
        book = feat.get("source_book", "") or "Unknown"
        books[book] = books.get(book, 0) + 1
        if feat.get("prerequisites"):
            with_prereqs += 1
        if feat.get("required_for"):
            with_required_for += 1

    print(f"\nBy type:")
    for t, count in sorted(types.items(), key=lambda x: -x[1]):
        print(f"  {t}: {count}")

    print(f"\nBy edition:")
    for ed, count in sorted(editions.items()):
        print(f"  {ed}: {count}")

    print(f"\nTop 10 source books:")
    for book, count in sorted(books.items(), key=lambda x: -x[1])[:10]:
        print(f"  {book}: {count}")

    print(f"\nWith prerequisites: {with_prereqs}")
    print(f"With required_for: {with_required_for}")

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    # Write output JSON
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(feats, f, indent=2, ensure_ascii=False)
    print(f"\nWritten to: {output_file}")

    # Also write JSONL
    jsonl_file = output_file.replace(".json", ".jsonl")
    with open(jsonl_file, "w", encoding="utf-8") as f:
        for feat in feats:
            f.write(json.dumps(feat, ensure_ascii=False) + "\n")
    print(f"JSONL: {jsonl_file}")

    # Report feats without descriptions
    no_desc = [f for f in feats if not f.get("desc_html")]
    if no_desc:
        print(f"\n  WARNING: {len(no_desc)} feats without description")
        for feat in no_desc[:5]:
            print(f"    - {feat['name']} ({feat.get('source_book', '?')})")


if __name__ == "__main__":
    main()
