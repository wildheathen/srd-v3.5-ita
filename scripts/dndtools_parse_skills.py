#!/usr/bin/env python3
"""
Parse downloaded dndtools.net HTML into structured JSON for skills and skill tricks.

Reads skill HTML files from html_cache/skills/items/ and skill trick HTML files
from html_cache/skill-tricks/items/, extracts all fields, and produces data/skills.json.

Skills (71 items): /skills/{skill-slug}/ pages
Skill Tricks (42 items): /feats/{book-slug}/{trick-slug}/ pages (category "Skill Trick")

Usage:
    python scripts/dndtools_parse_skills.py
    python scripts/dndtools_parse_skills.py --output data/skills.json
"""

from html import unescape as html_unescape
import json
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(REPO_ROOT, "html_cache")
SKILLS_CACHE = os.path.join(CACHE_DIR, "skills", "items")
TRICKS_CACHE = os.path.join(CACHE_DIR, "skill-tricks", "items")
DEFAULT_OUTPUT = os.path.join(REPO_ROOT, "data", "skills.json")

# Book abbreviation map (slug prefix -> abbreviation)
BOOK_ABBR = {
    "players-handbook-v35": "PHB",
    "players-handbook-30": "PHB3.0",
    "complete-scoundrel": "CSc",
    "complete-adventurer": "CAd",
    "complete-warrior": "CW",
    "dungeon-masters-guide-v35": "DMG",
    "expanded-psionics-handbook": "XPH",
    "oriental-adventures": "OA",
    "eberron-campaign-setting": "ECS",
    "unearthed-arcana": "UA",
    "miniatures-handbook": "MH",
    "tome-of-battle-the-book-of-nine-swords": "ToB",
    "frostburn": "Frost",
    "sandstorm": "Sand",
    "stormwrack": "Storm",
    "cityscape": "CScp",
    "races-of-the-wild": "RotW",
    "races-of-stone": "RoS",
    "races-of-destiny": "RoD",
    "races-of-eberron": "RoE",
    "races-of-faerun": "RoF",
    "planar-handbook": "PlH",
}


def book_slug_to_abbr(book_slug):
    """Convert a dndtools book slug to an abbreviation."""
    # Try exact match first (slug without the --ID suffix)
    name_part = re.sub(r"--\d+$", "", book_slug)
    if name_part in BOOK_ABBR:
        return BOOK_ABBR[name_part]
    return name_part


def strip_tags(html):
    """Remove all HTML tags, returning plain text."""
    text = re.sub(r"<[^>]+>", "", html)
    text = " ".join(text.split())
    return html_unescape(text).strip()


def clean_section_html(html):
    """Clean section HTML: remove links but keep other tags, normalize whitespace."""
    # Remove anchor tags but keep their text
    html = re.sub(r'<a[^>]*>(.*?)</a>', r'\1', html)
    # Remove the inaccurate div if present
    html = re.sub(r'<div[^>]*id="inaccurate"[^>]*>.*?</div>', '', html, flags=re.DOTALL)
    return html.strip()


def extract_sections(content_html):
    """Extract named sections from the skill page content.

    Sections are delimited by <h4> tags. Returns a dict mapping
    normalized section name -> HTML content between headers.
    """
    sections = {}

    # Find all h4 headings and their positions
    h4_pattern = re.compile(r'<h4>\s*(.*?)\s*</h4>', re.DOTALL | re.IGNORECASE)
    matches = list(h4_pattern.finditer(content_html))

    for i, match in enumerate(matches):
        # Section name: strip tags and normalize
        section_name = strip_tags(match.group(1)).strip().rstrip(":")
        section_name_lower = section_name.lower().strip()

        # Content extends from after this h4 to the start of the next h4,
        # or to the end of the nice-textile div / end of content
        start = match.end()
        if i + 1 < len(matches):
            end = matches[i + 1].start()
        else:
            # Find closing </div> of nice-textile or next <h3>
            end_match = re.search(r'</div>\s*(?:\n|$)|<h3>', content_html[start:])
            if end_match:
                end = start + end_match.start()
            else:
                end = len(content_html)

        section_content = content_html[start:end].strip()
        section_content = clean_section_html(section_content)

        sections[section_name_lower] = section_content

    return sections


