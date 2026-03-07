#!/usr/bin/env python3
"""
Parse downloaded dndtools.net class HTML pages into structured JSON.

Reads class HTML files from html_cache/classes/items/, extracts all fields,
and produces data/dndtools/classes_en_parsed.json with deduplication and stats.

Auto-discovers HTML files from html_cache/classes/items/.
Also reads list pages to build a prestige class lookup table.

Usage:
    python scripts/dndtools_parse_classes.py                  # parse all classes in cache
    python scripts/dndtools_parse_classes.py --output out.json # custom output file
"""

from html import unescape as html_unescape
import json
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(REPO_ROOT, "html_cache")
CLASSES_ITEMS_DIR = os.path.join(CACHE_DIR, "classes", "items")
CLASSES_CACHE_DIR = os.path.join(CACHE_DIR, "classes")
DEFAULT_OUTPUT = os.path.join(REPO_ROOT, "data", "dndtools", "classes_en_parsed.json")


def strip_tags(html_str):
    """Remove HTML tags from a string."""
    return re.sub(r"<[^>]+>", "", html_str)


def clean_text(text):
    """Clean text: decode entities, normalize whitespace."""
    text = html_unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def build_prestige_lookup():
    """Build a lookup of class prestige status from list pages.

    Returns a dict mapping (book_slug, class_slug) -> bool (is_prestige).
    The list page has rows like:
        <td><a href="/classes/book-slug/class-slug/">Class Name</a></td>
        <td><img src="...icon-yes.gif" ... /></td>   (prestige = yes)
    """
    prestige_map = {}
    list_dir = CLASSES_CACHE_DIR

    # Find all list_page_*.html files
    list_files = []
    if os.path.isdir(list_dir):
        for f in os.listdir(list_dir):
            if f.startswith("list_page_") and f.endswith(".html"):
                list_files.append(os.path.join(list_dir, f))

    if not list_files:
        return prestige_map

    # Pattern to match table rows with class link + prestige icon
    # Each row has: <td><a href="/classes/{book-slug}/{class-slug}/">Name</a></td>
    #               <td><img src="...icon-yes.gif" alt="yes" .../></td>
    row_pattern = re.compile(
        r'<td>\s*<a\s+href="/classes/([^/]+)/([^/]+)/">[^<]*</a>\s*</td>'
        r'\s*<td>\s*<img\s+[^>]*alt="(yes|no)"[^>]*/>\s*</td>',
        re.DOTALL
    )

    for list_file in list_files:
        try:
            with open(list_file, "r", encoding="utf-8") as f:
                html = f.read()
        except Exception:
            continue

        for match in row_pattern.finditer(html):
            book_slug = match.group(1)
            class_slug = match.group(2)
            is_prestige = match.group(3) == "yes"
            prestige_map[(book_slug, class_slug)] = is_prestige

    return prestige_map


def extract_source_url(filename):
    """Reconstruct the dndtools URL from the filename.

    Filename pattern: {book-slug}__{class-slug}.html
    URL: https://dndtools.net/classes/{book-slug}/{class-slug}/
    """
    base = filename.replace(".html", "")
    if "__" in base:
        parts = base.split("__", 1)
        book_slug = parts[0]
        class_slug = parts[1]
        return f"https://dndtools.net/classes/{book_slug}/{class_slug}/", book_slug, class_slug
    else:
        return f"https://dndtools.net/classes/{base}/", "", base


