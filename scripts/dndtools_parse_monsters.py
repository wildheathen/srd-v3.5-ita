#!/usr/bin/env python3
"""
Parse downloaded dndtools.net monster HTML pages into structured JSON.

Reads monster HTML files from html_cache/monsters/items/, extracts all fields,
and produces data/dndtools/monsters_en_parsed.json with deduplication and stats.

Usage:
    python scripts/dndtools_parse_monsters.py
    python scripts/dndtools_parse_monsters.py --output custom.json
"""

from html import unescape as html_unescape
import json
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(REPO_ROOT, "html_cache")
ITEMS_DIR = os.path.join(CACHE_DIR, "monsters", "items")
OUTPUT_DIR = os.path.join(REPO_ROOT, "data", "dndtools")
DEFAULT_OUTPUT = os.path.join(OUTPUT_DIR, "monsters_en_parsed.json")

# RaceSize object IDs from dndtools Django DB -> D&D size names
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


def extract_strong_field(content, label):
    """Extract text after <strong>Label:</strong> until next <strong> or </p> or <p>."""
    pattern = (
        r"<strong>" + re.escape(label) + r":</strong>\s*(.*?)"
        r"(?=<strong>|</p>|<p>|</div>)"
    )
    match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
    if match:
        value = match.group(1)
        value = re.sub(r"<[^>]+>", "", value)
        value = html_unescape(value)
        value = " ".join(value.split()).strip()
        # Remove trailing comma
        value = value.rstrip(",").strip()
        return value
    return ""


def parse_type_line(content):
    """Parse the Size/Type line from the stat block.

    Format in HTML:
    <strong>RaceSize object (N) CreatureType
        (Subtype1, Subtype2)
    </strong>

    Returns: "Size CreatureType (Subtypes)" string
    """
    # Find the first <strong> in close-paragraphs that contains RaceSize
    type_match = re.search(
        r"<p>\s*<strong>(RaceSize object \(\d+\).*?)</strong>\s*</p>",
        content, re.DOTALL
    )
    if not type_match:
        return ""

    raw = type_match.group(1)

    # Extract size from RaceSize object (N)
    size_match = re.search(r"RaceSize object \((\d+)\)", raw)
    size_name = ""
    if size_match:
        size_id = size_match.group(1)
        size_name = RACE_SIZE_MAP.get(size_id, "")

    # Remove the RaceSize object part
    type_text = re.sub(r"RaceSize object \(\d+\)\s*", "", raw)

    # Clean HTML tags
    type_text = re.sub(r"<[^>]+>", "", type_text)
    type_text = html_unescape(type_text)

    # Normalize whitespace and commas in subtypes
    type_text = " ".join(type_text.split()).strip()

    # Clean up subtype formatting: "(Evil , Extraplanar , Lawful)" -> "(Evil, Extraplanar, Lawful)"
    type_text = re.sub(r"\s*,\s*", ", ", type_text)
    # Remove space before opening paren
    type_text = re.sub(r"\s+\(", " (", type_text)
    # Remove trailing/leading whitespace in parens
    type_text = re.sub(r"\(\s+", "(", type_text)
    type_text = re.sub(r"\s+\)", ")", type_text)

    if size_name and type_text:
        return f"{size_name} {type_text}"
    elif size_name:
        return size_name
    return type_text


def parse_speed(content):
    """Parse the Speed field which has a special HTML structure.

    Format in HTML:
    <strong>Speed:</strong>
        RaceSpeedType? 30&nbsp;ft.
        , Fly 60&nbsp;ft. (Average)
    """
    speed_match = re.search(
        r"<strong>Speed:</strong>\s*(.*?)(?=</p>)",
        content, re.DOTALL
    )
    if not speed_match:
        return ""

    raw = speed_match.group(1)

    # Remove HTML tags except text
    raw = re.sub(r"<[^>]+>", "", raw)
    raw = html_unescape(raw)
    # Replace &nbsp; with space
    raw = raw.replace("\xa0", " ")
    # Normalize whitespace
    raw = " ".join(raw.split()).strip()

    # Clean up: remove commas at start/end, normalize
    raw = raw.strip(",").strip()
    # Collapse multiple commas
    raw = re.sub(r",\s*,", ",", raw)

    return raw