def parse_skill_html(html, filename):
    """Parse a skill detail page from dndtools.net/skills/{slug}/."""
    data = {
        "name": "",
        "slug": "",
        "category": "skill",
        "key_ability": None,
        "trained_only": False,
        "armor_check_penalty": False,
        "check": None,
        "action": None,
        "try_again": None,
        "special": None,
        "synergy": None,
        "restriction": None,
        "untrained": None,
        "required_for_feats": [],
        "desc_html": "",
        "source_book": "",
        "source_page": "",
        "source_url": "",
        "edition": "3.5",
        "source_site": "dndtools.net",
        "source": "",
    }

    # Derive slug from filename
    slug = filename.replace(".html", "")
    data["slug"] = slug
    data["source_url"] = f"https://dndtools.net/skills/{slug}/"

    # Find the #content div
    content_match = re.search(r'<div[^>]*id="content"[^>]*>(.*)', html, re.DOTALL)
    content = content_match.group(1) if content_match else html

    # Edition detection: check for 3.0 warning text
    if re.search(r'3\.0 Edition material', content, re.IGNORECASE):
        data["edition"] = "3.0"

    # Skill name from <h2>, with parenthetical notation in <span class="small">
    # Format: <h2>Balance <span class="small">(DEX; Armor check penalty)</span></h2>
    # or: <h2>Knowledge (arcana) <span class="small">(INT; Trained only)</span></h2>
    h2_match = re.search(r"<h2>(.*?)</h2>", content, re.DOTALL)
    if h2_match:
        h2_html = h2_match.group(1)

        # Extract the ability/indicator info from <span class="small">(...)
        span_match = re.search(
            r'<span[^>]*class="small"[^>]*>\s*\(([^)]+)\)\s*</span>',
            h2_html, re.DOTALL
        )
        if span_match:
            paren_text = span_match.group(1)

            # Name is everything BEFORE the <span>, stripped of tags
            name_html = h2_html[:span_match.start()]
            name = strip_tags(name_html).strip()

            # Parse key ability (first token before semicolon)
            parts = [p.strip() for p in paren_text.split(";")]
            if parts:
                ability = parts[0].strip().upper()
                # Handle "None" ability (like Speak Language)
                if ability == "NONE":
                    data["key_ability"] = None
                else:
                    data["key_ability"] = ability

            # Check for trained only / armor check penalty
            paren_lower = paren_text.lower()
            data["trained_only"] = "trained only" in paren_lower
            data["armor_check_penalty"] = "armor check penalty" in paren_lower
        else:
            name = strip_tags(h2_html).strip()

        data["name"] = name

    # Source book from rulebook link
    # Format: (<a href="/skills/rulebook/players-handbook-v35--6/">Player's Handbook v.3.5</a> variant, p. 67)
    # or: (<a href="/rulebooks/...">Book Name</a>, p. 123)
    book_match = re.search(
        r'<a href="/(skills/rulebook|rulebooks)/([^"]*?)/"[^>]*>([^<]+)</a>\s*(?:variant,?\s*)?(?:,?\s*p\.\s*(\d+))?',
        content
    )
    if book_match:
        book_slug_raw = book_match.group(2)
        data["source_book"] = html_unescape(book_match.group(3).strip())
        if book_match.group(4):
            data["source_page"] = book_match.group(4)
        data["source"] = book_slug_to_abbr(book_slug_raw)

        # Also detect edition from book name
        if "3.0" in data["source_book"]:
            data["edition"] = "3.0"

    # Extract sections from the nice-textile div
    textile_match = re.search(
        r'<div class="nice-textile">(.*?)</div>\s*(?:</div>|\n)',
        content, re.DOTALL
    )
    if not textile_match:
        # Fallback: look for nice-textile content more broadly
        textile_match = re.search(
            r'<div class="nice-textile">(.*?)(?:</div>\s*){1,3}\s*(?:<h3>|$)',
            content, re.DOTALL
        )

    if textile_match:
        textile_content = textile_match.group(1)
    else:
        # Use all content after the source line
        textile_content = content

    sections = extract_sections(textile_content)

    # Map sections to data fields
    section_mapping = {
        "check": "check",
        "action": "action",
        "try again": "try_again",
        "special": "special",
        "synergy": "synergy",
        "restriction": "restriction",
        "untrained": "untrained",
    }

    for section_name, field_name in section_mapping.items():
        if section_name in sections:
            data[field_name] = sections[section_name]

    # Build desc_html from all sections (Description + Check + Action + ...)
    desc_parts = []
    section_order = ["description", "check", "action", "try again", "special",
                     "synergy", "restriction", "untrained"]
    for section_name in section_order:
        if section_name in sections and sections[section_name]:
            # Use title-cased heading
            heading = section_name.replace("_", " ").title()
            if section_name == "try again":
                heading = "Try Again"
            desc_parts.append(f"<h4>{heading}</h4>\n{sections[section_name]}")

    data["desc_html"] = "\n\n".join(desc_parts)

    # Required for feats: extract from table after <h3>Required for feats</h3>
    feats_section = re.search(
        r'<h3>Required for feats</h3>.*?<table[^>]*>(.*?)</table>',
        content, re.DOTALL
    )
    if feats_section:
        feat_links = re.findall(r'<a[^>]*>([^<]+)</a>', feats_section.group(1))
        data["required_for_feats"] = [html_unescape(f.strip()) for f in feat_links if f.strip()]

    return data