def parse_class_html(html, filename="", prestige_map=None):
    """Parse a class detail page using regex — robust for dndtools HTML."""
    source_url, book_slug_from_file, class_slug_from_file = extract_source_url(filename)

    data = {
        "name": "",
        "slug": "",
        "hit_die": "",
        "skill_points": "",
        "is_prestige": False,
        "alignment": "",
        "class_skills": [],
        "table_html": "",
        "desc_html": "",
        "source_book": "",
        "source_page": "",
        "source_url": source_url,
        "edition": "3.5",
        "source_site": "dndtools.net",
        "source": "",
    }

    # Find the #content div for focused parsing
    content_match = re.search(r'<div[^>]*id="content"[^>]*>(.*)', html, re.DOTALL)
    content = content_match.group(1) if content_match else html

    # --- Name ---
    h2_match = re.search(r"<h2>(.*?)</h2>", content)
    if h2_match:
        data["name"] = clean_text(strip_tags(h2_match.group(1)))

    # --- Slug ---
    data["slug"] = class_slug_from_file or slugify(data["name"])

    # --- Edition ---
    # Check for 3.0 Edition warning banner
    if re.search(r'3\.0\s+Edition', html):
        data["edition"] = "3.0"

    # --- Source book & page ---
    # Pattern: (<a href="/classes/rulebook/...">Book Name</a> variant, p. 24)
    # or: (<a href="/rulebooks/...">Book Name</a>, p. 24)
    book_match = re.search(
        r'<a\s+href="/classes/rulebook/[^"]*">([^<]+)</a>\s*(?:variant)?\s*,?\s*p\.\s*(\d+)',
        content
    )
    if not book_match:
        book_match = re.search(
            r'<a\s+href="/rulebooks/[^"]*">([^<]+)</a>\s*,?\s*p\.\s*(\d+)',
            content
        )
    if book_match:
        data["source_book"] = clean_text(book_match.group(1))
        data["source_page"] = book_match.group(2)
    else:
        # Try without page number
        book_match2 = re.search(
            r'<a\s+href="/classes/rulebook/[^"]*">([^<]+)</a>',
            content
        )
        if not book_match2:
            book_match2 = re.search(
                r'<a\s+href="/rulebooks/[^"]*">([^<]+)</a>',
                content
            )
        if book_match2:
            data["source_book"] = clean_text(book_match2.group(1))

    # --- Source abbreviation ---
    data["source"] = abbreviate_book(data["source_book"])

    # --- Hit Die ---
    hit_die_match = re.search(
        r'<h4>\s*Hit\s+die\s*</h4>\s*<p>\s*(d\d+)\s*</p>',
        content, re.IGNORECASE
    )
    if hit_die_match:
        data["hit_die"] = hit_die_match.group(1)
    else:
        # Fallback: look for "Hit Die" strong label
        hit_die_match2 = re.search(
            r'<strong>Hit\s+Die:?\s*</strong>\s*(d\d+)',
            content, re.IGNORECASE
        )
        if hit_die_match2:
            data["hit_die"] = hit_die_match2.group(1)

    # --- Skill Points ---
    sp_match = re.search(
        r'<h4>\s*Skill\s+points?\s*</h4>\s*<p>\s*(.*?)\s*</p>',
        content, re.IGNORECASE
    )
    if sp_match:
        data["skill_points"] = clean_text(strip_tags(sp_match.group(1)))
    else:
        sp_match2 = re.search(
            r'<strong>Skill\s+Points?:?\s*</strong>\s*(.*?)(?:<br|<strong|</p>)',
            content, re.IGNORECASE
        )
        if sp_match2:
            data["skill_points"] = clean_text(strip_tags(sp_match2.group(1)))

    # --- Alignment (from Requirements section) ---
    align_match = re.search(
        r'<strong>Alignment:?\s*</strong>\s*(.*?)(?:</p>|<br)',
        content, re.IGNORECASE | re.DOTALL
    )
    if align_match:
        data["alignment"] = clean_text(strip_tags(align_match.group(1))).rstrip(".")

    # --- Is Prestige ---
    # 1. Check prestige lookup from list pages
    if prestige_map and (book_slug_from_file, class_slug_from_file) in prestige_map:
        data["is_prestige"] = prestige_map[(book_slug_from_file, class_slug_from_file)]
    else:
        # 2. Heuristic: prestige classes have a "Requirements" section
        has_requirements = bool(re.search(
            r'<h4>\s*Requirements?\s*</h4>',
            content, re.IGNORECASE
        ))
        data["is_prestige"] = has_requirements

    # --- Class Skills ---
    # Extract from the skills table: <a href="/skills/{slug}/">Skill Name</a>
    skills_section = ""
    skills_heading = re.search(
        r'<h3>\s*Class\s+skills?\s*</h3>(.*?)(?:<h3>|<h2>|</div>\s*</div>)',
        content, re.IGNORECASE | re.DOTALL
    )
    if skills_heading:
        skills_section = skills_heading.group(1)

    if skills_section:
        skill_links = re.findall(
            r'<a\s+href="/skills/[^"]*">([^<]+)</a>',
            skills_section
        )
        data["class_skills"] = [clean_text(s) for s in skill_links]
    else:
        # Fallback: search in the whole content for a skills table
        skill_links = re.findall(
            r'<td>\s*<a\s+href="/skills/[^"]*">([^<]+)</a>\s*</td>',
            content
        )
        if skill_links:
            data["class_skills"] = [clean_text(s) for s in skill_links]

    # --- Level Progression Table (Advancement) ---
    # Look for <h3>Advancement</h3> followed by <table>
    advancement_match = re.search(
        r'<h3>\s*Advancement\s*</h3>\s*(<table>.*?</table>)',
        content, re.IGNORECASE | re.DOTALL
    )
    if advancement_match:
        data["table_html"] = advancement_match.group(1).strip()
    else:
        # Some pages have the table without an Advancement heading,
        # look for the first table that has BAB/Fort/Ref/Will columns
        table_matches = re.findall(r'(<table[^>]*>.*?</table>)', content, re.DOTALL)
        for table in table_matches:
            if re.search(r'BAB|Base\s+Attack|Fort|Ref|Will', table, re.IGNORECASE):
                # Exclude skills tables (they have "Skill name" header)
                if not re.search(r'Skill\s+name|Key\s+ability', table, re.IGNORECASE):
                    data["table_html"] = table.strip()
                    break

    # --- Description / Class Features ---
    desc_parts = []

    # 1. Intro text (first nice-textile div before Requirements/Hit die)
    intro_match = re.search(
        r'</h2>\s*(?:<p>\([^)]*\)</p>\s*)?'  # skip the source line
        r'<div\s+class="nice-textile">\s*(.*?)\s*</div>',
        content, re.DOTALL
    )
    if intro_match:
        intro_text = intro_match.group(1).strip()
        if intro_text:
            desc_parts.append(intro_text)

    # 2. Requirements section (for prestige classes)
    req_match = re.search(
        r'(<h4>\s*Requirements?\s*</h4>.*?)</div>',
        content, re.IGNORECASE | re.DOTALL
    )
    if req_match:
        req_html = req_match.group(1).strip()
        if req_html:
            desc_parts.append(req_html)

    # 3. Class Features section
    features_match = re.search(
        r'(<h4>\s*Class\s+Features?\s*</h4>.*?)(?:<h3>\s*Advancement|<h3>\s*Class\s+skills?|$)',
        content, re.IGNORECASE | re.DOTALL
    )
    if features_match:
        features_html = features_match.group(1).strip()
        if features_html:
            desc_parts.append(features_html)

    if desc_parts:
        desc_html = "\n".join(desc_parts)
        # Strip navigation links but keep content formatting
        desc_html = re.sub(r'<a[^>]*>(.*?)</a>', r'\1', desc_html)
        data["desc_html"] = desc_html.strip()

    # Decode HTML entities in simple text fields
    for field in ("name", "hit_die", "skill_points", "alignment",
                  "source_book", "source_page"):
        if data[field]:
            data[field] = html_unescape(data[field])

    return data


