#!/usr/bin/env python3
"""
Parse downloaded dndtools.net race HTML pages into structured JSON.

Reads race HTML files from html_cache/races/items/, extracts all fields,
and produces data/dndtools/races_en_parsed.json with deduplication and stats.

Usage:
    python scripts/dndtools_parse_races.py
    python scripts/dndtools_parse_races.py --output custom.json
"""

from html import unescape as html_unescape
import json
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(REPO_ROOT, "html_cache")
ITEMS_DIR = os.path.join(CACHE_DIR, "races", "items")
OUTPUT_DIR = os.path.join(REPO_ROOT, "data", "dndtools")
DEFAULT_OUTPUT = os.path.join(OUTPUT_DIR, "races_en_parsed.json")

# RaceSize object IDs from dndtools Django DB → D&D size names
# Derived from known creatures: Human(5)=Medium, Gnome(4)=Small, Imp(3)=Tiny, etc.
RACE_SIZE_MAP = {
    "1": "Fine",
    "2": "Diminutive",
    "3": "Tiny",
    "4": "Small",
    "5": "Medium",
    "6": "Large",
    "7": "Huge",
    "8": "Gargantuan",
    "9": "Colossal",
}

# RaceSpeedType object IDs → speed type labels
# 9 = Land, 8 = Swim, 2 = Climb (inferred from data)
SPEED_TYPE_MAP = {
    "1": "Burrow",
    "2": "Climb",
    "3": "Fly",
    "8": "Swim",
    "9": "Land",
}


def slugify(name):
    """Create a slug from a name."""
    s = name.lower().strip()
    s = re.sub(r"['\u2019]", "", s)
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    return s


def clean_text(text):
    """Strip HTML tags and normalize whitespace."""
    text = re.sub(r"<[^>]+>", "", text)
    text = html_unescape(text)
    text = " ".join(text.split()).strip()
    return text