def parse_skill_trick_html(html, filename):
    """Parse a skill trick detail page from dndtools.net/feats/{book}/{trick}/."""
    data = {
        "name": "",
        "slug": "",
        "category": "skill_trick",
        "key_ability": None,
        "trained_only": None,
        "armor_check_penalty": None,
        "prerequisites": None,
        "benefit": None,
        "desc_html": "",
        "source_book": "",
        "source_page": "",
        "source_url": "",
        "edition": "3.5",
        "source_site": "dndtools.net",
        "source": "",
    }

    # Derive slug from filename: "complete-scoundrel--60__acrobatic-backstab--3275.html"
    # -> slug = "acrobatic-backstab"
    raw_name = filename.replace(".html", "")
    parts = raw_name.split("__")
    if len(parts) == 2:
        book_part = parts[0]
        trick_part = parts[1]
        # Remove the dndtools numeric ID suffix (--1234)
        trick_slug = re.sub(r"--\d+$", "", trick_part)
        book_slug_raw = book_part
        data["slug"] = trick_slug
        data["source_url"] = f"https://dndtools.net/feats/{book_part}/{trick_part}/"
    else:
        trick_slug = re.sub(r"--\d+$", "", raw_name)
        book_slug_raw = ""
        data["slug"] = trick_slug
        data["source_url"] = f"https://dndtools.net/feats/{raw_name}/"

    # Find the #content div
    content_match = re.search(r'<div[^>]*id="content"[^>]*>(.*)', html, re.DOTALL)
    content = content_match.group(1) if content_match else html

    # Edition detection
    if re.search(r'3\.0 Edition material', content, re.IGNORECASE):
        data["edition"] = "3.0"

    # Name from <h2>
    h2_match = re.search(r"<h2>(.*?)</h2>", content, re.DOTALL)
    if h2_match:
        data["name"] = strip_tags(h2_match.group(1)).strip()

    # Source book from rulebook link
    # Format: (<a href="/rulebooks/supplementals-35--5/complete-scoundrel--60/">Complete Scoundrel</a>, p. 84)
    book_match = re.search(
        r'<a href="/rulebooks/[^"]*?/([^/"]+)/"[^>]*>([^<]+)</a>\s*,?\s*p\.\s*(\d+)',
        content
    )
    if book_match:
        data["source_book"] = html_unescape(book_match.group(2).strip())
        data["source_page"] = book_match.group(3)
        data["source"] = book_slug_to_abbr(book_match.group(1))

        if "3.0" in data["source_book"]:
            data["edition"] = "3.0"
    else:
        # Fallback: just the book link without page
        book_match2 = re.search(
            r'<a href="/rulebooks/[^"]*?/([^/"]+)/"[^>]*>([^<]+)</a>',
            content
        )
        if book_match2:
            data["source_book"] = html_unescape(book_match2.group(2).strip())
            data["source"] = book_slug_to_abbr(book_match2.group(1))
        elif book_slug_raw:
            data["source"] = book_slug_to_abbr(book_slug_raw)

    # Prerequisites section
    # Format: <h4>Prerequisite</h4>\n<p>\n<a href="/skills/tumble/">Tumble</a> 12 ranks,\n</p>
    prereq_match = re.search(
        r'<h4>Prerequisite\s*</h4>\s*<p>(.*?)</p>',
        content, re.DOTALL
    )
    if prereq_match:
        prereq_html = prereq_match.group(1)
        # Strip tags but keep text
        prereq_text = strip_tags(prereq_html)
        # Clean up trailing commas and whitespace
        prereq_text = re.sub(r',\s*$', '', prereq_text).strip()
        if prereq_text:
            data["prerequisites"] = prereq_text

    # Description paragraph (before Prerequisite or Benefit heading)
    # Format: <p>You dart past your opponent's attacks...</p>
    # This appears right after the category brackets or after <br/><br/>
    desc_intro_match = re.search(
        r'(?:\]|<br\s*/?>)\s*<br\s*/?>\s*(?:<br\s*/?>)?\s*<p>(.*?)</p>\s*(?:<h4>|<div)',
        content, re.DOTALL
    )
    if not desc_intro_match:
        # Fallback: look for standalone <p> between the h2 header area and h4
        desc_intro_match = re.search(
            r'(?:<br\s*/?>)\s*\n*\s*<p>(.*?)</p>\s*\n*\s*<h4>',
            content, re.DOTALL
        )
    if not desc_intro_match:
        # Another fallback: the <p> right before <h4>Prerequisite
        desc_intro_match = re.search(
            r'<p>([^<].*?)</p>\s*(?:<h4>Prerequisite|<div class="nice-textile")',
            content, re.DOTALL
        )

    desc_intro = ""
    if desc_intro_match:
        desc_intro = clean_section_html(desc_intro_match.group(1).strip())

    # Benefit section
    textile_match = re.search(
        r'<div class="nice-textile">(.*?)(?:</div>\s*){1,3}',
        content, re.DOTALL
    )
    if textile_match:
        textile_content = textile_match.group(1)
        sections = extract_sections(textile_content)

        if "benefit" in sections:
            data["benefit"] = sections["benefit"]
    else:
        # Try to find Benefit without nice-textile wrapper
        benefit_match = re.search(
            r'<h4>Benefit\s*</h4>\s*(.*?)(?:<h4>|</div>|<h3>)',
            content, re.DOTALL
        )
        if benefit_match:
            data["benefit"] = clean_section_html(benefit_match.group(1).strip())

    # Build desc_html
    desc_parts = []
    if desc_intro:
        desc_parts.append(f"<p>{desc_intro}</p>")
    if data.get("prerequisites"):
        desc_parts.append(f"<h4>Prerequisite</h4>\n<p>{data['prerequisites']}</p>")
    if data.get("benefit"):
        desc_parts.append(f"<h4>Benefit</h4>\n{data['benefit']}")

    # Also include Special/Normal sections if present
    if textile_match:
        sections = extract_sections(textile_match.group(1))
        for section_name in ("special", "normal"):
            if section_name in sections:
                heading = section_name.title()
                desc_parts.append(f"<h4>{heading}</h4>\n{sections[section_name]}")

    data["desc_html"] = "\n\n".join(desc_parts)

    return data