def slugify(name):
    """Create a slug from a class name."""
    s = name.lower().strip()
    s = re.sub(r"['\u2019]", "", s)
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    return s


# Book name to abbreviation mapping
BOOK_ABBREVIATIONS = {
    "Player's Handbook v.3.5": "PHB",
    "Player's Handbook 3.0": "PHB30",
    "Dungeon Master's Guide v.3.5": "DMG",
    "Monster Manual v.3.5": "MM",
    "Monster Manual": "MM30",
    "Complete Warrior": "CW",
    "Complete Arcane": "CArc",
    "Complete Divine": "CDiv",
    "Complete Adventurer": "CAd",
    "Complete Mage": "CM",
    "Complete Champion": "CC",
    "Complete Scoundrel": "CS",
    "Complete Psionic": "CPsi",
    "Expanded Psionics Handbook": "XPH",
    "Player's Handbook II": "PHB2",
    "Dungeon Master's Guide II": "DMG2",
    "Spell Compendium": "SC",
    "Magic Item Compendium": "MIC",
    "Unearthed Arcana": "UA",
    "Book of Exalted Deeds": "BoED",
    "Book of Vile Darkness": "BoVD",
    "Tome of Battle: The Book of Nine Swords": "ToB",
    "Tome of Magic": "ToM",
    "Magic of Incarnum": "MoI",
    "Miniatures Handbook": "MH",
    "Eberron Campaign Setting": "ECS",
    "Forgotten Realms Campaign Setting": "FRCS",
    "Dragonlance Campaign Setting": "DLCS",
    "Races of Stone": "RoS",
    "Races of the Wild": "RotW",
    "Races of Destiny": "RoD",
    "Races of the Dragon": "RotDr",
    "Races of Eberron": "RoE",
    "Draconomicon": "Drac",
    "Libris Mortis: The Book of the Dead": "LM",
    "Lords of Madness": "LoM",
    "Heroes of Battle": "HoB",
    "Heroes of Horror": "HoH",
    "Frostburn": "Frost",
    "Sandstorm": "Sand",
    "Stormwrack": "Storm",
    "Planar Handbook": "PlH",
    "Fiendish Codex I: Hordes of the Abyss": "FC1",
    "Fiendish Codex II: Tyrants of the Nine Hells": "FC2",
    "Dragon Magic": "DrM",
    "Dragon Compendium": "DrC",
    "Dungeonscape": "DSc",
    "CityScape": "CSc",
    "Drow of the Underdark": "DotU",
    "Savage Species": "SS",
    "Epic Level Handbook": "ELH",
    "Oriental Adventures": "OA",
}