def parse_race_html(html, source_url=""):
    """Parse a race detail page using regex."""
    data = {
        "name": "",
        "slug": "",
        "size": "",
        "speed": "",
        "ability_adjustments": "None",
        "level_adjustment": "",
        "space": "",
        "reach": "",
        "traits": [],
        "desc_html": "",
        "source_book": "",
        "source_page": "",
        "source_url": source_url,
        "edition": "3.5",
        "source_site": "dndtools.net",
        "source": "",
    }

    # Find the #content div
    content_match = re.search(r'<div[^>]*id="content"[^>]*>(.*)', html, re.DOTALL)
    content = content_match.group(1) if content_match else html

    # Race name from <h2>
    h2_match = re.search(r"<h2>(.*?)</h2>", content)
    if h2_match:
        data["name"] = clean_text(h2_match.group(1))

    if not data["name"]:
        return None

    data["slug"] = slugify(data["name"])

    # Edition detection: look for 3.0 Edition warning anywhere in the HTML
    if re.search(r"3\.0 Edition", html):
        data["edition"] = "3.0"

    # Source book from rulebook link (after <h2>, in the parenthetical)
    book_match = re.search(
        r'<a href="/rulebooks/[^"]*">([^<]+)</a>\s*(?:,\s*p\.\s*(\d+))?\s*\)',
        content
    )
    if book_match:
        data["source_book"] = html_unescape(book_match.group(1).strip())
        if book_match.group(2):
            data["source_page"] = book_match.group(2)

    # Source abbreviation from filename convention (set by caller)

    # --- Attributes table ---

    # Size: "RaceSize object (N)"
    size_match = re.search(r"RaceSize object \((\d+)\)", content)
    if size_match:
        size_id = size_match.group(1)
        data["size"] = RACE_SIZE_MAP.get(size_id, f"Unknown({size_id})")

    # Base speed: "RaceSpeedType object (N) <number>"
    speed_entries = re.findall(
        r"RaceSpeedType object \((\d+)\)\s*(\d+)", content
    )
    if speed_entries:
        speed_parts = []
        for speed_type_id, speed_val in speed_entries:
            speed_type = SPEED_TYPE_MAP.get(speed_type_id, "")
            if speed_type == "Land" or speed_type == "":
                speed_parts.append(speed_val)
            else:
                speed_parts.append(f"{speed_type} {speed_val}")
        data["speed"] = ", ".join(speed_parts)

    # Ability adjustments from the attributes table
    ability_labels = ["Strength", "Intelligence", "Dexterity", "Wisdom",
                      "Constitution", "Charisma"]
    ability_abbrevs = {"Strength": "Str", "Intelligence": "Int",
                       "Dexterity": "Dex", "Wisdom": "Wis",
                       "Constitution": "Con", "Charisma": "Cha"}
    adjustments = []

    for label in ability_labels:
        # Match: <th>Label:</th>\s*<td> +N</td> or <td> &minus;N</td>
        # Use alternation for minus sign variants (entity, unicode, ascii)
        pattern = (
            r"<th>" + label + r":</th>\s*<td>\s*"
            r"((?:\+|-|\u2212|&minus;)?\s*\d+)\s*</td>"
        )
        match = re.search(pattern, content, re.DOTALL)
        if match:
            val_str = match.group(1).strip()
            # Normalize minus signs
            val_str = val_str.replace("\u2212", "-").replace("&minus;", "-")
            val_str = re.sub(r"\s+", "", val_str)
            try:
                val = int(val_str)
                if val != 0:
                    sign = "+" if val > 0 else ""
                    adjustments.append(
                        f"{sign}{val} {ability_abbrevs[label]}"
                    )
            except ValueError:
                pass

    if adjustments:
        data["ability_adjustments"] = ", ".join(adjustments)

    # Level adjustment
    la_match = re.search(
        r"<th>Level adjustment:</th>\s*<td>\s*((?:\+|-|\u2212|&minus;)?\s*\d+)\s*</td>",
        content, re.DOTALL
    )
    if la_match:
        la_val = la_match.group(1).strip()
        la_val = la_val.replace("\u2212", "-").replace("&minus;", "-")
        la_val = re.sub(r"\s+", "", la_val)
        # Ensure + prefix for non-negative
        if not la_val.startswith("-") and not la_val.startswith("+"):
            la_val = "+" + la_val
        data["level_adjustment"] = la_val

    # Space
    space_match = re.search(
        r"<th>Space:</th>\s*<td>\s*(\d+)\s*(?:feet|ft)",
        content, re.DOTALL
    )
    if space_match:
        data["space"] = space_match.group(1)

    # Reach
    reach_match = re.search(
        r"<th>Reach:</th>\s*<td>\s*(\d+)\s*(?:feet|ft)",
        content, re.DOTALL
    )
    if reach_match:
        data["reach"] = reach_match.group(1)

    # --- Sections in nice-textile div ---
    textile_match = re.search(
        r'<div class="nice-textile">(.*?)</div>\s*(?:<div|$)',
        content, re.DOTALL
    )
    textile_html = textile_match.group(1) if textile_match else ""

    # Description section
    desc_match = re.search(
        r"<h3>Description</h3>\s*(.*?)(?=<h3>|$)",
        textile_html, re.DOTALL
    )
    desc_html_parts = []
    if desc_match:
        desc_content = desc_match.group(1).strip()
        if desc_content:
            # Strip links but keep text
            desc_content = re.sub(r'<a[^>]*>(.*?)</a>', r'\1', desc_content)
            desc_html_parts.append(desc_content)

    # Combat section
    combat_match = re.search(
        r"<h3>Combat</h3>\s*(.*?)(?=<h3>|$)",
        textile_html, re.DOTALL
    )
    if combat_match:
        combat_content = combat_match.group(1).strip()
        if combat_content:
            combat_content = re.sub(r'<a[^>]*>(.*?)</a>', r'\1', combat_content)
            desc_html_parts.append("<h3>Combat</h3>\n" + combat_content)

    # Racial Traits section
    traits_match = re.search(
        r"<h3>Racial Traits</h3>\s*(.*?)(?=<h3>|$)",
        textile_html, re.DOTALL
    )
    if traits_match:
        traits_content = traits_match.group(1).strip()
        if traits_content:
            # Extract individual trait items from <li> tags
            trait_items = re.findall(r"<li>(.*?)</li>", traits_content, re.DOTALL)
            for item in trait_items:
                trait_text = clean_text(item)
                if trait_text:
                    data["traits"].append(trait_text)

            # Add traits section to desc_html
            traits_clean = re.sub(r'<a[^>]*>(.*?)</a>', r'\1', traits_content)
            desc_html_parts.append("<h3>Racial Traits</h3>\n" + traits_clean)

    if desc_html_parts:
        data["desc_html"] = "\n".join(desc_html_parts).strip()

    return data