def parse_all_skills():
    """Parse all skill HTML files from html_cache/skills/items/."""
    if not os.path.isdir(SKILLS_CACHE):
        print(f"  Skills cache not found: {SKILLS_CACHE}")
        print(f"  Run: python scripts/dndtools_download.py --category skills")
        return []

    html_files = sorted(f for f in os.listdir(SKILLS_CACHE) if f.endswith(".html"))
    if not html_files:
        print(f"  No skill HTML files found in {SKILLS_CACHE}")
        return []

    print(f"  Parsing {len(html_files)} skill files...")

    skills = []
    errors = []
    empty_desc = 0

    for filename in html_files:
        filepath = os.path.join(SKILLS_CACHE, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                html = f.read()
        except Exception as e:
            errors.append((filename, str(e)))
            continue

        try:
            skill_data = parse_skill_html(html, filename)
        except Exception as e:
            errors.append((filename, f"Parse error: {e}"))
            continue

        if not skill_data["name"]:
            errors.append((filename, "No skill name found"))
            continue

        if not skill_data["desc_html"]:
            empty_desc += 1

        skills.append(skill_data)

    if errors:
        print(f"    Errors: {len(errors)}")
        for fname, err in errors[:5]:
            print(f"      {fname}: {err}")

    if empty_desc:
        print(f"    No desc: {empty_desc}")

    print(f"    Parsed: {len(skills)} skills")
    return skills


def parse_all_skill_tricks():
    """Parse all skill trick HTML files from html_cache/skill-tricks/items/."""
    if not os.path.isdir(TRICKS_CACHE):
        print(f"  Skill tricks cache not found: {TRICKS_CACHE}")
        print(f"  Run: python scripts/dndtools_download.py --category skill-tricks")
        return []

    html_files = sorted(f for f in os.listdir(TRICKS_CACHE) if f.endswith(".html"))
    if not html_files:
        print(f"  No skill trick HTML files found in {TRICKS_CACHE}")
        return []

    print(f"  Parsing {len(html_files)} skill trick files...")

    tricks = []
    errors = []
    empty_desc = 0

    for filename in html_files:
        filepath = os.path.join(TRICKS_CACHE, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                html = f.read()
        except Exception as e:
            errors.append((filename, str(e)))
            continue

        try:
            trick_data = parse_skill_trick_html(html, filename)
        except Exception as e:
            errors.append((filename, f"Parse error: {e}"))
            continue

        if not trick_data["name"]:
            errors.append((filename, "No trick name found"))
            continue

        if not trick_data["desc_html"]:
            empty_desc += 1

        tricks.append(trick_data)

    if errors:
        print(f"    Errors: {len(errors)}")
        for fname, err in errors[:5]:
            print(f"      {fname}: {err}")

    if empty_desc:
        print(f"    No desc: {empty_desc}")

    print(f"    Parsed: {len(tricks)} skill tricks")
    return tricks


def deduplicate(items):
    """Remove duplicates by (name, category). Keep first occurrence."""
    seen = set()
    unique = []
    dupes = 0
    for item in items:
        key = (item["name"].lower(), item["category"])
        if key in seen:
            dupes += 1
            continue
        seen.add(key)
        unique.append(item)
    if dupes:
        print(f"  Removed {dupes} duplicates")
    return unique


def main():
    args = sys.argv[1:]
    output_file = DEFAULT_OUTPUT

    for i, arg in enumerate(args):
        if arg == "--output" and i + 1 < len(args):
            output_file = args[i + 1]

    print(f"D&D Tools Skills & Skill Tricks Parser")
    print(f"Cache dir: {CACHE_DIR}")
    print(f"Output: {output_file}\n")

    # Parse skills
    print("Skills:")
    skills = parse_all_skills()

    # Parse skill tricks
    print("\nSkill Tricks:")
    tricks = parse_all_skill_tricks()

    # Combine
    all_items = skills + tricks

    if not all_items:
        print("\nNo items parsed. Make sure HTML cache directories exist:")
        print(f"  Skills:       {SKILLS_CACHE}")
        print(f"  Skill Tricks: {TRICKS_CACHE}")
        print(f"\nDownload with:")
        print(f"  python scripts/dndtools_download.py --category skills")
        print(f"  python scripts/dndtools_download.py --category skill-tricks")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"Pre-dedup total: {len(all_items)}")

    all_items = deduplicate(all_items)

    # Sort: skills first (alphabetically), then skill tricks (alphabetically)
    all_items.sort(key=lambda x: (0 if x["category"] == "skill" else 1, x["name"].lower()))

    print(f"Final total: {len(all_items)}")
    print(f"  Skills:       {sum(1 for x in all_items if x['category'] == 'skill')}")
    print(f"  Skill Tricks: {sum(1 for x in all_items if x['category'] == 'skill_trick')}")

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    # Write JSON output
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_items, f, indent=2, ensure_ascii=False)
    print(f"\nWritten to: {output_file}")

    # Stats
    editions = {}
    sources = {}
    abilities = {}
    for item in all_items:
        ed = item.get("edition", "?")
        editions[ed] = editions.get(ed, 0) + 1
        src = item.get("source", "?")
        sources[src] = sources.get(src, 0) + 1
        if item["category"] == "skill":
            ab = item.get("key_ability") or "None"
            abilities[ab] = abilities.get(ab, 0) + 1

    print(f"\nEditions: {dict(sorted(editions.items()))}")
    print(f"Sources: {dict(sorted(sources.items(), key=lambda x: -x[1]))}")
    if abilities:
        print(f"Key abilities: {dict(sorted(abilities.items(), key=lambda x: -x[1]))}")

    # Report items without descriptions
    no_desc = [x for x in all_items if not x.get("desc_html")]
    if no_desc:
        print(f"\n  WARNING: {len(no_desc)} items without description")
        for item in no_desc[:5]:
            print(f"    {item['name']} ({item['category']})")


if __name__ == "__main__":
    main()