def parse_saves(content):
    """Parse the Saves field which has a multi-line structure.

    Format:
    <strong>Saves:</strong>
        Fort +7
        (notes)
        Ref +6
        Will +7
    """
    saves_match = re.search(
        r"<strong>Saves:</strong>\s*(.*?)(?=</p>)",
        content, re.DOTALL
    )
    if not saves_match:
        return ""

    raw = saves_match.group(1)
    raw = re.sub(r"<[^>]+>", "", raw)
    raw = html_unescape(raw)
    raw = " ".join(raw.split()).strip()

    # Format: "Fort +7 (notes) Ref +6 Will +7"
    # Normalize to comma-separated: "Fort +7, Ref +6, Will +7"
    # Keep parenthetical notes

    # Insert commas between save entries
    raw = re.sub(r"(\+\d+(?:\s*\([^)]*\))?)\s+(Ref|Will)", r"\1, \2", raw)

    return raw


def parse_abilities(content):
    """Parse the Abilities field.

    Format:
    <strong>Abilities:</strong>
        Str 19,
        Dex 13,
        ...
    """
    abilities_match = re.search(
        r"<strong>Abilities:</strong>\s*(.*?)(?=</p>)",
        content, re.DOTALL
    )
    if not abilities_match:
        return ""

    raw = abilities_match.group(1)
    raw = re.sub(r"<[^>]+>", "", raw)
    raw = html_unescape(raw)
    raw = " ".join(raw.split()).strip()
    # Remove trailing comma
    raw = raw.rstrip(",").strip()

    return raw


def parse_skills(content):
    """Parse the Skills field which contains links.

    Format:
    <strong>Skills:</strong>
        <a href="/skills/balance/">Balance</a> +10,
        <a href="/skills/climb/">Climb</a> +13, ...
    """
    skills_match = re.search(
        r"<strong>Skills:</strong>\s*(.*?)(?=</p>)",
        content, re.DOTALL
    )
    if not skills_match:
        return ""

    raw = skills_match.group(1)
    # Strip HTML tags but keep text
    raw = re.sub(r"<[^>]+>", "", raw)
    raw = html_unescape(raw)
    raw = " ".join(raw.split()).strip()
    # Remove trailing comma
    raw = raw.rstrip(",").strip()

    return raw


def parse_feats(content):
    """Parse the Feats field which contains links.

    Format:
    <strong>Feats:</strong>
        <a href="...">Dodge</a>,
        <a href="...">Mobility</a>, ...
    """
    feats_match = re.search(
        r"<strong>Feats:</strong>\s*(.*?)(?=</p>)",
        content, re.DOTALL
    )
    if not feats_match:
        return ""

    raw = feats_match.group(1)
    # Strip HTML tags but keep text
    raw = re.sub(r"<[^>]+>", "", raw)
    raw = html_unescape(raw)
    raw = " ".join(raw.split()).strip()
    # Remove trailing comma
    raw = raw.rstrip(",").strip()

    return raw


def parse_armor_class(content):
    """Parse Armor class which may span multiple lines.

    Format:
    <strong>Armor class:</strong> 20 (?1 size, +1 Dex, +10 natural,
        touch 10,
        flat-footed 19
    """
    ac_match = re.search(
        r"<strong>Armor class:</strong>\s*(.*?)(?=</p>)",
        content, re.DOTALL
    )
    if not ac_match:
        return ""

    raw = ac_match.group(1)
    raw = re.sub(r"<[^>]+>", "", raw)
    raw = html_unescape(raw)
    raw = " ".join(raw.split()).strip()

    # Fix the common "?" character used instead of proper minus sign
    # e.g. "20 (?1 size" -> "20 (-1 size"
    raw = re.sub(r"\?(\d)", r"-\1", raw)

    return raw