def derive_source_abbr(filename):
    """Derive a short source abbreviation from the filename's book slug."""
    # Filename format: book-slug--id__race-slug--id.html
    parts = filename.split("__")
    if not parts:
        return ""
    book_part = parts[0]

    # Known book abbreviations
    known = {
        "players-handbook-v35--6": "PHB",
        "monster-manual-v35--5": "MM",
        "dungeon-masters-guide-v35--4": "DMG",
        "book-of-exalted-deeds--52": "BoED",
        "book-of-vile-darkness--37": "BoVD",
        "dragon-compendium--109": "DC",
        "forgotten-realms-campaign-setting--19": "FRCS",
        "magic-of-incarnum--74": "MoI",
        "oriental-adventures--96": "OA",
        "races-of-destiny--81": "RoD",
        "races-of-eberron--10": "RoE",
        "races-of-stone--82": "RoS",
        "races-of-the-wild--84": "RoW",
        "savage-species--47": "SS",
        "underdark--34": "Und",
        "fiend-folio--42": "FF",
        "libris-mortis-the-book-of-the-dead--71": "LM",
        "players-handbook-ii--80": "PHB2",
    }

    if book_part in known:
        return known[book_part]

    # Fallback: abbreviate the book name
    name = book_part.split("--")[0]
    words = name.split("-")
    if len(words) == 1:
        return words[0].capitalize()[:4]
    return "".join(w[0].upper() for w in words if w)


def deduplicate(races):
    """Remove duplicates by (name_lower, source_book). Keep first occurrence."""
    seen = set()
    unique = []
    dupes = 0
    for race in races:
        key = (race["name"].lower(), race.get("source_book", ""))
        if key in seen:
            dupes += 1
            continue
        seen.add(key)
        unique.append(race)
    if dupes:
        print(f"  Removed {dupes} duplicates")
    return unique


def main():
    args = sys.argv[1:]
    output_file = DEFAULT_OUTPUT

    for i, arg in enumerate(args):
        if arg == "--output" and i + 1 < len(args):
            output_file = args[i + 1]

    print("D&D Tools Race Parser")
    print(f"Items dir: {ITEMS_DIR}")
    print(f"Output: {output_file}")
    print()

    if not os.path.isdir(ITEMS_DIR):
        print(f"ERROR: Items directory not found: {ITEMS_DIR}")
        print("Run: python scripts/dndtools_download.py --category races")
        sys.exit(1)

    # Auto-discover HTML files
    html_files = sorted(f for f in os.listdir(ITEMS_DIR) if f.endswith(".html"))
    print(f"Found {len(html_files)} HTML files")

    races = []
    errors = []
    empty_desc = 0

    for filename in html_files:
        filepath = os.path.join(ITEMS_DIR, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                html = f.read()
        except Exception as e:
            errors.append((filename, str(e)))
            continue

        # Derive source URL from filename
        # Filename: book-slug--id__race-slug--id.html
        parts = filename.replace(".html", "").split("__")
        if len(parts) == 2:
            book_slug, race_slug = parts
            source_url = f"https://dndtools.net/races/{book_slug}/{race_slug}/"
        else:
            source_url = ""

        race_data = parse_race_html(html, source_url)

        if race_data is None:
            errors.append((filename, "No race name found"))
            continue

        # Add source abbreviation
        race_data["source"] = derive_source_abbr(filename)

        if not race_data["desc_html"]:
            empty_desc += 1

        races.append(race_data)

    print(f"\nParsed: {len(races)} races")
    if errors:
        print(f"Errors: {len(errors)}")
        for fname, err in errors[:5]:
            print(f"  {fname}: {err}")
    if empty_desc:
        print(f"No description: {empty_desc}")

    # Deduplicate
    races = deduplicate(races)

    # Sort by name
    races.sort(key=lambda r: r["name"].lower())

    # Write output
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(races, f, indent=2, ensure_ascii=False)
    print(f"\nWritten {len(races)} races to: {output_file}")

    # Summary by source
    by_source = {}
    for r in races:
        src = r.get("source_book", "Unknown")
        by_source[src] = by_source.get(src, 0) + 1
    print(f"\nBy source book:")
    for src, count in sorted(by_source.items()):
        print(f"  {src}: {count}")

    # Summary by edition
    by_edition = {}
    for r in races:
        ed = r.get("edition", "?")
        by_edition[ed] = by_edition.get(ed, 0) + 1
    print(f"\nBy edition:")
    for ed, count in sorted(by_edition.items()):
        print(f"  {ed}: {count}")

    # Summary by size
    by_size = {}
    for r in races:
        sz = r.get("size", "?") or "?"
        by_size[sz] = by_size.get(sz, 0) + 1
    print(f"\nBy size:")
    for sz, count in sorted(by_size.items()):
        print(f"  {sz}: {count}")


if __name__ == "__main__":
    main()