def abbreviate_book(book_name):
    """Convert a book name to its abbreviation."""
    if not book_name:
        return ""
    if book_name in BOOK_ABBREVIATIONS:
        return BOOK_ABBREVIATIONS[book_name]
    # Fallback: create abbreviation from first letters of major words
    words = book_name.replace(":", "").replace("'s", "").split()
    major = [w for w in words if w[0].isupper()] if words else []
    if major:
        return "".join(w[0] for w in major[:4])
    return book_name[:6]


def discover_html_files():
    """Auto-discover class HTML files from html_cache/classes/items/."""
    if not os.path.isdir(CLASSES_ITEMS_DIR):
        return []

    files = []
    for f in sorted(os.listdir(CLASSES_ITEMS_DIR)):
        if f.endswith(".html"):
            files.append(os.path.join(CLASSES_ITEMS_DIR, f))
    return files


def deduplicate(classes):
    """Remove duplicates by (name_lower, source_book). Keep first occurrence."""
    seen = set()
    unique = []
    dupes = 0
    for cls in classes:
        key = (cls["name"].lower(), cls.get("source_book", ""))
        if key in seen:
            dupes += 1
            continue
        seen.add(key)
        unique.append(cls)
    if dupes:
        print(f"  Removed {dupes} duplicates")
    return unique


def main():
    args = sys.argv[1:]
    output_file = DEFAULT_OUTPUT

    for i, arg in enumerate(args):
        if arg == "--output" and i + 1 < len(args):
            output_file = args[i + 1]

    html_files = discover_html_files()
    if not html_files:
        print("No class HTML files found in html_cache/classes/items/.")
        print("Run: python scripts/dndtools_download.py --category classes")
        sys.exit(1)

    print(f"D&D Tools Class Parser")
    print(f"Cache dir: {CLASSES_ITEMS_DIR}")
    print(f"HTML files found: {len(html_files)}")
    print(f"Output: {output_file}\n")

    # Build prestige lookup from list pages
    print("Building prestige lookup from list pages...")
    prestige_map = build_prestige_lookup()
    print(f"  Prestige entries: {len(prestige_map)}")
    prestige_count = sum(1 for v in prestige_map.values() if v)
    base_count = sum(1 for v in prestige_map.values() if not v)
    print(f"  Prestige classes: {prestige_count}, Base classes: {base_count}\n")

    # Parse all class files
    all_classes = []
    errors = []
    empty_desc = 0
    no_table = 0

    for filepath in html_files:
        filename = os.path.basename(filepath)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                html = f.read()
        except Exception as e:
            errors.append((filename, str(e)))
            continue

        class_data = parse_class_html(html, filename, prestige_map)

        if not class_data["name"]:
            errors.append((filename, "No class name found"))
            continue

        if not class_data["desc_html"]:
            empty_desc += 1

        if not class_data["table_html"]:
            no_table += 1

        all_classes.append(class_data)

    print(f"Parsed: {len(all_classes)} classes")
    if errors:
        print(f"Errors: {len(errors)}")
        for fname, err in errors[:10]:
            print(f"  {fname}: {err}")
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more")
    if empty_desc:
        print(f"No description: {empty_desc}")
    if no_table:
        print(f"No progression table: {no_table}")

    # Deduplicate
    print(f"\nPre-dedup total: {len(all_classes)}")
    all_classes = deduplicate(all_classes)
    print(f"Final total: {len(all_classes)}")

    # Stats
    prestige_classes = [c for c in all_classes if c["is_prestige"]]
    base_classes = [c for c in all_classes if not c["is_prestige"]]
    edition_30 = [c for c in all_classes if c["edition"] == "3.0"]
    edition_35 = [c for c in all_classes if c["edition"] == "3.5"]

    print(f"\nBreakdown:")
    print(f"  Prestige: {len(prestige_classes)}")
    print(f"  Base: {len(base_classes)}")
    print(f"  3.0 Edition: {len(edition_30)}")
    print(f"  3.5 Edition: {len(edition_35)}")

    # Source book distribution (top 15)
    book_counts = {}
    for cls in all_classes:
        book = cls.get("source_book", "Unknown") or "Unknown"
        book_counts[book] = book_counts.get(book, 0) + 1

    print(f"\nTop source books:")
    for book, count in sorted(book_counts.items(), key=lambda x: -x[1])[:15]:
        print(f"  {book}: {count}")

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    # Write output
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_classes, f, indent=2, ensure_ascii=False)
    print(f"\nWritten to: {output_file}")


if __name__ == "__main__":
    main()