def parse_monster_html(html, source_url=""):
    """Parse a monster detail page using regex."""
    data = {
        "name": "",
        "slug": "",
        "type": "",
        "hit_dice": "",
        "initiative": "",
        "speed": "",
        "armor_class": "",
        "base_attack_grapple": "",
        "attack": "",
        "full_attack": "",
        "space_reach": "",
        "special_attacks": "",
        "special_qualities": "",
        "saves": "",
        "abilities": "",
        "skills": "",
        "feats": "",
        "environment": "",
        "organization": "",
        "challenge_rating": "",
        "treasure": "",
        "alignment": "",
        "advancement": "",
        "level_adjustment": "",
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

    # Monster name from <h2>
    h2_match = re.search(r"<h2>(.*?)</h2>", content)
    if h2_match:
        data["name"] = clean_text(h2_match.group(1))

    if not data["name"]:
        return None

    data["slug"] = slugify(data["name"])

    # Edition detection
    if re.search(r"3\.0 Edition", html):
        data["edition"] = "3.0"

    # Source book from rulebook link
    book_match = re.search(
        r'<a href="/rulebooks/[^"]*">([^<]+)</a>\s*(?:,\s*p\.\s*(\d+))?\s*\)',
        content
    )
    if book_match:
        data["source_book"] = html_unescape(book_match.group(1).strip())
        if book_match.group(2):
            data["source_page"] = book_match.group(2)

    # --- Stat block (in close-paragraphs div) ---

    # Find the close-paragraphs div
    stat_match = re.search(
        r'<div class="close-paragraphs">(.*?)</div>',
        content, re.DOTALL
    )
    stat_block = stat_match.group(1) if stat_match else content

    # Type (Size + Creature Type + Subtypes)
    data["type"] = parse_type_line(stat_block)

    # Hit dice
    data["hit_dice"] = extract_strong_field(stat_block, "Hit dice")

    # Initiative
    data["initiative"] = extract_strong_field(stat_block, "Initiative")

    # Speed (special parsing)
    data["speed"] = parse_speed(stat_block)

    # Armor class (special parsing)
    data["armor_class"] = parse_armor_class(stat_block)

    # Base Attack/Grapple
    bab = extract_strong_field(stat_block, "Base Attack/Grapple")
    # Normalize minus signs
    bab = bab.replace("\u2212", "-")
    data["base_attack_grapple"] = bab

    # Attack
    data["attack"] = extract_strong_field(stat_block, "Attack")

    # Full Attack
    data["full_attack"] = extract_strong_field(stat_block, "Full Attack")

    # Space/Reach
    data["space_reach"] = extract_strong_field(stat_block, "Space/Reach")

    # Special Attacks (optional)
    data["special_attacks"] = extract_strong_field(stat_block, "Special Attacks")

    # Special Qualities (optional)
    data["special_qualities"] = extract_strong_field(stat_block, "Special Qualities")

    # Saves (special parsing)
    data["saves"] = parse_saves(stat_block)

    # Abilities (special parsing)
    data["abilities"] = parse_abilities(stat_block)

    # Skills (contains links)
    data["skills"] = parse_skills(stat_block)

    # Feats (contains links)
    data["feats"] = parse_feats(stat_block)

    # Simple strong fields
    data["environment"] = extract_strong_field(stat_block, "Environment")
    data["organization"] = extract_strong_field(stat_block, "Organization")

    # Fix truncated organization (common dndtools rendering issue with parens)
    # e.g. "Solitary or flock (5?8" -> try to recover
    org = data["organization"]
    if org and "?" in org:
        org = org.replace("?", "-")
        data["organization"] = org

    data["challenge_rating"] = extract_strong_field(stat_block, "Challenge Rating")
    data["treasure"] = extract_strong_field(stat_block, "Treasure")
    data["alignment"] = extract_strong_field(stat_block, "Alignment")

    # Advancement (may have truncated parens)
    adv = extract_strong_field(stat_block, "Advancement")
    if adv and "?" in adv:
        adv = adv.replace("?", "-")
    data["advancement"] = adv

    # Level adjustment (in stat block, different from races)
    la = extract_strong_field(stat_block, "Level adjustment")
    # Normalize dashes
    la = la.replace("\u2014", "\u2014")  # em dash stays
    data["level_adjustment"] = la

    # --- Description (in nice-textile div) ---
    textile_match = re.search(
        r'<div class="nice-textile">(.*?)</div>\s*(?:<div|$)',
        content, re.DOTALL
    )
    if textile_match:
        desc_raw = textile_match.group(1).strip()
        # Strip links but keep text
        desc_raw = re.sub(r'<a[^>]*>(.*?)</a>', r'\1', desc_raw)
        # Convert &#39; and other entities
        desc_raw = html_unescape(desc_raw)
        data["desc_html"] = desc_raw

    return data


def derive_source_abbr(filename):
    """Derive a short source abbreviation from the filename's book slug."""
    parts = filename.split("__")
    if not parts:
        return ""
    book_part = parts[0]

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

    name = book_part.split("--")[0]
    words = name.split("-")
    if len(words) == 1:
        return words[0].capitalize()[:4]
    return "".join(w[0].upper() for w in words if w)


def deduplicate(monsters):
    """Remove duplicates by (name_lower, source_book). Keep first occurrence."""
    seen = set()
    unique = []
    dupes = 0
    for monster in monsters:
        key = (monster["name"].lower(), monster.get("source_book", ""))
        if key in seen:
            dupes += 1
            continue
        seen.add(key)
        unique.append(monster)
    if dupes:
        print(f"  Removed {dupes} duplicates")
    return unique


def main():
    args = sys.argv[1:]
    output_file = DEFAULT_OUTPUT

    for i, arg in enumerate(args):
        if arg == "--output" and i + 1 < len(args):
            output_file = args[i + 1]

    print("D&D Tools Monster Parser")
    print(f"Items dir: {ITEMS_DIR}")
    print(f"Output: {output_file}")
    print()

    if not os.path.isdir(ITEMS_DIR):
        print(f"ERROR: Items directory not found: {ITEMS_DIR}")
        print("Run: python scripts/dndtools_download.py --category monsters")
        sys.exit(1)

    # Auto-discover HTML files
    html_files = sorted(f for f in os.listdir(ITEMS_DIR) if f.endswith(".html"))
    print(f"Found {len(html_files)} HTML files")

    monsters = []
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
        parts = filename.replace(".html", "").split("__")
        if len(parts) == 2:
            book_slug, monster_slug = parts
            source_url = (
                f"https://dndtools.net/monsters/{book_slug}/{monster_slug}/"
            )
        else:
            source_url = ""

        monster_data = parse_monster_html(html, source_url)

        if monster_data is None:
            errors.append((filename, "No monster name found"))
            continue

        # Add source abbreviation
        monster_data["source"] = derive_source_abbr(filename)

        if not monster_data["desc_html"]:
            empty_desc += 1

        monsters.append(monster_data)

    print(f"\nParsed: {len(monsters)} monsters")
    if errors:
        print(f"Errors: {len(errors)}")
        for fname, err in errors[:5]:
            print(f"  {fname}: {err}")
    if empty_desc:
        print(f"No description: {empty_desc}")

    # Deduplicate
    monsters = deduplicate(monsters)

    # Sort by name
    monsters.sort(key=lambda m: m["name"].lower())

    # Write output
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(monsters, f, indent=2, ensure_ascii=False)
    print(f"\nWritten {len(monsters)} monsters to: {output_file}")

    # Summary by source
    by_source = {}
    for m in monsters:
        src = m.get("source_book", "Unknown")
        by_source[src] = by_source.get(src, 0) + 1
    print(f"\nBy source book:")
    for src, count in sorted(by_source.items()):
        print(f"  {src}: {count}")

    # Summary by edition
    by_edition = {}
    for m in monsters:
        ed = m.get("edition", "?")
        by_edition[ed] = by_edition.get(ed, 0) + 1
    print(f"\nBy edition:")
    for ed, count in sorted(by_edition.items()):
        print(f"  {ed}: {count}")

    # Show sample entries
    print(f"\nSample entries (first 5):")
    for m in monsters[:5]:
        print(f"  {m['name']} - {m['type']} (CR {m['challenge_rating']})")
        print(f"    HD: {m['hit_dice']}, AC: {m['armor_class'][:40]}...")
        print(f"    Source: {m['source_book']}, p. {m['source_page']}")


if __name__ == "__main__":
    main()
